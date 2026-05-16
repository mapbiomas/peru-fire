import os
import json
from M0_auth_config import CONFIG
from M_cache import _get_fs

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

