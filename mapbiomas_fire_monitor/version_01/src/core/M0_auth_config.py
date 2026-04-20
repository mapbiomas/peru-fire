"""
M0 — Autenticação e Configuração
MapBiomas Fire Sentinel Monitor

Este módulo contém a configuração global do projeto.
Selecione o país definindo a variável COUNTRY antes de importar.
"""

import warnings
warnings.filterwarnings('ignore', message='.*Google Cloud SDK.*')

import ee
import os
import json

# ─── PAÍSES DISPONÍVEIS ─────────────────────────────────────────────────────────

PAISES = {
    'peru': {
        'nome': 'Peru',
        'ee_project': 'mapbiomas-peru',
        'bucket': 'mapbiomas-fire',
        'lulc': 'projects/mapbiomas-public/assets/peru/collection2/mapbiomas_peru_collection2_integration_v1',
        'regioes_asset': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',
    },
    'bolivia': {
        'nome': 'Bolivia',
        'ee_project': 'mapbiomas-peru',  # Compartilhado
        'bucket': 'mapbiomas-fire',        # Compartilhado
        'lulc': 'projects/mapbiomas-public/assets/bolivia/collection2/mapbiomas_bolivia_collection2_integration_v1',
        'regioes_asset': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_bolivia_v1',
    },
    'paraguay': {
        'nome': 'Paraguay',
        'ee_project': 'mapbiomas-peru',  # Compartilhado
        'bucket': 'mapbiomas-fire',        # Compartilhado
        'lulc': 'projects/mapbiomas-public/assets/paraguay/collection2/mapbiomas_paraguay_collection2_integration_v1',
        'regioes_asset': 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_paraguay_v1',
    },
}

# ─── CONFIGURAÇÃO GLOBAL ───────────────────────────────────────────────────────

def get_config(country):
    """
    Retorna CONFIG para o país especificado.
    
    Args:
        country: 'peru', 'bolivia', ou 'paraguay'
    
    Returns:
        dict: Configuração completa do país
    """
    if country not in PAISES:
        raise ValueError(f"País '{country}' não encontrado. Opções: {list(PAISES.keys())}")
    
    p = PAISES[country]
    
    return {
        # ── País / projeto ──
        'country': country,
        'country_name': p['nome'],
        'ee_project': p['ee_project'],
        'bucket': p['bucket'],
        
        # ── GCS base path ──
        'base_path': f'sudamerica/{country}/monitor',
        'gcs_base': f'sudamerica/{country}/monitor',
        
        # ── Rotas de GEE Asset ──
        'asset_classification': f"projects/mapbiomas-{country}/assets/FIRE/MONITOR/CLASSIFICATIONS/RAW_VERSIONS",
        'asset_regions': p['regioes_asset'],
        'asset_samples': 'projects/mapbiomas-peru/assets/FIRE/SAMPLES',
        
        # ── LULC ──
        'lulc_asset': p['lulc'],
        'lulc_mask_classes': [26, 22, 33, 24],  # agua, nuvens, urbano, mining
        
        # ── Estrutura de pastas GCS ──
        # Nota: paths de chunks/cog incluem sensor dinamicamente.
        # Use as funções helper: monthly_chunk_path(), gcs_chunks_prefix(), etc.
        'gcs_models': f'sudamerica/{country}/monitor/models',
        'gcs_samples': f'sudamerica/{country}/monitor/samples',
        
        # ── Configuração Sentinel-2 ──
        'sensor': 'COPERNICUS/S2_SR_HARMONIZED',
        'cs_plus': 'GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED',
        'cs_threshold': 0.40,
        
        # ── Buffer de focos ──
        'focus_buffer': 'projects/workspace-ipam/assets/BUFFER-DOUBLE-MONTHLY-FOCUS-OF-INPE-SULAMERICA',
        
        # ── Bandas do mosaico ──
        'bands_spectral': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'],
        'bands_all': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'],
        
        # ── Bandas do modelo ──
        'bands_model_default': ['red', 'nir', 'swir1', 'swir2'],
        'bands_model_optional': ['blue', 'green', 'dayOfYear'],
        
        # ── Mapeamento de bandas S2 ──
        's2_bands_in': ['B2', 'B3', 'B4', 'B8', 'B11', 'B12'],
        's2_bands_out': ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'],
        
        # ── Escala espectral ──
        'spectral_scale_factor': 100,  # 0-10000 → 0-100 (byte)
        
        # ── Tamanho da grade (~1/4 cena Landsat ≈ 92km) ──
        'tile_size_deg': 0.83,
        
        # ── Saída de classificação ──
        'classification_output': 'day_of_year',
        
        # ── Modelo DNN ──
        'model_layers': [7, 14, 7, 14, 7],
        'model_lr': 0.001,
        'model_batch': 1000,
        'model_iters': 7000,
        'model_split': 0.70,  # 70% treino / 30% teste
    }


# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────

def authenticate(project='mapbiomas-peru'):
    """Autenticar com Google Earth Engine e GCS."""
    try:
        ee.Initialize(project=project)
        print("✅ GEE já autenticado.")
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project)
        print("✅ GEE autenticado.")
    
    print("✅ Autenticação GCS via ADC (Application Default Credentials).")


# ─── VARIÁVEIS GLOBAIS (serão configuradas) ─────────────────────────────────

CONFIG = get_config('peru')  # Padrão: Peru (compatível com notebooks existentes)

GLOBAL_OPTS = {
    'SENSOR': 'landsat',       # landsat, sentinel2, hls, modis
    'PERIODICITY': 'yearly'    # yearly, monthly
}

def set_global_opts(sensor='landsat', periodicity='yearly'):
    """
    Configura variáveis globais do fluxo de processamento (mosaicos).
    
    Args:
        sensor: 'landsat', 'sentinel2', 'hls' ou 'modis'
        periodicity: 'yearly' ou 'monthly'
    """
    global GLOBAL_OPTS
    GLOBAL_OPTS['SENSOR'] = sensor
    GLOBAL_OPTS['PERIODICITY'] = periodicity
    return GLOBAL_OPTS


# ─── MODO DE EDIÇÃO ──────────────────────────────────────────────────────────

_EDIT_MODE = False

def set_edit_mode(enabled):
    """Ativa/desativa o modo de edição (exibe botão Deletar na UI)."""
    global _EDIT_MODE
    _EDIT_MODE = enabled

def is_edit_mode():
    """Retorna se o modo de edição está ativo."""
    return _EDIT_MODE


# ─── SELEÇÃO DE PAÍS ──────────────────────────────────────────────────────────

def set_country(country):
    """
    Define o país e configura CONFIG global.
    
    Args:
        country: 'peru', 'bolivia', ou 'paraguay'
    """
    global CONFIG
    CONFIG = get_config(country)
    return CONFIG


def get_countries():
    """Retorna lista de países disponíveis."""
    return list(PAISES.keys())


# ─── FUNÇÕES AUXILIARES ────────────────────────────────────────────────────────

def gcs_path(subpath):
    """Retorna o caminho completo gs:// para uma subrota GCS."""
    return f"gs://{CONFIG['bucket']}/{subpath}"


def _gcs_library_base():
    """Retorna o prefixo GCS dinâmico incluindo o sensor ativo."""
    sensor = GLOBAL_OPTS['SENSOR']
    return f"{CONFIG['gcs_base']}/library_images/{sensor}"


def gcs_chunks_prefix(period='monthly'):
    """Retorna o prefixo GCS base para chunks (sem ano/mês)."""
    period_folder = period  # 'monthly' ou 'yearly'
    return f"{_gcs_library_base()}/{period_folder}/chunks"


def gcs_mosaic_prefix(period='monthly'):
    """Retorna o prefixo GCS base para COGs (sem ano/mês)."""
    period_folder = period  # 'monthly' ou 'yearly'
    return f"{_gcs_library_base()}/{period_folder}/cog"


def monthly_chunk_path(year, month):
    return f"{gcs_chunks_prefix('monthly')}/{year}/{month:02d}"


def monthly_mosaic_path(year, month):
    return f"{gcs_mosaic_prefix('monthly')}/{year}/{month:02d}"


def yearly_chunk_path(year):
    return f"{gcs_chunks_prefix('yearly')}/{year}"


def yearly_mosaic_path(year):
    return f"{gcs_mosaic_prefix('yearly')}/{year}"


def get_asset_mosaic_collection(period='monthly', band=None):
    """
    Retorna o path base do GEE Asset de acordo com a nova estrutura padrao.
    Ex: projects/mapbiomas-mosaics/assets/FIRE/SENTINEL2/MONTHLY/swir2
    """
    sensor_key = GLOBAL_OPTS['SENSOR']
    # Normalizar o nome do sensor para o formato esperado na pasta
    sensor_map = {
        'landsat': 'LANDSAT',
        'sentinel2': 'SENTINEL2',
        'modis': 'MODIS',
        'hls': 'HLS'
    }
    sensor_folder = sensor_map.get(sensor_key, sensor_key.upper())
    
    period_folder = 'MONTHLY' if period == 'monthly' else 'ANNUAL'
    base_path = f"projects/mapbiomas-mosaics/assets/FIRE/{sensor_folder}/{period_folder}"
    
    if band:
        return f"{base_path}/{band}"
    return base_path

def mosaic_name(year, month=None, period=None):
    country = CONFIG['country']
    sensor = GLOBAL_OPTS['SENSOR']
    p = period if period else GLOBAL_OPTS['PERIODICITY']
    
    year_str = str(year)
    if p == 'monthly' and month is not None:
        return f"{sensor}_fire_{country}_{year_str}_{month:02d}"
    
    return f"{sensor}_fire_{country}_{year_str}"


def classification_name(regions, version, year, month=None):
    country = CONFIG['country']
    regions_str = '_'.join(regions)
    if month is not None:
        return f"burned_area_s2_{country}_{regions_str}_{version}_{year}_{month:02d}"
    return f"burned_area_s2_{country}_{regions_str}_{version}_{year}"


def model_path(version, region):
    return f"{CONFIG['gcs_models']}/{version}/{region}"


# ─── FUNÇÕES DE GEOMETRIA ───────────────────────────────────────────────────────

def get_country_geometry():
    """Retorna a geometria EE de todo o país (união de todas as regiões)."""
    fc = ee.FeatureCollection(CONFIG['asset_regions'])
    return fc.geometry()


def get_region_geometry(region_name):
    """Retorna a geometria EE de uma região específica por nome."""
    fc = ee.FeatureCollection(CONFIG['asset_regions']) \
           .filter(ee.Filter.eq('region_nam', region_name))
    return fc.geometry()


def list_regions():
    """Retorna a lista ordenada de nomes de regiões."""
    fc = ee.FeatureCollection(CONFIG['asset_regions'])
    names = fc.aggregate_array('region_nam').getInfo()
    return sorted(names)


# ─── IMPRIMIR RESUMO ──────────────────────────────────────────────────────────

def print_config():
    print("=" * 60)
    print("  🔥 MapBiomas Fire Monitor — Pipeline")
    print("=" * 60)
    print(f"  País         : {CONFIG['country_name'].upper()} ({CONFIG['country']})")
    print(f"  Projeto GEE  : {CONFIG['ee_project']}")
    print(f"  Bucket GCS   : gs://{CONFIG['bucket']}")
    print(f"  Base Path    : {CONFIG['base_path']}")
    print("=" * 60)
    print(f"  Sensor (Fluxo): {GLOBAL_OPTS['SENSOR'].upper()}")
    print(f"  Periodicidade : {GLOBAL_OPTS['PERIODICITY'].upper()}")
    print(f"  Modo Edição   : {'✅ ATIVO' if _EDIT_MODE else '❌ Desativado'}")
    print(f"  Sensor EE     : {CONFIG['sensor']}")
    print(f"  Bandas espec. : {CONFIG['bands_spectral']}")
    print(f"  Bandas modelo : {CONFIG['bands_model_default']}")
    print(f"  Tile size     : {CONFIG['tile_size_deg']}° (~92km)")
    print(f"  LULC mask     : classes {CONFIG['lulc_mask_classes']}")
    print(f"  LULC Asset    : {CONFIG['lulc_asset']}")
    print("=" * 60)


# ─── FUNÇÕES UTILITÁRIAS ─────────────────────────────────────────────────────

def get_temp_dir():
    """Retorna diretório temporário para o projeto."""
    import tempfile
    temp_dir = os.path.join(tempfile.gettempdir(), 'mapbiomas_fire')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def check_command_exists(cmd):
    """Verifica se um comando está disponível no sistema."""
    import shutil
    return shutil.which(cmd) is not None


def ensure_gdal_path():
    """
    Tenta localizar binários do GDAL no Windows vasculhando caminhos comuns do Conda/OSGeo4W.
    Injeta no PATH se encontrar.
    """
    import os
    import shutil
    import platform

    if platform.system() != 'Windows':
        return  # Apenas Windows precisa de busca manual profunda

    if shutil.which('gdalbuildvrt') and shutil.which('gdal_translate'):
        return # Já está no PATH

    print("[BUSCA] Buscando binários do GDAL no ambiente local...")
    
    # Caminhos prováveis onde o Conda instala o GDAL no Windows
    possible_roots = [
        os.path.join(os.environ.get('USERPROFILE', ''), 'miniconda3'),
        os.path.join(os.environ.get('USERPROFILE', ''), 'anaconda3'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'miniconda3'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'anaconda3'),
        r"C:\ProgramData\miniconda3",
        r"C:\ProgramData\anaconda3",
        r"C:\OSGeo4W",
        r"C:\OSGeo4W64",
    ]

    # Pastas de binários dentro desses roots
    bin_subfolders = [
        r"Library\bin", # Padrão Conda (GeoTIFF, GDAL)
        r"Scripts",     # Alternativa Conda
        r"bin",         # Padrão OSGeo4W
    ]

    for root in possible_roots:
        if not os.path.exists(root): continue
        
        # Procurar em subpastas de ambientes se existir 'envs'
        envs_path = os.path.join(root, 'envs')
        search_dirs = [root]
        if os.path.exists(envs_path):
            try:
                search_dirs.extend([os.path.join(envs_path, d) for d in os.listdir(envs_path)])
            except: pass

        for sdir in search_dirs:
            for sub in bin_subfolders:
                path = os.path.join(sdir, sub)
                if os.path.exists(path) and os.path.exists(os.path.join(path, 'gdalbuildvrt.exe')):
                    if path not in os.environ['PATH']:
                        os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                        print(f"[OK] GDAL localizado em: {path}")
                        return True
    
    return False
