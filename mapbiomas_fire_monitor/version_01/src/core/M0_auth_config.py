"""
M0 - Configuração Global e Autenticação
MapBiomas Fuego Sentinel Monitor
"""
import ee
import os
import warnings
import logging

# Silenciar avisos de autenticação do Google e loggers verbosos do GCSFS
warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")
logging.getLogger("google.auth").setLevel(logging.ERROR)
logging.getLogger("gcsfs").setLevel(logging.ERROR)
logging.getLogger("fsspec").setLevel(logging.ERROR)

# ─── CONFIGURAÇÃO DO PROJETO ──────────────────────────────────────────────────

def get_config(country='peru'):
    """Retorna o dicionário de caminhos e buckets para o país escolhido."""
    if country.lower() == 'peru':
        return {
            'country': 'peru',
            'bucket': 'mapbiomas-fire',
            'gcs_project': 'mapbiomas-fire-485203',
            'version': 'version_01',
            'mosaic_methods': ['minnbr', 'minnbr_buffer', 'median', 'minndvi'],
            
            # --- CAMINHOS LEGADOS (Mantidos provisoriamente) ---
            'gcs_samples_old': 'sudamerica/peru/monitor/version_01/library_samples',
            'gcs_mosaics_old': 'sudamerica/peru/monitor/version_01/library_images',
            'gcs_models_old': 'sudamerica/peru/monitor/version_01/models',
            'gcs_classifications_old': 'sudamerica/peru/monitor/version_01/classifications',
            'gcs_filtered_old': 'sudamerica/peru/monitor/version_01/filtered',
            'asset_mosaics_base_old': 'projects/mapbiomas-mosaics/assets/FIRE',
            'asset_samples_old': 'projects/mapbiomas-peru/assets/FIRE/MONITOR_01/LIBRARY_SAMPLES',
            'asset_classification_old': 'projects/mapbiomas-peru/assets/FIRE/MONITOR_01/CLASSIFICATIONS',
            'asset_filtered_old': 'projects/mapbiomas-peru/assets/FIRE/MONITOR_01/FILTERED',
            
            # --- NOVOS CAMINHOS GCS (Arquitetura Singleband) ---
            'gcs_library_images': 'sudamerica/peru/monitor/version_01/library_images',
            'gcs_library_samples': 'sudamerica/peru/monitor/version_01/library_samples',
            'gcs_cache': 'sudamerica/peru/monitor/version_01/.cache',
            'gcs_chunks': 'sudamerica/peru/monitor/version_01/chunks',
            
            # --- NOVOS CAMINHOS GEE (Arquitetura Singleband) ---
            'asset_monitor_base': 'projects/mapbiomas-peru/assets/FIRE/MONITOR_01',
            
            # Auxiliares
            'asset_regions': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',
            'asset_fire_ref': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/REFERENCES/cicatrizes_fuego_reference_2016_2024/cicatriz_fuego_',
            'asset_hotspots': 'projects/mapbiomas-fire-485203/assets/DATABASE/monthly-focus-sul-america',
            
            # Parâmetros de Processamento
            'bands_model_default': ['red', 'nir', 'swir1', 'swir2'],
            'bands_all': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'],
        }
    else:
        raise ValueError(f"País {country} não configurado.")


# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────

def authenticate(project='mapbiomas-peru'):
    """Autenticar com Google Earth Engine e GCS (Suporta Local e Colab)."""
    import ee
    
    # Detecção de ambiente Colab para autenticação GCS
    try:
        import google.colab
        print("[COLAB] Detectado ambiente Google Colab. Autenticando usuário...")
        from google.colab import auth
        auth.authenticate_user()
    except ImportError:
        pass # Ambiente local, assume Application Default Credentials (ADC)
    
    try:
        ee.Initialize(project=project)
        print("[GEE] Inicializado.")
    except Exception:
        print("Sessão GEE expirada ou nula. Iniciando autenticação...")
        ee.Authenticate()
        ee.Initialize(project=project)
        print("[GEE] Autenticado com sucesso.")
    
    print("[GCS] Autenticação GCS/ADC configurada.")


# ─── VARIÁVEIS GLOBAIS (serão configuradas) ─────────────────────────────────

CONFIG = get_config('peru')  # Padrão: Peru (compatível com notebooks existentes)

GLOBAL_OPTS = {
    'SENSOR': 'landsat',       # landsat, sentinel2, hls, modis
    'PERIODICITY': 'yearly',   # yearly, monthly
    'MOSAIC_METHOD': 'minnbr', # minnbr, minnbr_buffer, median, minndvi
    'PERSONAL_TASK_FLAG': 'MONITOR'
}

def _get_fs():
    """Retorna uma instância GCSFileSystem corretamente autenticada para qualquer ambiente."""
    import gcsfs
    is_colab = 'COLAB_RELEASE_TAG' in os.environ or 'COLAB_BACKEND_VERSION' in os.environ
    if is_colab:
        # No Colab, não passamos project para evitar erros de billing desabilitado
        return gcsfs.GCSFileSystem(token='google_default', requests_timeout=5)
    else:
        # No Windows/Local, usamos o token padrão (ADC). 
        # Deixamos o gcsfs detectar o projeto automaticamente para evitar conflitos de quota.
        return gcsfs.GCSFileSystem(token='google_default', requests_timeout=10)

def set_global_opts(sensor='landsat', periodicity='yearly', personal_task_flag='MONITOR', clean_cache=False):
    """
    Configura variáveis globais do fluxo de processamento.
    
    Args:
        sensor: 'landsat', 'sentinel2', 'hls' ou 'modis'
        periodicity: 'yearly' ou 'monthly'
        personal_task_flag: Prefixo para organizar tasks no GEE (ex: 'MONITOR')
    """
    global GLOBAL_OPTS
    GLOBAL_OPTS['SENSOR'] = sensor
    GLOBAL_OPTS['PERIODICITY'] = periodicity
    GLOBAL_OPTS['PERSONAL_TASK_FLAG'] = personal_task_flag
    
    print(f"✅ Opções Globais: {sensor.upper()} | {periodicity.upper()} | Task Flag: {personal_task_flag}")

    if clean_cache:
        try:
            fs = _get_fs()
            cache_file = f"state.json"
            gcs_path = f"gs://{CONFIG['bucket']}/{CONFIG['gcs_cache']}/{cache_file}"
            if fs.exists(gcs_path):
                fs.rm(gcs_path)
                print(f"🧹 Cache removido: {gcs_path}")
            else:
                print("ℹ️ Cache não encontrado (nada para limpar).")
        except Exception as e:
            print(f"⚠️ Aviso ao limpar cache: {e}")
    
    return GLOBAL_OPTS


# ─── GENERADORES DE CAMINHOS GCS ──────────────────────────────────────────────

def _gcs_library_base():
    """Base folder for images in GCS (agrupado por sensor)."""
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    return f"{CONFIG['gcs_library_images']}/{sensor}"

def _gcs_mosaic_path(periodicity, temporal_id, mosaic=None):
    """
    Padrão GCS: .../library_images/{sensor}/{periodicity}/{mosaic}/{temporal_id}/
    """
    base = _gcs_library_base()
    period = periodicity.lower()
    m = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).lower()
    return f"{base}/{period}/{m}/{temporal_id}"

def monthly_mosaic_path(year, month):
    temporal_id = f"{year}_{month:02d}"
    return _gcs_mosaic_path("monthly", temporal_id)

def yearly_mosaic_path(year):
    temporal_id = f"{year}"
    return _gcs_mosaic_path("yearly", temporal_id)

def monthly_chunk_path(year, month, mosaic='minnbr', sensor=None):
    """Caminho GCS para chunks mensais: {sensor}/{period}/{mosaic}/{date}/chunks/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).lower()
    return f"{CONFIG['gcs_library_images']}/{s}/monthly/{mosaic.lower()}/{year}_{month:02d}/chunks"

def yearly_chunk_path(year, mosaic='minnbr', sensor=None):
    """Caminho GCS para chunks anuais: {sensor}/{period}/{mosaic}/{date}/chunks/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).lower()
    return f"{CONFIG['gcs_library_images']}/{s}/annually/{mosaic.lower()}/{year}/chunks"

def monthly_cog_path(year, month, mosaic='minnbr', sensor=None):
    """Caminho GCS para COGs mensais: {sensor}/{period}/{mosaic}/{date}/cog/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).lower()
    return f"{CONFIG['gcs_library_images']}/{s}/monthly/{mosaic.lower()}/{year}_{month:02d}/cog"

def yearly_cog_path(year, mosaic='minnbr', sensor=None):
    """Caminho GCS para COGs anuais: {sensor}/{period}/{mosaic}/{date}/cog/"""
    s = (sensor or GLOBAL_OPTS['SENSOR']).lower()
    return f"{CONFIG['gcs_library_images']}/{s}/annually/{mosaic.lower()}/{year}/cog"

def model_path(training_id, shortname, region=None):
    """
    GCS: GCS/{country}/.../monitor/version_01/library_images/{sensor}/models/{asset_name}
    Asset: training_{training_id}_{shortname}_{sensor}
    """
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    asset_name = f"training_{training_id}_{shortname}_{sensor}"
    base = f"{_gcs_library_base()}/models/{asset_name}"
    if region:
        return f"{base}/{region}"
    return base

def gcs_path(relative):
    """Retorna URL gs:// completa."""
    return f"gs://{CONFIG['bucket']}/{relative}"


# ─── GENERADORES DE CAMINHOS GEE ──────────────────────────────────────────────

def get_asset_mosaic_collection(sensor=None, periodicity=None, band=None, period=None, mosaic=None):
    """
    Gera o path da ImageCollection no GEE para imagens raw/mosaicadas.
    Padrão: .../LIBRARY_IMAGES/{SENSOR}/{PERIODICITY}/{MOSAIC}/{band}
    """
    period = period or periodicity or GLOBAL_OPTS['PERIODICITY']
    folder_period = period.upper()
    m = (mosaic or GLOBAL_OPTS.get('MOSAIC_METHOD', 'minnbr')).upper()
    
    sensor_name = (sensor or GLOBAL_OPTS['SENSOR']).upper()
    
    # Path principal da library de imagens
    path = f"{CONFIG['asset_monitor_base']}/LIBRARY_IMAGES/{sensor_name}/{folder_period}/{m}"
    
    if band:
        path = f"{path}/{band}"
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
                print(f"✅ GDAL encontrado e adicionado ao PATH: {d}")
                return
    
    # Se ainda não encontrou, emite aviso com instruções
    print(f"⚠️ Aviso: Utilitários GDAL não encontrados: {missing}")
    if 'COLAB_RELEASE_TAG' in os.environ or 'COLAB_BACKEND_VERSION' in os.environ:
        print("💡 No Google Colab, execute: !apt-get install -y gdal-bin")
    elif platform.system() == 'Windows':
        print("💡 No Windows, certifique-se de que o GDAL está no seu PATH ou use o ambiente Conda (gdal).")
        print(f"   Dica: Ative o ambiente correto com 'conda activate <env>' antes de iniciar o Jupyter.")

def sample_asset_name(temporal_id, version_id):
    """
    Garante o padrão sample_{id}_{temporal_id}
    version_id pode ser '0001' ou 'sample_0001'
    """
    clean_version = version_id.replace('sample_', '')
    return f"sample_{clean_version}_{temporal_id}"

def get_asset_samples(temporal_id, version_id):
    asset = sample_asset_name(temporal_id, version_id)
    return f"{CONFIG['asset_monitor_base']}/LIBRARY_SAMPLES/{asset}"

def get_gcs_samples(temporal_id, version_id):
    asset = sample_asset_name(temporal_id, version_id)
    return f"{CONFIG['gcs_library_samples']}/{asset}"

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
    """Atualiza a configuração global para um novo país."""
    global CONFIG
    CONFIG = get_config(country)
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
    print(f"🌍 País: {CONFIG['country'].upper()}")
    print(f"📦 Bucket: {CONFIG['bucket']}")
    print(f"🏷️  Versão: {CONFIG['version']}")
    print(f"📡 Sensor: {GLOBAL_OPTS['SENSOR']} (Task Prefix: {GLOBAL_OPTS['PERSONAL_TASK_FLAG']})")
