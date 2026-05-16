import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import rasterio
from rasterio.mask import mask
from rasterio.io import MemoryFile
import gcsfs
TF_AVAILABLE = None
TF_ERROR = None
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import matplotlib.pyplot as plt
from datetime import datetime
import time
from M0_auth_config import CONFIG, GLOBAL_OPTS, gcs_path, model_path
from M_cache import _get_fs
from M_ui_components import PipelineStepUI
SENSOR_MOSAIC_BANDS = {
    ('sentinel2', 'minnbr'):        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
    ('sentinel2', 'minnbr_buffer'): ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
    ('landsat',   'minnbr'):        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
    ('hls',       'minnbr'):        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
}
ALL_BANDS_LIST = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']

def _load_m4_cache():
    """Lê o cache local com busca em múltiplos níveis de diretório."""
    filename = "m4_ranking_cache.json"
    candidates = [filename, os.path.join("..", filename), os.path.join("..", "..", filename)]
    
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f: return json.load(f)
            except: continue
    return {}

def _save_m4_cache(data):
    """Salva o estado no arquivo local mais próximo."""
    try:
        with open("m4_ranking_cache.json", 'w') as f:
            json.dump(data, f, indent=2)
    except: pass

def list_trained_models(force_refresh=False):
    """Lista modelos já treinados priorizando o cache local para velocidade."""
    from M0_auth_config import _gcs_models_base, CONFIG
    cache = _load_m4_cache()
    
    # Se temos cache e não forçamos refresh, retorna instantaneamente
    if cache.get('known_ids') and not force_refresh:
        return cache['known_ids']
        
    try:
        fs = _get_fs()
        path = f"{CONFIG['bucket']}/{_gcs_models_base()}"
        models = []
        if fs.exists(path):
            trainings = fs.ls(path)
            for t_dir in trainings:
                t_name = t_dir.split('/')[-1]
                if t_name.startswith('training_'):
                    models.append(t_name)
                    # Guarda o path no cache em vez de poluir a lista de IDs
                    if 'meta' not in cache: cache['meta'] = {}
                    if t_name not in cache['meta']: cache['meta'][t_name] = {}
                    cache['meta'][t_name]['path'] = t_dir
        
        # Atualiza a lista de IDs conhecidos no cache
        cache['known_ids'] = models
        _save_m4_cache(cache)
        return models
    except Exception as e:
        return cache.get('known_ids', [])

