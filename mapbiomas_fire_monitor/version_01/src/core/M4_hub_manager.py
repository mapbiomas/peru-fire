import os
import json
from M0_auth_config import CONFIG
from M_cache import CacheManager, _get_fs


def _load_m4_metadata():
    """Lê apenas metadados de treinamento do cache local (não lista de arquivos GCS)."""
    filename = "m4_ranking_cache.json"
    candidates = [filename, os.path.join("..", filename), os.path.join("..", "..", filename)]

    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                continue
    return {}


def _save_m4_metadata(data):
    """Salva todos os metadados de treinamento em cache local."""
    try:
        with open("m4_ranking_cache.json", 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def list_trained_models(force_refresh=False):
    """Lista modelos treinados usando CacheManager como fonte principal."""
    state = CacheManager.get_state()
    trained = state.get('trained_models', [])

    if trained and not force_refresh:
        return trained

    # Fallback: escaneia GCS direto
    try:
        from M0_auth_config import _gcs_models_base
        fs = _get_fs()
        path = f"{CONFIG['bucket']}/{_gcs_models_base()}"
        models = []
        if fs.exists(path):
            trainings = fs.ls(path)
            for t_dir in trainings:
                t_name = t_dir.split('/')[-1]
                if t_name.startswith('training_'):
                    if not fs.exists(f"{t_dir}/metadata.json"):
                        fs.rm(t_dir, recursive=True)
                        continue
                    models.append(t_name)
                    # Guarda o path em metadata
                    meta_cache = _load_m4_metadata()
                    if 'meta' not in meta_cache:
                        meta_cache['meta'] = {}
                    if t_name not in meta_cache['meta']:
                        meta_cache['meta'][t_name] = {}
                    meta_cache['meta'][t_name]['path'] = t_dir
                    _save_m4_metadata(meta_cache)

        # Atualiza CacheManager
        state['trained_models'] = models
        CacheManager._state = state
        CacheManager.save()
        return models
    except Exception as e:
        return trained

