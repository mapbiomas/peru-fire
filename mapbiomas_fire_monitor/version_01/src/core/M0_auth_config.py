"""
M0 — Autenticación y Configuración
MapBiomas Fuego Sentinel Monitor — Piloto Perú
"""

# ─── INSTALACIÓN (ejecutar una vez por sesión de Colab) ────────────────────────
# !pip install earthengine-api gcsfs rasterio tensorflow

import ee
import os
import json

# ─── AUTENTICACIÓN ────────────────────────────────────────────────────────────

def authenticate():
    """Autenticar con Google Earth Engine y GCS."""
    try:
        ee.Initialize(project=CONFIG['ee_project'])
        print("✅ GEE ya autenticado.")
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=CONFIG['ee_project'])
        print("✅ GEE autenticado.")

    # Autenticación de GCS a través de Credenciales Predeterminadas de la Aplicación (Colab ya maneja esto)
    print("✅ Autenticación de GCS mediante ADC (Colab).")


# ─── CONFIGURACIÓN GLOBAL ─────────────────────────────────────────────────────

CONFIG = {
    # ── País / proyecto
    'country':    'peru',
    'ee_project': 'mapbiomas-peru',
    'bucket':     'mapbiomas-fire',
    'base_path':  'sudamerica/peru/monitor',

    # ── Rutas de GEE Asset
    'asset_mosaics_monthly': 'projects/mapbiomas-mosaics/assets/SENTINEL/FIRE/quality_mosaics_nbr_countries_monthly-01',
    'asset_mosaics_yearly':  'projects/mapbiomas-mosaics/assets/SENTINEL/FIRE/quality_mosaics_nbr_countries_yearly-01',
    'asset_classification':  'projects/mapbiomas-peru/assets/FIRE/MONITOR/classification',
    'asset_regions':         'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',

    # ── Estructura de carpetas de GCS
    'gcs_monthly_chunks':  'sudamerica/peru/monitor/library_images/monthly/chunks',
    'gcs_monthly_mosaics': 'sudamerica/peru/monitor/library_images/monthly/mosaics',
    'gcs_yearly_chunks':   'sudamerica/peru/monitor/library_images/yearly/chunks',
    'gcs_yearly_mosaics':  'sudamerica/peru/monitor/library_images/yearly/mosaics',
    'gcs_models':          'sudamerica/peru/monitor/models',
    'gcs_samples':         'sudamerica/peru/monitor/samples',

    # ── Configuración de Sentinel-2
    'sensor':         'COPERNICUS/S2_SR_HARMONIZED',
    'cs_plus':        'GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED',
    'cs_threshold':   0.40,

    # ── Buffer de focos de incendio (Sudamérica)
    'focus_buffer': 'projects/workspace-ipam/assets/BUFFER-DOUBLE-MONTHLY-FOCUS-OF-INPE-SULAMERICA',

    # ── Bandas del mosaico
    # Todas las bandas espectrales almacenadas en el mosaico → byte (dividir(100), rango 0–100, base-10)
    # dayOfYear → int16, sin conversión (1–366)
    'bands_spectral': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'],
    'bands_all':      ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'],

    # ── Rutas locales (para el mosaico nacional e IPAM-local)
    # Similar a /content/ en Colab, usamos una carpeta de trabajo local rápida
    # Se recomienda fuera de OneDrive para evitar latencia de sincronización
    'local_temp_dir': 'C:/mapbiomas_fire_temp',

    # ── Bandas del modelo: valores predeterminados siempre activos + extras opcionales
    # El usuario selecciona en el momento del entrenamiento/clasificando
    'bands_model_default':  ['red', 'nir', 'swir1', 'swir2'],
    'bands_model_optional': ['blue', 'green', 'dayOfYear'],

    # Mapeo de bandas de Sentinel-2 (crudo → nombres estándar)
    's2_bands_in':  ['B2',   'B3',    'B4',  'B8',  'B11',   'B12'],
    's2_bands_out': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'],

    # ── Escala: Valores crudos S2 SR 0–10000 → dividir(100) → 0–100 → byte
    'spectral_scale_factor': 100,

    # ── Tamaño de la cuadrícula (~1/4 de escena Landsat ≈ 92km)
    'tile_size_deg': 0.83,

    # ── Salida de clasificación
    # Los píxeles quemados obtienen el valor = dayOfYear (no binario 1)
    # No quemado = 0 / enmascarado
    'classification_output': 'day_of_year',  # opciones: 'binary' | 'day_of_year'

    # ── Arquitectura del modelo TF (misma que la referencia version_02)
    'model_layers': [7, 14, 7, 14, 7],
    'model_lr':     0.001,
    'model_batch':  1000,
    'model_iters':  7000,
    'model_split':  0.70,   # 70% entrenamiento / 30% prueba
}


# ─── RUTAS DERIVADAS ──────────────────────────────────────────────────────────

def gcs_path(subpath):
    """Devolver la ruta completa gs:// para una subruta de GCS."""
    return f"gs://{CONFIG['bucket']}/{subpath}"


def monthly_chunk_path(year, month):
    return f"{CONFIG['gcs_monthly_chunks']}/{year}/{month:02d}"

def monthly_mosaic_path(year, month):
    return f"{CONFIG['gcs_monthly_mosaics']}/{year}/{month:02d}"

def yearly_chunk_path(year):
    return f"{CONFIG['gcs_yearly_chunks']}/{year}"

def yearly_mosaic_path(year):
    return f"{CONFIG['gcs_yearly_mosaics']}/{year}"

def mosaic_name(year, month=None, period='monthly'):
    country = CONFIG['country']
    if period == 'monthly' and month is not None:
        return f"s2_fire_{country}_{year}_{month:02d}"
    return f"s2_fire_{country}_{year}"

def classification_name(regions, version, year, month=None):
    country = CONFIG['country']
    regions_str = '_'.join(regions)
    if month is not None:
        return f"burned_area_s2_{country}_{regions_str}_{version}_{year}_{month:02d}"
    return f"burned_area_s2_{country}_{regions_str}_{version}_{year}"

def model_path(version, region):
    return f"{CONFIG['gcs_models']}/{version}/{region}"


# ─── AYUDAS DE SISTEMA (Local) ────────────────────────────────────────────────

def get_temp_dir():
    """Retornar la ruta del directorio temporal local, creándolo si no existe."""
    path = CONFIG.get('local_temp_dir', os.path.join(os.path.expanduser("~"), "mapbiomas_fire_temp"))
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            print(f"⚠️ No se pudo crear {path}, usando temporal del sistema: {e}")
            import tempfile
            return tempfile.gettempdir()
    return path

def check_command_exists(cmd):
    """Verificar si un comando está disponible en el PATH del sistema."""
    import shutil
    return shutil.which(cmd) is not None


# ─── AYUDAS DE EE ─────────────────────────────────────────────────────────────

def get_country_geometry():
    """Devolver la geometría EE de todo el país (unión de todas las regiones)."""
    fc = ee.FeatureCollection(CONFIG['asset_regions'])
    return fc.geometry()

def get_region_geometry(region_name):
    """Devolver la geometría EE de una región específica por nombre."""
    fc = ee.FeatureCollection(CONFIG['asset_regions']) \
           .filter(ee.Filter.eq('region_nam', region_name))
    return fc.geometry()

def list_regions():
    """Devolver la lista ordenada de nombres de regiones."""
    fc = ee.FeatureCollection(CONFIG['asset_regions'])
    names = fc.aggregate_array('region_nam').getInfo()
    return sorted(names)


# ─── IMPRIMIR RESUMEN ─────────────────────────────────────────────────────────

def print_config():
    print("=" * 60)
    print("  MapBiomas Fuego Monitor — Sentinel-2")
    print(f"  País      : {CONFIG['country'].upper()}")
    print(f"  Proyecto  : {CONFIG['ee_project']}")
    print(f"  Bucket    : gs://{CONFIG['bucket']}")
    print("=" * 60)
    print(f"  Sensor        : {CONFIG['sensor']}")
    print(f"  Umbral CS+    : ≥ {CONFIG['cs_threshold']}")
    print(f"  Bandas espec. : {CONFIG['bands_spectral']}")
    print(f"  Factor escala : ÷{CONFIG['spectral_scale_factor']} → byte (0–100)")
    print(f"  dayOfYear     : int16 (sin conversión)")
    print(f"  Tamaño cuad.  : {CONFIG['tile_size_deg']}° (~92km)")
    print(f"  Salida clasif : {CONFIG['classification_output']}")
    print("=" * 60)
