"""
M1 — Generador de Mosaicos
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Generación de mosaicos Sentinel-2 a través de GEE (mensual + anual)
  2. Exportación a GEE Asset (país completo)
  3. Exportación a GCS como fragmentos COG (por mosaico de cuadrícula dinámica)
  4. Verificación de estado: qué mosaicos ya han sido exportados
  5. Ensamblaje del mosaico nacional: VRT → COG desde fragmentos de GCS
  6. Interfaz de ipywidgets para Colab
"""

import ee
import os
import math
import json
import subprocess
from datetime import date, timedelta
import calendar
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, gcs_path, mosaic_name, \
    monthly_chunk_path, monthly_mosaic_path, \
    yearly_chunk_path, yearly_mosaic_path, \
    get_country_geometry


# ─── FUNCIONES DE PROCESAMIENTO DE EE ─────────────────────────────────────────

def mask_and_rename(image):
    """Aplicar la máscara Cloud Score+ y renombrar las bandas de S2."""
    mask = image.select('cs').gte(CONFIG['cs_threshold'])
    return image \
        .updateMask(mask) \
        .select(CONFIG['s2_bands_in'], CONFIG['s2_bands_out'])


def add_nbr(image):
    """Añadir NBR invertido para la selección de mosaicos de calidad.
    Invertido: áreas quemadas (bajo NBR) → valores ALTOS → seleccionado por qualityMosaic().
    """
    nbr = image \
        .expression('(b("nir") - b("swir2")) / (b("nir") + b("swir2"))') \
        .multiply(-1).add(1).multiply(1000) \
        .int16().rename('nbr')
    return image.addBands(nbr)


def add_day_of_year(image):
    """Añadir la banda dayOfYear (1–366, int16) a partir de la fecha de adquisición."""
    doy = ee.Image(
        ee.Number.parse(
            ee.Date(image.get('system:time_start')).format('D')
        )
    ).int16().rename('dayOfYear')
    return image.addBands(doy)


def preprocess(image):
    """Preprocesamiento completo de S2: máscara de nubes → renombrar → NBR → dayOfYear."""
    image = mask_and_rename(image)
    image = add_nbr(image)
    image = add_day_of_year(image)
    return image


def get_focus_mask(year, month):
    """Devolver la máscara del buffer de foco de incendio para un año/mes determinado (Sudamérica)."""
    return ee.ImageCollection(CONFIG['focus_buffer']) \
        .filter(ee.Filter.eq('year', year)) \
        .filter(ee.Filter.eq('month', month)) \
        .mean()


def build_s2_collection(start_date, end_date, geometry, apply_focus_mask=False,
                         year=None, month=None):
    """Construir la ImageCollection S2 preprocesada para una ventana de tiempo."""
    cs_plus_bands = ee.ImageCollection(CONFIG['cs_plus']).first().bandNames()

    col = ee.ImageCollection(CONFIG['sensor']) \
        .filterDate(start_date, end_date) \
        .filterBounds(geometry) \
        .linkCollection(ee.ImageCollection(CONFIG['cs_plus']), cs_plus_bands) \
        .map(preprocess)

    if apply_focus_mask and year is not None and month is not None:
        focus = get_focus_mask(year, month)
        col = col.map(lambda img: img.updateMask(focus.unmask(0).gt(0)))

    return col


def build_mosaic(start_date, end_date, geometry, apply_focus_mask=False,
                  year=None, month=None):
    """
    Construir mosaico de calidad a partir de la colección S2.

    Devuelve una imagen con las bandas:
      - espectral [blue,green,red,nir,swir1,swir2]: dividir(100) → byte (0–100)
      - dayOfYear: int16 (1–366, sin conversión)
    """
    col = build_s2_collection(start_date, end_date, geometry,
                               apply_focus_mask, year, month)
    mosaic = col.qualityMosaic('nbr')

    # Espectral: S2 crudo (0–10000) ÷ 100 → 0–100 → byte
    spectral = mosaic.select(CONFIG['bands_spectral']) \
                     .divide(CONFIG['spectral_scale_factor']) \
                     .byte()

    # dayOfYear: mantener int16
    doy = mosaic.select('dayOfYear').int16()

    return spectral.addBands(doy)


# ─── CUADRÍCULA DINÁMICA ──────────────────────────────────────────────────────

def generate_grid(geometry, tile_size_deg=None):
    """
    Generar una cuadrícula de mosaicos (~1/4 de escena Landsat) que cubra la geometría.
    Devuelve una lista de diccionarios: [{tile_id, geometry, col, row}]
    Cálculo en el lado del cliente después de .getInfo().
    """
    tile_size = tile_size_deg or CONFIG['tile_size_deg']
    bounds = geometry.bounds().coordinates().getInfo()[0]

    xmin = bounds[0][0]
    ymin = bounds[0][1]
    xmax = bounds[2][0]
    ymax = bounds[2][1]

    ncols = math.ceil((xmax - xmin) / tile_size)
    nrows = math.ceil((ymax - ymin) / tile_size)

    tiles = []
    for col in range(ncols):
        for row in range(nrows):
            x0 = xmin + col * tile_size
            y0 = ymin + row * tile_size
            x1 = x0 + tile_size
            y1 = y0 + tile_size
            tile_geom = ee.Geometry.Rectangle([x0, y0, x1, y1])
            intersection = tile_geom.intersection(geometry, ee.ErrorMargin(1))
            tile_id = f"c{col:02d}r{row:02d}"
            tiles.append({
                'tile_id': tile_id,
                'geometry': tile_geom,
                'intersection': intersection,
                'col': col,
                'row': row,
            })

    return tiles


# ─── FUNCIONES DE EXPORTACIÓN ─────────────────────────────────────────────────

def export_to_asset(mosaic, name, year, month=None, period='monthly'):
    """Enviar tarea de exportación de GEE a Asset (mosaico nacional completo)."""
    country_geom = get_country_geometry()

    if period == 'monthly':
        t_start = ee.Date(f'{year}-{month:02d}-01').millis()
        t_end   = ee.Date(f'{year}-{month:02d}-01').advance(1, 'month').millis()
    else:
        t_start = ee.Date(f'{year}-01-01').millis()
        t_end   = ee.Date(f'{year+1}-01-01').millis()

    img = mosaic \
        .clip(country_geom) \
        .set({
            'system:time_start': t_start,
            'system:time_end':   t_end,
            'country':  CONFIG['country'],
            'year':     year,
            'month':    month or 0,
            'period':   period,
            'sensor':   'sentinel2',
            'bands':    CONFIG['bands_all'],
            'name':     name,
        })

    task = ee.batch.Export.image.toAsset(
        image       = img,
        description = f'ASSET_{name}',
        assetId     = f"{CONFIG['asset_mosaics']}/{name}",
        region      = country_geom.bounds(),
        scale       = 10,
        maxPixels   = 1e13,
        pyramidingPolicy = {'.default': 'median'},
    )
    task.start()
    return task


def export_to_gcs_chunks(mosaic, name, year, month=None, period='monthly', tiles=None):
    """
    Enviar tareas de exportación de GEE a GCS: un COG por mosaico de la cuadrícula.
    Devuelve una lista de tuplas (tile_id, task).
    """
    if tiles is None:
        geometry = get_country_geometry()
        tiles = generate_grid(geometry)

    if period == 'monthly':
        folder = monthly_chunk_path(year, month)
    else:
        folder = yearly_chunk_path(year)

    tasks = []
    for tile in tiles:
        tile_name = f"{name}_{tile['tile_id']}"
        img = mosaic.clip(tile['intersection'])

        task = ee.batch.Export.image.toCloudStorage(
            image           = img,
            description     = f'GCS_{tile_name}',
            bucket          = CONFIG['bucket'],
            fileNamePrefix  = f"{folder}/{tile_name}",
            region          = tile['intersection'].bounds(),
            scale           = 10,
            maxPixels       = 1e13,
            fileFormat      = 'GeoTIFF',
            formatOptions   = {'cloudOptimized': True},
        )
        task.start()
        tasks.append((tile['tile_id'], task))

    return tasks


# ─── VERIFICACIÓN DE ESTADO DE GCS ────────────────────────────────────────────

def list_gcs_files(prefix):
    """Enumerar archivos en un prefijo de GCS. Devuelve una lista de nombres de archivos."""
    try:
        result = subprocess.run(
            ['gsutil', 'ls', f"gs://{CONFIG['bucket']}/{prefix}/"],
            capture_output=True, text=True
        )
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return files
    except Exception as e:
        print(f"  ⚠️  error de gsutil: {e}")
        return []


def check_mosaic_status(year, months=None, period='monthly'):
    """
    Verificar qué mosaicos ya han sido exportados a GCS.
    Devuelve un diccionario: {mosaic_name: {'chunks': int, 'mosaic': bool}}
    """
    status = {}
    if period == 'monthly':
        check_months = months or list(range(1, 13))
        for month in check_months:
            name = mosaic_name(year, month, 'monthly')
            chunk_prefix = monthly_chunk_path(year, month)
            mosaic_prefix = monthly_mosaic_path(year, month)
            chunks = list_gcs_files(chunk_prefix)
            mosaics = list_gcs_files(mosaic_prefix)
            status[name] = {
                'chunks': len(chunks),
                'mosaic': len(mosaics) > 0,
            }
    else:
        name = mosaic_name(year, period='yearly')
        chunk_prefix = yearly_chunk_path(year)
        mosaic_prefix = yearly_mosaic_path(year)
        chunks = list_gcs_files(chunk_prefix)
        mosaics = list_gcs_files(mosaic_prefix)
        status[name] = {
            'chunks': len(chunks),
            'mosaic': len(mosaics) > 0,
        }
    return status


# ─── ENSAMBLAJE DE MOSAICO NACIONAL (VRT → COG) ───────────────────────────────

def assemble_country_mosaic(year, month=None, period='monthly'):
    """
    Descargar todos los fragmentos de GCS, construir VRT, convertir a COG, subir de nuevo a GCS.
    Requiere: gdalbuildvrt, gdal_translate, gsutil.
    """
    import tempfile, glob

    if period == 'monthly':
        chunk_prefix  = monthly_chunk_path(year, month)
        mosaic_prefix = monthly_mosaic_path(year, month)
        name = mosaic_name(year, month, 'monthly')
    else:
        chunk_prefix  = yearly_chunk_path(year)
        mosaic_prefix = yearly_mosaic_path(year)
        name = mosaic_name(year, period='yearly')

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Descargar todos los fragmentos
        print(f"  ⬇️  Descargando fragmentos de gs://{CONFIG['bucket']}/{chunk_prefix}/")
        subprocess.run([
            'gsutil', '-m', 'cp',
            f"gs://{CONFIG['bucket']}/{chunk_prefix}/*.tif",
            tmpdir
        ], check=True)

        # 2. Construir VRT
        chunk_files = glob.glob(os.path.join(tmpdir, '*.tif'))
        if not chunk_files:
            print("  ⚠️  No se encontraron fragmentos. Saltando ensamblaje.")
            return

        vrt_path = os.path.join(tmpdir, f'{name}.vrt')
        subprocess.run(['gdalbuildvrt', vrt_path] + chunk_files, check=True)
        print(f"  🔗  VRT creado: {vrt_path}")

        # 3. Convertir a COG
        cog_path = os.path.join(tmpdir, f'{name}_cog.tif')
        subprocess.run([
            'gdal_translate',
            '-of', 'COG',
            '-co', 'COMPRESS=DEFLATE',
            '-co', 'PREDICTOR=2',
            '-co', 'TILED=YES',
            '-co', 'BLOCKXSIZE=512',
            '-co', 'BLOCKYSIZE=512',
            '-co', 'OVERVIEWS=IGNORE_EXISTING',
            vrt_path, cog_path
        ], check=True)
        print(f"  🗜️  COG creado: {cog_path}")

        # 4. Subir a la carpeta de mosaicos de GCS
        dest = f"gs://{CONFIG['bucket']}/{mosaic_prefix}/{name}_cog.tif"
        subprocess.run(['gsutil', 'cp', cog_path, dest], check=True)
        print(f"  ☁️  Subido a: {dest}")

    print(f"  ✅  Mosaico nacional ensamblado: {name}")
    return dest


# ─── INTERFAZ DE IPYWIDGETS ───────────────────────────────────────────────────

class MosaicGeneratorUI:
    """
    Interfaz interactiva de widgets de Colab para la generación y el seguimiento de mosaicos.
    Características:
      - Selección de año / mes
      - Período: alternar mensual / anual
      - Verificación de estado: qué se ha exportado ya
      - Disparador de incendio: enviar tareas de exportación de GEE
    """

    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML

        title = HTML("""
            <div style="
                background: linear-gradient(135deg, #1a1a2e, #16213e);
                color: #e94560;
                padding: 16px 20px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                margin-bottom: 10px;
            ">
                🔥 <b>MapBiomas Fuego Monitor</b> — Sentinel-2 Generador de Mosaicos<br>
                <span style="color:#8892b0; font-size:11px;">
                    País: {country} | Bucket: gs://{bucket}
                </span>
            </div>
        """.format(**CONFIG))

        # ── Controles
        self.w_year = widgets.IntSlider(
            value=2024, min=2017, max=2026, step=1,
            description='Año:', style={'description_width': '80px'},
            layout=widgets.Layout(width='350px')
        )
        self.w_months = widgets.SelectMultiple(
            options=[(f'{m:02d} — {calendar.month_name[m]}', m) for m in range(1, 13)],
            value=[1], description='Meses:',
            style={'description_width': '80px'},
            layout=widgets.Layout(height='120px', width='350px')
        )
        self.w_period = widgets.RadioButtons(
            options=['monthly', 'yearly', 'both'],
            value='monthly', description='Período:',
            style={'description_width': '80px'},
        )
        self.w_export_asset = widgets.Checkbox(value=True, description='Exportar → GEE Asset')
        self.w_export_gcs   = widgets.Checkbox(value=True, description='Exportar → Fragmentos GCS')

        self.btn_status   = widgets.Button(description='🔍 Verificar Estado',
                                            button_style='info',
                                            layout=widgets.Layout(width='180px'))
        self.btn_dispatch = widgets.Button(description='🚀 Enviar Mosaico',
                                            button_style='warning',
                                            layout=widgets.Layout(width='180px'))
        self.btn_assemble = widgets.Button(description='🗺️ Ensamblar Mosaico Nacional',
                                            button_style='success',
                                            layout=widgets.Layout(width='220px'))

        self.out = widgets.Output()

        # ── Diseño
        controls = widgets.VBox([
            self.w_year,
            widgets.HBox([
                widgets.VBox([self.w_months]),
                widgets.VBox([self.w_period,
                              self.w_export_asset,
                              self.w_export_gcs]),
            ]),
            widgets.HBox([self.btn_status, self.btn_dispatch, self.btn_assemble]),
        ], layout=widgets.Layout(padding='10px'))

        self.ui = widgets.VBox([title, controls, self.out])

        # ── Funciones de llamada
        self.btn_status.on_click(self._on_status)
        self.btn_dispatch.on_click(self._on_dispatch)
        self.btn_assemble.on_click(self._on_assemble)

    def _get_params(self):
        year   = self.w_year.value
        months = list(self.w_months.value)
        period = self.w_period.value
        return year, months, period

    def _on_status(self, _):
        year, months, period = self._get_params()
        with self.out:
            clear_output()
            print(f"🔍 Comprobando el estado de {year}...\n")
            if period in ('monthly', 'both'):
                status = check_mosaic_status(year, months, 'monthly')
                for name, s in status.items():
                    icon = '✅' if s['mosaic'] else ('⏳' if s['chunks'] > 0 else '❌')
                    print(f"  {icon}  {name}  |  fragmentos: {s['chunks']}  |  mosaico: {s['mosaic']}")
            if period in ('yearly', 'both'):
                status = check_mosaic_status(year, period='yearly')
                for name, s in status.items():
                    icon = '✅' if s['mosaic'] else ('⏳' if s['chunks'] > 0 else '❌')
                    print(f"  {icon}  {name}  |  fragmentos: {s['chunks']}  |  mosaico: {s['mosaic']}")

    def _on_dispatch(self, _):
        year, months, period = self._get_params()
        geometry = get_country_geometry()
        tiles    = generate_grid(geometry)

        with self.out:
            clear_output()
            print(f"🚀 Enviando tareas de mosaico — {year} | período: {period}\n")
            print(f"   Cuadrícula: {len(tiles)} mosaicos × {CONFIG['tile_size_deg']}° cada uno\n")

            if period in ('monthly', 'both'):
                for month in months:
                    name = mosaic_name(year, month, 'monthly')
                    start = ee.Date(f'{year}-{month:02d}-01')
                    end   = start.advance(1, 'month')

                    mosaic = build_mosaic(start, end, geometry,
                                          apply_focus_mask=True,
                                          year=year, month=month)

                    if self.w_export_asset.value:
                        t = export_to_asset(mosaic, name, year, month, 'monthly')
                        print(f"  📦  Tarea de Asset enviada: {name} [{t.status()['state']}]")

                    if self.w_export_gcs.value:
                        tasks = export_to_gcs_chunks(mosaic, name, year, month,
                                                     'monthly', tiles)
                        print(f"  ☁️   Tareas de fragmentos de GCS: {len(tasks)} fragmentos para {name}")

            if period in ('yearly', 'both'):
                name = mosaic_name(year, period='yearly')
                start = ee.Date(f'{year}-01-01')
                end   = ee.Date(f'{year+1}-01-01')

                mosaic = build_mosaic(start, end, geometry,
                                      apply_focus_mask=False)

                if self.w_export_asset.value:
                    t = export_to_asset(mosaic, name, year, period='yearly')
                    print(f"  📦  Tarea de Asset enviada: {name} [{t.status()['state']}]")

                if self.w_export_gcs.value:
                    tasks = export_to_gcs_chunks(mosaic, name, year,
                                                 period='yearly', tiles=tiles)
                    print(f"  ☁️   Tareas de fragmentos de GCS: {len(tasks)} fragmentos para {name}")

            print("\n✅ Todas las tareas enviadas. Supervise en el Administrador de tareas de GEE.")

    def _on_assemble(self, _):
        year, months, period = self._get_params()
        with self.out:
            clear_output()
            print(f"🗺️  Ensamblando mosaicos nacionales — {year} | período: {period}\n")
            if period in ('monthly', 'both'):
                for month in months:
                    print(f"\n  📅  {year}-{month:02d}")
                    assemble_country_mosaic(year, month, 'monthly')
            if period in ('yearly', 'both'):
                print(f"\n  📅  {year} (anual)")
                assemble_country_mosaic(year, period='yearly')

    def show(self):
        display(self.ui)


# ─── EJECUCIÓN RÁPIDA ──────────────────────────────────────────────────────────

def run_ui():
    """Iniciar la interfaz del generador de mosaicos en Colab."""
    ui = MosaicGeneratorUI()
    ui.show()
