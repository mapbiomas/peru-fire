"""
M0 - Global Configuration and Authentication
MapBiomas Fire Monitor
"""
import ee
import os
import warnings
import logging

# Silenciar avisos de autenticacao do Google e loggers verbosos do GCSFS
warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")
logging.getLogger("google.auth").setLevel(logging.ERROR)
logging.getLogger("gcsfs").setLevel(logging.CRITICAL)
logging.getLogger("fsspec").setLevel(logging.CRITICAL)

# ---------------------------------------------------------------------------
# Parameter descriptions (for validation)
# ---------------------------------------------------------------------------

_PARAM_DESCRIPTIONS = {
    'country':             'codigo do pais/regiao (ex: "peru", "bolivia")',
    'gcs_bucket':          'nome do bucket Google Cloud Storage (ex: "mapbiomas-fire")',
    'gcs_library_images_prefix': 'pasta GCS onde ficam as imagens base/LIBRARY_IMAGES (ex: "sudamerica/peru/CATALOG_01")',
    'gcs_campaigns_prefix':'pasta GCS onde ficam as campanhas (ex: "sudamerica/peru/CATALOG_01")',
    'gee_project':         'GEE Cloud Project ID (ex: "mapbiomas-peru")',
    'gee_library_images_prefix': 'GEE asset path para imagens (ex: "projects/mapbiomas-peru/assets/FIRE/CATALOG_01")',
    'gee_campaigns_prefix':'GEE asset path para campanhas (ex: "projects/mapbiomas-peru/assets/FIRE/CATALOG_01")',
    'campaign':            'campanha ativa (ex: "MONITOR_01", "WATER_01")',
    'asset_regions':       'GEE FeatureCollection com geometria das regioes (ex: "projects/.../CATALOG_01/MONITOR_01/AUXILIARY/regiones_fuego_peru_v1")',
}

# ---------------------------------------------------------------------------
# CONFIG builder
# ---------------------------------------------------------------------------

def _make_config(
    country,
    bucket,
    gcs_library_images_prefix,
    gcs_campaigns_prefix,
    gee_project,
    gee_library_images_prefix,
    gee_campaigns_prefix,
    campaign,
    asset_regions,
):
    """Build the CONFIG dict from project-level parameters. All required."""
    return {
        'country': country,
        'bucket': bucket,
        'gee_project': gee_project,
        'campaign': campaign,
        'asset_regions': asset_regions,
        'mosaic_methods': ['minnbr'],

        # --- GCS prefixos ---
        'gcs_library_images_prefix': gcs_library_images_prefix,
        'gcs_campaigns_prefix':     gcs_campaigns_prefix,

        # --- GCS paths derivados ---
        'gcs_library_images': f"{gcs_library_images_prefix}/LIBRARY_IMAGES",
        'gcs_cache':          f"{gcs_campaigns_prefix}/.CACHE",

        # --- GEE prefixos ---
        'gee_library_images_prefix': gee_library_images_prefix,
        'gee_campaigns_prefix':     gee_campaigns_prefix,

        # Processing params
        'bands_model_default': ['red', 'nir', 'swir1', 'swir2'],
        'bands_all': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'],
    }


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def _single(val):
    """If val is a list, return first element; otherwise return val as-is."""
    return val[0] if isinstance(val, list) else val

# Deve ser inicializado via set_global_opts()
CONFIG = None

GLOBAL_OPTS = {
    'SENSOR': ['landsat'],
    'PERIODICITY': ['yearly'],
    'MOSAIC_METHOD': 'minnbr',
    'PERSONAL_TASK_FLAG': 'CATALOG',
    'FIRE_POTENTIAL_FILTER': False,
}


# ---------------------------------------------------------------------------
# Dynamic path helpers (campaign-aware)
# ---------------------------------------------------------------------------

def gcs_samples_path(campaign=None):
    c = campaign or CONFIG['campaign']
    return f"{CONFIG['gcs_campaigns_prefix']}/{c}/LIBRARY_SAMPLES"

def gcs_models_path(campaign=None):
    c = campaign or CONFIG['campaign']
    return f"{CONFIG['gcs_campaigns_prefix']}/{c}/LIBRARY_MODELS"

def gcs_classifications_path(campaign=None):
    c = campaign or CONFIG['campaign']
    return f"{CONFIG['gcs_campaigns_prefix']}/{c}/LIBRARY_CLASSIFICATIONS"

def gee_samples_path(campaign=None):
    c = campaign or CONFIG['campaign']
    return f"{CONFIG['gee_campaigns_prefix']}/{c}/LIBRARY_SAMPLES"

def gee_classifications_path(campaign=None):
    c = campaign or CONFIG['campaign']
    return f"{CONFIG['gee_campaigns_prefix']}/{c}/LIBRARY_CLASSIFICATIONS"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

_AUTHENTICATED = False
_GCS_CREDENTIALS = None


def authenticate(project='mapbiomas-peru'):
    """Autenticar com Google Earth Engine e GCS. Deve ser chamado antes de set_global_opts()."""
    global _AUTHENTICATED, _GCS_CREDENTIALS
    
    if _AUTHENTICATED:
        return
    
    import ee

    if getattr(ee.data, '_credentials', None):
        _AUTHENTICATED = True
        return
    
    # Deteccao de ambiente Colab para autenticacao GCS
    try:
        import google.colab
        print("[COLAB] Detected Google Colab environment. Authenticating user...")
        from google.colab import auth
        auth.authenticate_user()
        import google.auth
        _GCS_CREDENTIALS, _ = google.auth.default()
    except ImportError:
        pass  # Ambiente local, assume Application Default Credentials (ADC)
    
    try:
        ee.Initialize(project=project)
        print("[GEE] Inicializado.")
    except Exception:
        print("GEE session expired or null. Starting authentication...")
        ee.Authenticate()
        ee.Initialize(project=project)
        print("[GEE] Authenticated successfully.")
    
    from M_gcs import authenticate as _mgcs_auth
    _mgcs_auth()
    print("[GCS] GCS/ADC authentication configured.")
    _AUTHENTICATED = True


_fs_instance = None

def _get_fs():
    """Retorna uma instancia GCSFileSystem (lazy, read-only)."""
    from M_gcs import _get_fs as _mgcs_get_fs
    return _mgcs_get_fs()


# ---------------------------------------------------------------------------
# GCS (gsutil) helpers
# ---------------------------------------------------------------------------

def _gcs_download(gcs_rel_path, local_path):
    from M_gcs import download
    download(gcs_rel_path, local_path)


def _gcs_upload(local_path, gcs_rel_path):
    from M_gcs import upload
    upload(local_path, gcs_rel_path)


# ---------------------------------------------------------------------------
# set_global_opts
# ---------------------------------------------------------------------------

def set_global_opts(
    # === Obrigatorios ===
    country,
    gcs_bucket,
    gcs_library_images_prefix,
    gcs_campaigns_prefix,
    gee_project,
    gee_library_images_prefix,
    gee_campaigns_prefix,
    campaign,
    asset_regions,

    # === Opcionais (pipeline) ===
    sensor=['sentinel2'],
    periodicity=['monthly'],
    mosaic_methods=None,
    personal_task_flag='MONITOR',
    language='en',
    clean_cache=False,
):
    """Configure global processing options and project paths.

    All required parameters must be provided explicitly.
    No defaults for project-level configuration.
    """
    global GLOBAL_OPTS, CONFIG

    # Build CONFIG
    CONFIG = _make_config(
        country=country,
        bucket=gcs_bucket,
        gcs_library_images_prefix=gcs_library_images_prefix,
        gcs_campaigns_prefix=gcs_campaigns_prefix,
        gee_project=gee_project,
        gee_library_images_prefix=gee_library_images_prefix,
        gee_campaigns_prefix=gee_campaigns_prefix,
        campaign=campaign,
        asset_regions=asset_regions,
    )

    GLOBAL_OPTS['SENSOR'] = sensor if isinstance(sensor, list) else [sensor]
    GLOBAL_OPTS['PERIODICITY'] = periodicity if isinstance(periodicity, list) else [periodicity]
    GLOBAL_OPTS['PERSONAL_TASK_FLAG'] = personal_task_flag
    GLOBAL_OPTS['LANGUAGE'] = language

    # Aplica filtro de metodos de mosaico se passado
    if mosaic_methods is not None:
        from M_mosaics import all_methods as _all_mosaic_methods
        valid = set(_all_mosaic_methods())
        CONFIG['mosaic_methods'] = [m for m in mosaic_methods if m in valid]

    from M_lang import L
    L.load_locale(language)

    mosaics_str = ', '.join(CONFIG['mosaic_methods'])
    sensor_str = ', '.join(s.upper() if isinstance(s, str) else str(s).upper() for s in sensor)
    period_str = ', '.join(p.upper() if isinstance(p, str) else str(p).upper() for p in periodicity)
    print(f"Global options: Sensor(s): {sensor_str} | Period(s): {period_str} | Mosaics: {mosaics_str} | Campaign: {CONFIG['campaign']} | Task Flag: {personal_task_flag}")

    if clean_cache:
        try:
            from M_cache import CacheManager
            CacheManager.clear()
            
            from M_gcs import exists, rm as gcs_rm
            cache_file = "state.json"
            gcs_path = f"gs://{CONFIG['bucket']}/{CONFIG['gcs_cache']}/{cache_file}"
            if exists(gcs_path):
                gcs_rm(gcs_path)
                print(f"GCS cache cleared: {gcs_path}")
            else:
                print("GCS cache not found (nothing to clear).")
        except Exception as e:
            print(f"Warning while clearing cache: {e}")
    
    # Sincronizar cache automaticamente apos M0
    try:
        from M_cache import CacheManager
        state = CacheManager.get_state()
        if not state.get('updated_at') or not state.get('cogs_monthly'):
            CacheManager.build_full_cache()
    except Exception as e:
        print(f"Cache sync deferred (GCS auth pending). Run manual sync in M1/M2 if needed.")
    
    return GLOBAL_OPTS


# ---------------------------------------------------------------------------
# GCS path generators
# ---------------------------------------------------------------------------

def _gcs_library_base():
    """Retorna o base path da library de imagens (sem sensor/period)."""
    sensor = _single(GLOBAL_OPTS['SENSOR']).upper()
    return f"{CONFIG['gcs_library_images']}/{sensor}"

def _gcs_models_base():
    """Base folder for trained models in GCS."""
    return gcs_models_path()

def _gcs_mosaic_path(periodicity, temporal_id, mosaic=None):
    base = _gcs_library_base()
    period = periodicity.upper()
    m = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).upper()
    return f"{base}/{period}/{m}/{temporal_id}"

def monthly_mosaic_path(year, month, mosaic=None):
    temporal_id = f"{year}_{month:02d}"
    return _gcs_mosaic_path("monthly", temporal_id, mosaic=mosaic)

def yearly_mosaic_path(year, mosaic=None):
    temporal_id = f"{year}"
    return _gcs_mosaic_path("yearly", temporal_id, mosaic=mosaic)

def monthly_chunk_path(year, month, mosaic='minnbr', sensor=None):
    s = (sensor or _single(GLOBAL_OPTS['SENSOR'])).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/MONTHLY/{mosaic.upper()}/{year}_{month:02d}/CHUNKS"

def yearly_chunk_path(year, mosaic='minnbr', sensor=None):
    s = (sensor or _single(GLOBAL_OPTS['SENSOR'])).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/ANNUALLY/{mosaic.upper()}/{year}/CHUNKS"

def monthly_cog_path(year, month, mosaic='minnbr', sensor=None):
    s = (sensor or _single(GLOBAL_OPTS['SENSOR'])).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/MONTHLY/{mosaic.upper()}/{year}_{month:02d}/COG"

def yearly_cog_path(year, mosaic='minnbr', sensor=None):
    s = (sensor or _single(GLOBAL_OPTS['SENSOR'])).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/ANNUALLY/{mosaic.upper()}/{year}/COG"

def model_path(training_id, shortname, region=None):
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    t_id = str(training_id)
    if t_id.startswith('training_'):
        asset_name = t_id
    else:
        asset_name = f"training_{t_id}_{shortname}_{sensor}"
    
    base = f"{_gcs_models_base()}/{asset_name}"
    if region:
        return f"{base}/{region}"
    return base

def gcs_path(relative):
    """Retorna URL gs:// completa."""
    return f"gs://{CONFIG['bucket']}/{relative}"


# ---------------------------------------------------------------------------
# GEE path generators
# ---------------------------------------------------------------------------

def get_asset_mosaic_collection(sensor=None, periodicity=None, band=None, period=None, mosaic=None):
    period = period or periodicity or _single(GLOBAL_OPTS['PERIODICITY'])
    folder_period = period.upper()
    m_name = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).upper()
    
    sensor_name = (sensor or _single(GLOBAL_OPTS['SENSOR'])).upper()
    
    path = f"{CONFIG['gee_library_images_prefix']}/LIBRARY_IMAGES/{sensor_name}/{folder_period}/{m_name}"
    
    if band:
        path = f"{path}/{band.lower()}"
    return path


# ---------------------------------------------------------------------------
# Nomenclature
# ---------------------------------------------------------------------------

def mosaic_name(year, month=None, period=None, band=None, mosaic=None, sensor=None):
    country = CONFIG['country']
    s = (sensor or _single(GLOBAL_OPTS['SENSOR'])).lower()
    m = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).lower()
    
    date_str = f"{year}_{month:02d}" if month else f"{year}"
    
    if band:
        return f"image_{country}_fire_{s}_{m}_{band}_{date_str}"
    return f"image_{country}_fire_{s}_{m}_{date_str}"

def get_temp_dir(subdir=None):
    is_colab = 'COLAB_RELEASE_TAG' in os.environ
    base = '/content/TEMPORARY' if is_colab else os.path.abspath('TEMPORARY')
    os.makedirs(base, exist_ok=True)
    if subdir:
        path = os.path.join(base, subdir)
        os.makedirs(path, exist_ok=True)
        return path
    return base

def check_command_exists(cmd):
    import shutil
    return shutil.which(cmd) is not None or shutil.which(cmd + ".py") is not None

def ensure_gdal_path():
    import os, shutil, platform, sys
    
    gdal_cmds = ['gdalbuildvrt', 'gdal_translate']
    missing = [cmd for cmd in gdal_cmds if shutil.which(cmd) is None]
    
    if not missing:
        return
    
    candidate_dirs = []
    
    if platform.system() == 'Windows':
        py_prefix = sys.prefix
        candidate_dirs += [
            os.path.join(py_prefix, 'Library', 'bin'),
            os.path.join(py_prefix, 'Scripts'),
        ]
        home = os.path.expanduser('~')
        for conda_root in [
            os.path.join(home, 'miniconda3'),
            os.path.join(home, 'anaconda3'),
            os.path.join(home, 'AppData', 'Local', 'miniconda3'),
            r'C:\OSGeo4W\bin',
            r'C:\Program Files\GDAL',
        ]:
            candidate_dirs.append(os.path.join(conda_root, 'Library', 'bin'))
            candidate_dirs.append(os.path.join(conda_root, 'Scripts'))
            candidate_dirs.append(conda_root)
    else:
        py_prefix = sys.prefix
        candidate_dirs += [
            os.path.join(py_prefix, 'bin'),
            '/usr/bin', '/usr/local/bin',
        ]
    
    for d in candidate_dirs:
        if os.path.isdir(d):
            test_bin = 'gdalbuildvrt.exe' if platform.system() == 'Windows' else 'gdalbuildvrt'
            if os.path.exists(os.path.join(d, test_bin)):
                os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
                print(f"GDAL found and added to PATH: {d}")
                return
    
    print(f"Warning: GDAL utilities not found: {missing}")
    if 'COLAB_RELEASE_TAG' in os.environ or 'COLAB_BACKEND_VERSION' in os.environ:
        print("Tip: On Google Colab, run: !apt-get install -y gdal-bin")
    elif platform.system() == 'Windows':
        print("Tip: On Windows, ensure GDAL is in your PATH or use Conda environment (gdal).")

def sample_asset_name(temporal_id, version_id):
    clean_version = version_id.replace('sample_', '')
    return f"sample_{clean_version}_{temporal_id}"

def get_asset_samples(temporal_id, version_id):
    asset = sample_asset_name(temporal_id, version_id)
    return f"{gee_samples_path()}/{asset}"

def get_gcs_samples(temporal_id, version_id):
    asset = sample_asset_name(temporal_id, version_id)
    return f"{gcs_samples_path()}/{asset}"

def get_asset_regional(region_id, training_id, temporal_id):
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_upper = sensor.upper() + suffix
    period = _single(GLOBAL_OPTS['PERIODICITY']).upper()
    asset_name = f"region_{region_id}_training_{training_id}_{sensor}_{temporal_id}"
    return f"{CONFIG['gee_library_images_prefix']}/LIBRARY_IMAGES/{sensor_upper}/{period}/burned_day_of_year_regional/{asset_name}"

def get_gcs_regional(region_id, training_id, temporal_id):
    base = _gcs_library_base()
    period = _single(GLOBAL_OPTS['PERIODICITY']).lower()
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    asset_name = f"region_{region_id}_training_{training_id}_{sensor}_{temporal_id}"
    return f"{base}/{sensor}/{period}/burned_day_of_year_regional/{asset_name}"

def get_asset_candidate(candidate_id, temporal_id):
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_upper = sensor.upper() + suffix
    period = _single(GLOBAL_OPTS['PERIODICITY']).upper()
    asset_name = f"candidate_{candidate_id}_{sensor}_{temporal_id}"
    return f"{CONFIG['gee_library_images_prefix']}/LIBRARY_IMAGES/{sensor_upper}/{period}/burned_day_of_year_candidates/{asset_name}"

def get_gcs_candidate(candidate_id, temporal_id):
    base = _gcs_library_base()
    period = _single(GLOBAL_OPTS['PERIODICITY']).lower()
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    asset_name = f"candidate_{candidate_id}_{sensor}_{temporal_id}"
    return f"{base}/{sensor}/{period}/burned_day_of_year_candidates/{asset_name}"

def get_asset_official(temporal_id):
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_upper = sensor.upper() + suffix
    period = _single(GLOBAL_OPTS['PERIODICITY']).upper()
    asset_name = f"burned_day_of_year_{sensor}_{temporal_id}"
    return f"{CONFIG['gee_library_images_prefix']}/LIBRARY_IMAGES/{sensor_upper}/{period}/burned_day_of_year_official/{asset_name}"

def get_gcs_official(temporal_id):
    base = _gcs_library_base()
    period = _single(GLOBAL_OPTS['PERIODICITY']).lower()
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    asset_name = f"burned_day_of_year_{sensor}_{temporal_id}"
    return f"{base}/{sensor}/{period}/burned_day_of_year_official/{asset_name}.tif"

def classification_name(periodicity, year, month=None, version=None):
    """(DEPRECATED)"""
    country = CONFIG['country']
    sensor = _single(GLOBAL_OPTS['SENSOR']).lower()
    suffix = "_buffer" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    ver = version or 'version_01'
    region = "r01"
    return f"class_{sensor}{suffix}_{country}_{region}_{year}_{month:02d}_{ver}" if month else f"class_{sensor}{suffix}_{country}_{region}_{year}_{ver}"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def get_country_geometry():
    return ee.FeatureCollection(CONFIG['asset_regions']).geometry()

def get_fire_reference(year):
    """(DEPRECATED) Requer asset_fire_ref no CONFIG."""
    ref = CONFIG.get('asset_fire_ref')
    if not ref:
        raise RuntimeError("asset_fire_ref not configured.")
    return ee.Image(f"{ref}{year}")

def get_hotspots_collection(year, month=None):
    """(DEPRECATED) Requer asset_hotspots no CONFIG."""
    col = CONFIG.get('asset_hotspots')
    if not col:
        raise RuntimeError("asset_hotspots not configured.")
    col = ee.FeatureCollection(col)
    col = col.filter(ee.Filter.eq('year', year))
    if month:
        col = col.filter(ee.Filter.eq('month', month))
    return col

def get_sensor_scale(sensor=None):
    sensor = (sensor or _single(GLOBAL_OPTS['SENSOR'])).lower()
    scales = {
        'sentinel2': 10,
        'landsat': 30,
        'hls': 30,
        'modis': 250
    }
    return scales.get(sensor, 30)

def set_country(country):
    """Update country while preserving project-level params."""
    global CONFIG
    if CONFIG is None:
        raise RuntimeError("CONFIG not initialized. Call set_global_opts() first.")
    CONFIG['country'] = country
    return CONFIG

def set_edit_mode(mode):
    global GLOBAL_OPTS
    GLOBAL_OPTS['EDIT_MODE'] = mode

def is_edit_mode():
    return GLOBAL_OPTS.get('EDIT_MODE', False)

def print_config():
    if CONFIG is None:
        print("CONFIG not initialized. Call set_global_opts() first.")
        return
    sensor_str = ', '.join(GLOBAL_OPTS['SENSOR']) if isinstance(GLOBAL_OPTS['SENSOR'], list) else str(GLOBAL_OPTS['SENSOR'])
    period_str = ', '.join(GLOBAL_OPTS['PERIODICITY']) if isinstance(GLOBAL_OPTS['PERIODICITY'], list) else str(GLOBAL_OPTS['PERIODICITY'])
    print(f"Country: {CONFIG['country'].upper()}")
    print(f"GEE Project: {CONFIG['gee_project']}")
    print(f"GCS Bucket: {CONFIG['bucket']}")
    print(f"GCS Images: {CONFIG['gcs_library_images_prefix']}")
    print(f"GCS Campaigns: {CONFIG['gcs_campaigns_prefix']}")
    print(f"GEE Images: {CONFIG['gee_library_images_prefix']}")
    print(f"GEE Campaigns: {CONFIG['gee_campaigns_prefix']}")
    print(f"Campaign: {CONFIG['campaign']}")
    print(f"Asset Regions: {CONFIG['asset_regions']}")
    print(f"Sensor(s): {sensor_str} | Period(s): {period_str} | Task Flag: {GLOBAL_OPTS['PERSONAL_TASK_FLAG']}")
