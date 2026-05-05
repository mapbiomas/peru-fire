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
            
            # Estrutura de caminhos no GCS (Base: sudamerica/{country}/monitor/{version})
            'gcs_samples': 'sudamerica/peru/monitor/version_01/library_samples',
            'gcs_mosaics': 'sudamerica/peru/monitor/version_01/library_images',
            'gcs_models': 'sudamerica/peru/monitor/version_01/models',
            'gcs_cache': 'sudamerica/peru/monitor/version_01/.cache',
            'gcs_classifications': 'sudamerica/peru/monitor/version_01/classifications',
            'gcs_filtered': 'sudamerica/peru/monitor/version_01/filtered',
            'gcs_chunks': 'sudamerica/peru/monitor/version_01/chunks',
            
            # Estrutura de Assets no GEE
            'asset_mosaics_base': 'projects/mapbiomas-mosaics/assets/FIRE',
            'asset_samples': 'projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/LIBRARY_SAMPLES',
            'asset_regions': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',
            'asset_fire_ref': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/REFERENCES/cicatrizes_fuego_reference_2016_2024/cicatriz_fuego_',
            'asset_hotspots': 'projects/mapbiomas-fire-485203/assets/DATABASE/monthly-focus-sul-america',
            'asset_classification': 'projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/CLASSIFICATIONS',
            'asset_filtered': 'projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/FILTERED',
            
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
    'FIRE_POTENTIAL_FILTER': False
}

def set_global_opts(sensor='landsat', periodicity='yearly', fire_potential_filter=False):
    """
    Configura variáveis globais do fluxo de processamento (mosaicos).
    
    Args:
        sensor: 'landsat', 'sentinel2', 'hls' ou 'modis'
        periodicity: 'yearly' ou 'monthly'
        fire_potential_filter: True para usar imagens filtradas pelo buffer de focos
    """
    global GLOBAL_OPTS
    GLOBAL_OPTS['SENSOR'] = sensor
    GLOBAL_OPTS['PERIODICITY'] = periodicity
    GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] = fire_potential_filter
    return GLOBAL_OPTS


# ─── GENERADORES DE CAMINHOS GCS ──────────────────────────────────────────────

def _gcs_library_base():
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    suffix = "_buffer" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    return f"{CONFIG['gcs_mosaics']}/{sensor}{suffix}"

def monthly_mosaic_path(year, month):
    return f"{_gcs_library_base()}/monthly/{year}/{month:02d}"

def yearly_mosaic_path(year):
    return f"{_gcs_library_base()}/yearly/{year}"

def monthly_chunk_path(year, month):
    return f"{monthly_mosaic_path(year, month)}/chunks"

def yearly_chunk_path(year):
    return f"{yearly_mosaic_path(year)}/chunks"

def model_path(version, region):
    return f"{CONFIG['gcs_models']}/{version}/{region}"

def gcs_path(relative):
    """Retorna URL gs:// completa."""
    return f"gs://{CONFIG['bucket']}/{relative}"


# ─── GENERADORES DE CAMINHOS GEE ──────────────────────────────────────────────

def get_asset_mosaic_collection(sensor=None, periodicity=None, band=None, period=None):
    """
    Gera o path da ImageCollection no GEE.
    projects/mapbiomas-mosaics/assets/FIRE/SENTINEL2/MONTHLY/blue
    """
    period = period or periodicity or GLOBAL_OPTS['PERIODICITY']
    folder_period = period.upper()
    
    suffix = "_BUFFER" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    sensor_name = (sensor or GLOBAL_OPTS['SENSOR']).upper() + suffix
    
    path = f"{CONFIG['asset_mosaics_base']}/{sensor_name}/{folder_period}"
    if band:
        path = f"{path}/{band}"
    return path


# ─── NOMENCLATURA ─────────────────────────────────────────────────────────────

def mosaic_name(year, month=None, period=None):
    """
    Gera nome padrão para o mosaico: sentinel2_fire_peru_2024_01
    """
    country = CONFIG['country']
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    period = period or GLOBAL_OPTS['PERIODICITY']
    
    date_str = f"{year}_{month:02d}" if month else f"{year}"
    
    suffix = "_buffer" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    
    return f"{sensor}{suffix}_fire_{country}_{date_str}"

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

def classification_name(periodicity, year, month=None, version=None):
    """Gera nome para o arquivo de classificação: class_sentinel2_peru_r01_2024_01_v1"""
    country = CONFIG['country']
    sensor = GLOBAL_OPTS['SENSOR'].lower()
    suffix = "_buffer" if GLOBAL_OPTS['FIRE_POTENTIAL_FILTER'] else ""
    ver = version or CONFIG['version']
    region = "r01" # Exemplo, ajustar conforme logica de regioes
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
    print(f"📡 Sensor: {GLOBAL_OPTS['SENSOR']} (Filter: {GLOBAL_OPTS['FIRE_POTENTIAL_FILTER']})")
