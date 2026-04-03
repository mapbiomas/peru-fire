"""
M1 — Despachador de Exportaciones
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Generación de colecciones Sentinel-2 a través de GEE (mensual + anual)
  2. Exportación a GEE Asset (país completo)
  3. Exportación a GCS (país completo en fragmentos)
  4. Interfaz de usuario para solicitar exportaciones
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


# ─── CUADRÍCULA (Opcional, para referencia/depuración) ───────────────────────

def generate_grid(geometry, tile_size_deg=None):
    """
    Generar una cuadrícula de mosaicos para referencia.
    Nota: La exportación a GCS ahora usa la división nativa de GEE.
    """
    tile_size = tile_size_deg or CONFIG['tile_size_deg']
    bounds = geometry.bounds().coordinates().getInfo()[0]

    xmin, ymin = bounds[0][0], bounds[0][1]
    xmax, ymax = bounds[2][0], bounds[2][1]

    ncols = math.ceil((xmax - xmin) / tile_size)
    nrows = math.ceil((ymax - ymin) / tile_size)

    tiles = []
    for col in range(ncols):
        for row in range(nrows):
            x0, y0 = xmin + col * tile_size, ymin + row * tile_size
            x1, y1 = x0 + tile_size, y1 + row + tile_size
            tile_geom = ee.Geometry.Rectangle([x0, y0, x1, y1])
            tiles.append({'tile_id': f"c{col:02d}r{row:02d}", 'geometry': tile_geom})
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

    if period == 'monthly':
        asset_id = f"{CONFIG['asset_mosaics_monthly']}/{name}"
    else:
        asset_id = f"{CONFIG['asset_mosaics_yearly']}/{name}"

    task = ee.batch.Export.image.toAsset(
        image       = img,
        description = f'ASSET_{name}',
        assetId     = asset_id,
        region      = country_geom.bounds(),
        scale       = 10,
        maxPixels   = 1e13,
        pyramidingPolicy = {'.default': 'median'},
    )
    task.start()
    return task


def export_to_gcs(mosaic, name, year, month=None, period='monthly'):
    """
    Enviar tareas de exportación de GEE a GCS para cada banda por separado.
    """
    geometry = get_country_geometry()
    
    if period == 'monthly':
        folder = monthly_chunk_path(year, month)
    else:
        folder = yearly_chunk_path(year)

    tasks = []
    for band in CONFIG['bands_all']:
        band_name = f"{name}_{band}"
        task = ee.batch.Export.image.toCloudStorage(
            image           = mosaic.select(band).clip(geometry),
            description     = f'GCS_{band_name}',
            bucket          = CONFIG['bucket'],
            fileNamePrefix  = f"{folder}/{band_name}",
            region          = geometry.bounds(),
            scale           = 10,
            maxPixels       = 1e13,
            fileFormat      = 'GeoTIFF',
            formatOptions   = {'cloudOptimized': True},
        )
        task.start()
        tasks.append(task)
    return tasks


# ─── VERIFICACIÓN DE ESTADO DE GCS ────────────────────────────────────────────

# ─── FINAL DEL MÓDULO DE LÓGICA ───────────────────────────────────────────────
# Las interfaces de usuario se han movido a:
# M1a_export_dispatcher.py (GEE -> GCS)
# M1b_mosaic_assembler.py  (GCS -> COG)

"""
M1a — Despachador de Exportaciones
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Generación de mosaicos en GEE
  2. Verificar qué meses/años ya están en GCS
  3. Botón "Exportar Faltantes" para automatización masiva
"""

import ee
import calendar
import ipywidgets as widgets
from IPython.display import display, clear_output
from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, yearly_chunk_path
# from M1_mosaic_generator import build_mosaic, export_to_asset, export_to_gcs, check_mosaic_status

class ExportDispatcherUI:
    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        title = HTML("""
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#e94560;padding:16px;border-radius:10px;">
                🚀 <b>Despachador de Exportaciones</b> — GEE → GCS
            </div>
        """)
        self.w_years = widgets.SelectMultiple(
            options=range(2017, 2027), value=[2024], description='Años:',
            style={'description_width': '80px'}, layout=widgets.Layout(width='150px')
        )
        self.w_months = widgets.SelectMultiple(
            options=[(f'{m:02d}', m) for m in range(1, 13)], value=[1], description='Meses:',
            style={'description_width': '80px'}, layout=widgets.Layout(width='120px')
        )
        self.btn_status = widgets.Button(description='🔍 Verificar Faltantes', button_style='info')
        self.btn_miss   = widgets.Button(description='✨ Exportar Faltantes', button_style='warning')
        self.btn_all    = widgets.Button(description='🔥 Exportar TODO el Año', button_style='danger')
        self.w_period = widgets.RadioButtons(
            options=['monthly', 'yearly', 'both'],
            value='monthly', description='Período:',
            style={'description_width': '80px'},
        )
        self.w_export_asset = widgets.Checkbox(value=True, description='Exportar → GEE Asset')
        self.w_export_gcs   = widgets.Checkbox(value=True, description='Exportar → GCS (Bucket)')

        self.out = widgets.Output()
        
        controls = widgets.VBox([
            widgets.HBox([self.w_years, self.w_months]),
            widgets.HBox([
                self.w_period,
                widgets.VBox([self.w_export_asset, self.w_export_gcs])
            ]),
            widgets.HBox([self.btn_status, self.btn_miss, self.btn_all])
        ])
        self.ui = widgets.VBox([title, controls, self.out])
        
        self.btn_status.on_click(self._on_status)
        self.btn_miss.on_click(self._on_miss)
        self.btn_all.on_click(self._on_all)

    def _get_missings(self, years, months, period):
        missing = []
        for year in years:
            # Mensual
            if period in ('monthly', 'both'):
                status = check_mosaic_status(year, months, 'monthly')
                for name, s in status.items():
                    if s['chunks'] == 0:
                        m = int(name.split('_')[-1])
                        missing.append((year, m, 'monthly'))
            # Anual
            if period in ('yearly', 'both'):
                status = check_mosaic_status(year, period='yearly')
                for name, s in status.items():
                    if s['chunks'] == 0:
                        missing.append((year, None, 'yearly'))
        return missing

    def _on_status(self, _):
        years, months = list(self.w_years.value), list(self.w_months.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            miss = self._get_missings(years, months, period)
            if not miss:
                print("✅ Todos los periodos seleccionados ya tienen fragmentos en GCS.")
            else:
                print(f"⚠️  Faltan {len(miss)} mosaicos por exportar:")
                for y, m, p in miss: 
                    label = f"{y}-{m:02d}" if p == 'monthly' else f"{y} (Anual)"
                    print(f"   - {label}")

    def _dispatch(self, list_to_export):
        from M0_auth_config import get_country_geometry
        geom = get_country_geometry()
        for year, month, p in list_to_export:
            name = mosaic_name(year, month, p)
            if p == 'monthly':
                start = ee.Date(f'{year}-{month:02d}-01')
                end = start.advance(1, 'month')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=True, year=year, month=month)
                
                if self.w_export_asset.value:
                    export_to_asset(mosaic, name, year, month, 'monthly')
                if self.w_export_gcs.value:
                    export_to_gcs(mosaic, name, year, month, 'monthly')
            else:
                start = ee.Date(f'{year}-01-01')
                end = ee.Date(f'{year+1}-01-01')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=False)
                
                if self.w_export_asset.value:
                    export_to_asset(mosaic, name, year, period='yearly')
                if self.w_export_gcs.value:
                    export_to_gcs(mosaic, name, year, period='yearly')
            print(f"   🚀 Tareas enviadas: {name}")

    def _on_miss(self, _):
        years, months = list(self.w_years.value), list(self.w_months.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            miss = self._get_missings(years, months, period)
            if not miss:
                print("✅ Nada que exportar.")
                return
            print(f"🔥 Exportando {len(miss)} periodos faltantes...")
            self._dispatch(miss)

    def _on_all(self, _):
        years = list(self.w_years.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            print(f"🚨 Iniciando exportación TOTAL para los años {years}...")
            to_export = []
            for y in years:
                if period in ('monthly', 'both'):
                    for m in range(1, 13): to_export.append((y, m, 'monthly'))
                if period in ('yearly', 'both'):
                    to_export.append((y, None, 'yearly'))
            self._dispatch(to_export)

    def show(self):
        display(self.ui)

def run_ui():
    print("✨ Cargando interfaz del Despachador...")
    ui_obj = ExportDispatcherUI()
    return ui_obj.ui
