"""
M0 - Global Configuration and Authentication
MapBiomas Fire Monitor
"""
import ee
import os
import warnings
import logging

# Silenciar avisos de autenticação do Google e loggers verbosos do GCSFS
warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")
logging.getLogger("google.auth").setLevel(logging.ERROR)
logging.getLogger("gcsfs").setLevel(logging.CRITICAL)
logging.getLogger("fsspec").setLevel(logging.CRITICAL)

# ─── DEFAULT CONFIG ─────────────────────────────────────────

def _make_config(country='peru', bucket='mapbiomas-fire', gcs_project='mapbiomas-fire-485203',
                  version='version_01', gee_project='mapbiomas-peru',
                  gcs_catalog_prefix=None, gee_asset_repo=None):
    """Build the CONFIG dict from project-level parameters."""
    if gcs_catalog_prefix is None:
        gcs_catalog_prefix = f"sudamerica/{country}/CATALOG_01"
    if gee_asset_repo is None:
        gee_asset_repo = f"projects/{gee_project}/assets/FIRE/CATALOG_01"

    return {
        'country': country,
        'bucket': bucket,
        'gcs_project': gcs_project,
        'version': version,
        'gee_project': gee_project,
        'gee_asset_repo': gee_asset_repo,
        'gcs_catalog_prefix': gcs_catalog_prefix,
        'mosaic_methods': ['minnbr', 'minnbr_buffer', 'median', 'minndvi'],

        # --- GCS paths (derived) ---
        'gcs_library_images': f"{gcs_catalog_prefix}/LIBRARY_IMAGES",
        'gcs_library_samples': f"{gcs_catalog_prefix}/LIBRARY_SAMPLES",
        'gcs_library_models': f"{gcs_catalog_prefix}/LIBRARY_MODELS",
        'gcs_library_classifications': f"{gcs_catalog_prefix}/LIBRARY_CLASSIFICATIONS",
        'gcs_cache': f"{gcs_catalog_prefix}/.CACHE",
        'gcs_chunks': f"{gcs_catalog_prefix}/CHUNKS",

        # --- GEE paths (derived) ---
        'asset_monitor_base': gee_asset_repo,

        # --- Country-specific GEE assets (overridable) ---
        'asset_regions': f'projects/{gee_project}/assets/FIRE/AUXILIARY_DATA/regiones_fuego_{country}_v1',
        'asset_fire_ref': f'projects/{gee_project}/assets/FIRE/AUXILIARY_DATA/REFERENCES/cicatrizes_fuego_reference_2016_2024/cicatriz_fuego_',
        'asset_hotspots': f'projects/{bucket}/assets/DATABASE/monthly-focus-sul-america',

        # Processing params
        'bands_model_default': ['red', 'nir', 'swir1', 'swir2'],
        'bands_all': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'],
    }


# ─── CURRENT CONFIG ─────────────────────────────────────────

CONFIG = _make_config()  # Default: Peru

GLOBAL_OPTS = {
    'SENSOR': 'landsat',
    'PERIODICITY': 'yearly',
    'MOSAIC_METHOD': 'minnbr',
    'PERSONAL_TASK_FLAG': 'CATALOG',
    'SAMPLING_CAMPAIGN': 'monitor_01'
}


# ─── AUTHENTICATION ─────────────────────────────────────────

_AUTHENTICATED = False

def authenticate(project='mapbiomas-peru', clean_cache=False):
    """Autenticar com Google Earth Engine e GCS (Suporta Local e Colab)."""
    global _AUTHENTICATED

    if clean_cache:
_AUTHENTICATED = False
_GCS_CREDENTIALS = None
        from M_cache import CacheManager
        CacheManager.clear()
    
    if _AUTHENTICATED:
        return
    
    import ee

    if getattr(ee.data, '_credentials', None):
        _AUTHENTICATED = True
        return
    
    # Detecção de ambiente Colab para autenticação GCS
    try:
        import google.colab
        print("[COLAB] Detected Google Colab environment. Authenticating user...")
        from google.colab import auth
        auth.authenticate_user()
        import google.auth
        global _GCS_CREDENTIALS
        _GCS_CREDENTIALS, _ = google.auth.default()
    except ImportError:
        pass # Ambiente local, assume Application Default Credentials (ADC)
    
    try:
        ee.Initialize(project=project)
        print("[GEE] Inicializado.")
    except Exception:
        print("GEE session expired or null. Starting authentication...")
        ee.Authenticate()
        ee.Initialize(project=project)
        print("[GEE] Authenticated successfully.")
    
    print("[GCS] GCS/ADC authentication configured.")
    _AUTHENTICATED = True


def _get_fs():
    """Retorna uma instância GCSFileSystem corretamente autenticada para qualquer ambiente."""
    import gcsfs
    project = CONFIG['gcs_project']
    is_colab = 'COLAB_RELEASE_TAG' in os.environ or 'COLAB_BACKEND_VERSION' in os.environ

    if is_colab:
        if _GCS_CREDENTIALS is not None:
            return gcsfs.GCSFileSystem(project=project, token=_GCS_CREDENTIALS, requests_timeout=5)
        return gcsfs.GCSFileSystem(project=project, requests_timeout=5)
    else:
        return gcsfs.GCSFileSystem(project=project, requests_timeout=10)

def set_global_opts(sensor='landsat', periodicity='yearly', personal_task_flag='MONITOR', sampling_campaign='monitor_01', clean_cache=False, language='en',
                    country=None, gee_project=None, gee_asset_repo=None,
                    gcs_bucket=None, gcs_project=None, gcs_catalog_prefix=None):
    """
    Configure global processing options and project paths.

    Args:
        sensor: 'landsat', 'sentinel2', 'hls' or 'modis'
        periodicity: 'yearly' or 'monthly'
        personal_task_flag: Prefix for GEE tasks (e.g. 'MONITOR')
        sampling_campaign: Sampling campaign ID (e.g. 'monitor_01')
        clean_cache: Reset local + GCS cache at startup
        language: Language code: 'en' (default), 'es', 'pt', 'fr', 'id'
        country: Country code (e.g. 'peru', 'brazil'). If None, keeps current.
        gee_project: GEE project name (e.g. 'mapbiomas-peru')
        gee_asset_repo: Full GEE asset path for CATALOG_01
                        (e.g. 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01')
        gcs_bucket: GCS bucket name (e.g. 'mapbiomas-fire')
        gcs_project: GCS project name (e.g. 'mapbiomas-fire-485203')
        gcs_catalog_prefix: GCS prefix for CATALOG_01
                            (e.g. 'sudamerica/peru/CATALOG_01')
    """
    global GLOBAL_OPTS, CONFIG

    # Rebuild CONFIG if any project-level param is provided
    needs_rebuild = any(x is not None for x in [country, gee_project, gee_asset_repo,
                                                 gcs_bucket, gcs_project, gcs_catalog_prefix])
    if needs_rebuild:
        CONFIG = _make_config(
            country=country or CONFIG['country'],
            bucket=gcs_bucket or CONFIG['bucket'],
            gcs_project=gcs_project or CONFIG['gcs_project'],
            gee_project=gee_project or CONFIG.get('gee_project', CONFIG['country']),
            gcs_catalog_prefix=gcs_catalog_prefix,
            gee_asset_repo=gee_asset_repo,
        )

    GLOBAL_OPTS['SENSOR'] = sensor
    GLOBAL_OPTS['PERIODICITY'] = periodicity
    GLOBAL_OPTS['PERSONAL_TASK_FLAG'] = personal_task_flag
    GLOBAL_OPTS['SAMPLING_CAMPAIGN'] = sampling_campaign
    GLOBAL_OPTS['LANGUAGE'] = language

    from M_lang import L
    L.load_locale(language)
    
    print(f"Global options: {sensor.upper()} | {periodicity.upper()} | Campaign: {sampling_campaign} | Task Flag: {personal_task_flag}")

    if clean_cache:
        try:
            from M_cache import CacheManager
            CacheManager.clear()
            
            fs = _get_fs()
            cache_file = f"state.json"
            gcs_path = f"gs://{CONFIG['bucket']}/{CONFIG['gcs_cache']}/{cache_file}"
            if fs.exists(gcs_path):
                fs.rm(gcs_path)
                print(f"GCS cache cleared: {gcs_path}")
            else:
                print("GCS cache not found (nothing to clear).")
        except Exception as e:
            print(f"Warning while clearing cache: {e}")
    
    # Sincronizar cache automaticamente após M0
    try:
        from M_cache import CacheManager
        state = CacheManager.get_state()
        if not state.get('updated_at') or not state.get('cogs_monthly'):
            CacheManager.build_full_cache()
    except Exception as e:
        print(f"Cache sync deferred (GCS auth pending). Run manual sync in M1/M2 if needed.")
    
    return GLOBAL_OPTS


# ─── GENERADORES DE CAMINHOS GCS ──────────────────────────────────────────────

def _gcs_library_base():
    """Base folder for images in GCS (agrupado por sensor)."""
    sensor = GLOBAL_OPTS['SENSOR'].upper()
    return f"{CONFIG['gcs_library_images']}/{sensor}"

def _gcs_models_base():
    """Base folder for trained models in GCS (centralizado)."""
    return f"{CONFIG['gcs_library_models']}"

def _gcs_mosaic_path(periodicity, temporal_id, mosaic=None):
    """
    Padrão GCS: .../LIBRARY_IMAGES/{SENSOR}/{PERIODICITY}/{MOSAIC}/{temporal_id}/
    """
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
    """Caminho GCS para chunks mensais: {SENSOR}/{PERIOD}/{MOSAIC}/{date}/CHUNKS/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/MONTHLY/{mosaic.upper()}/{year}_{month:02d}/CHUNKS"

def yearly_chunk_path(year, mosaic='minnbr', sensor=None):
    """Caminho GCS para chunks anuais: {SENSOR}/{PERIOD}/{MOSAIC}/{date}/CHUNKS/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/ANNUALLY/{mosaic.upper()}/{year}/CHUNKS"

def monthly_cog_path(year, month, mosaic='minnbr', sensor=None):
    """Caminho GCS para COGs mensais: {SENSOR}/{PERIOD}/{MOSAIC}/{date}/COG/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/MONTHLY/{mosaic.upper()}/{year}_{month:02d}/COG"

def yearly_cog_path(year, mosaic='minnbr', sensor=None):
    """Caminho GCS para COGs anuais: {SENSOR}/{PERIOD}/{MOSAIC}/{date}/COG/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).upper()
    return f"{CONFIG['gcs_library_images']}/{s}/ANNUALLY/{mosaic.upper()}/{year}/COG"

def model_path(training_id, shortname, region=None):
    """
    GCS: GCS/{country}/.../monitor/version_01/library_images/models/{asset_name}
    Asset: training_{training_id}_{shortname}_{sensor}
    """
    sensor = GLOBAL_OPTS['SENSOR'].lower()
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


# ─── GENERADORES DE CAMINHOS GEE ──────────────────────────────────────────────

def get_asset_mosaic_collection(sensor=None, periodicity=None, band=None, period=None, mosaic=None):
    period = period or periodicity or GLOBAL_OPTS['PERIODICITY']
    folder_period = period.upper()
    m_name = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).upper()
    
    sensor_name = (sensor or GLOBAL_OPTS['SENSOR']).upper()
    
    # PADRÃO: ImageCollection por BANDA
    path = f"{CONFIG['asset_monitor_base']}/LIBRARY_IMAGES/{sensor_name}/{folder_period}/{m_name}"
    
    if band:
        path = f"{path}/{band.lower()}"
    return path


# ─── NOMENCLATURA ─────────────────────────────────────────────────────────────

def mosaic_name(year, month=None, period=None, band=None, mosaic=None, sensor=None):
    """
    Gera nome padrão para o mosaico/asset: image_{country}_fire_{sensor}_{mosaic}_{band}_{temporal_id}
    """
    country = CONFIG['country']
    s = (sensor or GLOBAL_OPTS['SENSOR']).lower()
    m = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).lower()
    
    date_str = f"{year}_{month:02d}" if month else f"{year}"
    
    if band:
        return f"image_{country}_fire_{s}_{m}_{band}_{date_str}"
    return f"image_{country}_fire_{s}_{m}_{date_str}"

def gcs_chunks_prefix(periodicity):
    """Retorna o prefixo da pasta de chunks no GCS para listagem."""
    return f"{CONFIG['gcs_chunks']}/{periodicity}"

def get_temp_dir():
    """Cria e retorna o caminho para a pasta temporária local."""
    tmp = "temp_mosaics"
    if not os.path.exists(tmp):
        os.makedirs(tmp)
    return tmp

def check_command_exists(cmd):
    """Verifica se um comando (ex: gdal_merge) existe no sistema."""
    import shutil
    return shutil.which(cmd) is not None or shutil.which(cmd + ".py") is not None

def ensure_gdal_path():
    """Garante que as ferramentas GDAL estão acessíveis, adicionando ao PATH se necessário."""
    import os, shutil, platform, sys
    
    gdal_cmds = ['gdalbuildvrt', 'gdal_translate']
    missing = [cmd for cmd in gdal_cmds if shutil.which(cmd) is None]
    
    if not missing:
        return  # GDAL já está no PATH
    
    # Tenta encontrar o GDAL em locais comuns (Windows / Conda / OSGeo4W)
    candidate_dirs = []
    
    if platform.system() == 'Windows':
        # Localização do ambiente Conda atual (onde o Python está rodando)
        py_prefix = sys.prefix
        candidate_dirs += [
            os.path.join(py_prefix, 'Library', 'bin'),  # Conda no Windows
            os.path.join(py_prefix, 'Scripts'),
        ]
        # Locais comuns de instalação manual
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
        # Linux/Mac: locais comuns do conda
        py_prefix = sys.prefix
        candidate_dirs += [
            os.path.join(py_prefix, 'bin'),
            '/usr/bin', '/usr/local/bin',
        ]
    
    # Testa cada diretório candidato
    for d in candidate_dirs:
        if os.path.isdir(d):
            test_bin = 'gdalbuildvrt.exe' if platform.system() == 'Windows' else 'gdalbuildvrt'
            if os.path.exists(os.path.join(d, test_bin)):
                os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
                print(f"GDAL found and added to PATH: {d}")
                return
    
    # Se ainda não encontrou, emite aviso com instruções
    print(f"Warning: GDAL utilities not found: {missing}")
    if 'COLAB_RELEASE_TAG' in os.environ or 'COLAB_BACKEND_VERSION' in os.environ:
        print("Tip: On Google Colab, run: !apt-get install -y gdal-bin")
    elif platform.system() == 'Windows':
        print("Tip: On Windows, ensure GDAL is in your PATH or use Conda environment (gdal).")
        print(f"   Tip: Activate the correct environment with 'conda activate <env>' antes de iniciar o Jupyter.")

def sample_asset_name(temporal_id, version_id):
    """
    Garante o padrão sample_{id}_{temporal_id}
    version_id pode ser '0001' ou 'sample_0001'
    """
    clean_version = version_id.replace('sample_', '')
    return f"sample_{clean_version}_{temporal_id}"

def get_asset_samples(temporal_id, version_id):
    asset = sample_asset_name(temporal_id, version_id)
    campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'monitor_01')
    return f"{CONFIG['asset_monitor_base']}/LIBRARY_SAMPLES/{campaign}/{asset}"

def get_gcs_samples(temporal_id, version_id):
    asset = sample_asset_name(temporal_id, version_id)
    campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'monitor_01')
    return f"{CONFIG['gcs_library_samples']}/{campaign}/{asset}"

def get_asset_regional(region_id, training_id, temporal_id):
    """Retorna o path do GEE para classificações regionais."""
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_upper = sensor.upper() + suffix
    period = GLOBAL_OPTS['PERIODICITY'].upper()
    asset_name = f"region_{region_id}_training_{training_id}_{sensor}_{temporal_id}"
    return f"{CONFIG['asset_monitor_base']}/LIBRARY_IMAGES/{sensor_upper}/{period}/burned_day_of_year_regional/{asset_name}"

def get_gcs_regional(region_id, training_id, temporal_id):
    """Retorna o path do GCS para classificações regionais."""
    base = _gcs_library_base()
    period = GLOBAL_OPTS['PERIODICITY'].lower()
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    asset_name = f"region_{region_id}_training_{training_id}_{sensor}_{temporal_id}"
    return f"{base}/{sensor}/{period}/burned_day_of_year_regional/{asset_name}"

def get_asset_candidate(candidate_id, temporal_id):
    """Retorna o path do GEE para candidatos validados."""
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_upper = sensor.upper() + suffix
    period = GLOBAL_OPTS['PERIODICITY'].upper()
    asset_name = f"candidate_{candidate_id}_{sensor}_{temporal_id}"
    return f"{CONFIG['asset_monitor_base']}/LIBRARY_IMAGES/{sensor_upper}/{period}/burned_day_of_year_candidates/{asset_name}"

def get_gcs_candidate(candidate_id, temporal_id):
    """Retorna o path do GCS para candidatos validados."""
    base = _gcs_library_base()
    period = GLOBAL_OPTS['PERIODICITY'].lower()
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    asset_name = f"candidate_{candidate_id}_{sensor}_{temporal_id}"
    return f"{base}/{sensor}/{period}/burned_day_of_year_candidates/{asset_name}"

def get_asset_official(temporal_id):
    """Retorna o path do GEE para o dado oficial consolidado."""
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_upper = sensor.upper() + suffix
    period = GLOBAL_OPTS['PERIODICITY'].upper()
    asset_name = f"burned_day_of_year_{sensor}_{temporal_id}"
    return f"{CONFIG['asset_monitor_base']}/LIBRARY_IMAGES/{sensor_upper}/{period}/burned_day_of_year_official/{asset_name}"

def get_gcs_official(temporal_id):
    """Retorna o path do GCS para o dado oficial consolidado."""
    base = _gcs_library_base()
    period = GLOBAL_OPTS['PERIODICITY'].lower()
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    asset_name = f"burned_day_of_year_{sensor}_{temporal_id}"
    return f"{base}/{sensor}/{period}/burned_day_of_year_official/{asset_name}.tif"

def classification_name(periodicity, year, month=None, version=None):
    """(DEPRECATED) Usa-se agora get_asset_regional e funções associadas."""
    country = CONFIG['country']
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    suffix = "_buffer" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    ver = version or CONFIG['version']
    region = "r01" # Exemplo
    return f"class_{sensor}{suffix}_{country}_{region}_{year}_{month:02d}_{ver}" if month else f"class_{sensor}{suffix}_{country}_{region}_{year}_{ver}"


# ─── GEOMETRIA E AUXILIARES ───────────────────────────────────────────────────

def get_country_geometry():
    """Retorna a geometria do país baseada no asset de regiões."""
    return ee.FeatureCollection(CONFIG['asset_regions']).geometry()

def get_fire_reference(year):
    """Retorna asset de referência de fogo para o ano."""
    return ee.Image(f"{CONFIG['asset_fire_ref']}{year}")

def get_hotspots_collection(year, month=None):
    """Retorna coleção de focos INPE filtrada."""
    col = ee.FeatureCollection(CONFIG['asset_hotspots'])
    col = col.filter(ee.Filter.eq('year', year))
    if month:
        col = col.filter(ee.Filter.eq('month', month))
    return col

def get_sensor_scale(sensor=None):
    """Retorna a escala em metros recomendada para cada sensor."""
    sensor = (sensor or GLOBAL_OPTS['SENSOR']).lower()
    scales = {
        'sentinel2': 10,
        'landsat': 30,
        'hls': 30,
        'modis': 250
    }
    return scales.get(sensor, 30)

def set_country(country):
    """Update the global configuration for a new country while preserving project-level overrides."""
    global CONFIG
    CONFIG = _make_config(
        country=country,
        bucket=CONFIG['bucket'],
        gcs_project=CONFIG['gcs_project'],
        gee_project=CONFIG.get('gee_project', country),
        gcs_catalog_prefix=None,
        gee_asset_repo=None,
    )
    return CONFIG

def set_edit_mode(mode):
    """Ativa ou desativa o modo de edição na UI."""
    global GLOBAL_OPTS
    GLOBAL_OPTS['EDIT_MODE'] = mode

def is_edit_mode():
    """Retorna True se o modo de edição estiver ativo."""
    return GLOBAL_OPTS.get('EDIT_MODE', False)

def print_config():
    """Imprime um resumo da configuração atual."""
    print(f"Country: {CONFIG['country'].upper()}")
    print(f"GEE Project: {CONFIG.get('gee_project', 'N/A')}")
    print(f"GEE Asset Repo: {CONFIG['asset_monitor_base']}")
    print(f"GCS Bucket: {CONFIG['bucket']}")
    print(f"GCS Project: {CONFIG['gcs_project']}")
    print(f"GCS Catalog: {CONFIG['gcs_catalog_prefix']}")
    print(f"Version: {CONFIG['version']}")
    print(f"Sensor: {GLOBAL_OPTS['SENSOR']} | Period: {GLOBAL_OPTS['PERIODICITY']} | Task Flag: {GLOBAL_OPTS['PERSONAL_TASK_FLAG']} | Campaign: {GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'N/A')}")
