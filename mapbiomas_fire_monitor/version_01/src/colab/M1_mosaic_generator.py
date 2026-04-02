"""
M1 — Generador de Mosaicos
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Generación de mosaicos Sentinel-2 a través de GEE (mensual + anual)
  2. Exportación a GEE Asset (país completo)
  3. Exportación a GCS (país completo — GEE divide en fragmentos grandes automáticamente)
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


# ─── FINAL DEL MÓDULO DE LÓGICA ───────────────────────────────────────────────
# Las interfaces de usuario se han movido a:
# M1a_export_dispatcher.py (GEE -> GCS)
# M1b_mosaic_assembler.py  (GCS -> COG)
