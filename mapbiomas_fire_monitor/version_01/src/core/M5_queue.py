import os
import json
from M0_auth_config import CONFIG, GLOBAL_OPTS

def _campaign(campaign=None):
    """Return campaign subfolder path segment."""
    c = campaign or GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
    return f"{c}/" if c else ''

def get_queue_file():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, 'm5_queue.json')

def load_queue():
    q_file = get_queue_file()
    if os.path.exists(q_file):
        with open(q_file, 'r') as f:
            return json.load(f)
    return []

def save_queue(q):
    with open(get_queue_file(), 'w') as f:
        json.dump(q, f, indent=2)

def make_job_id(model, region, period, campaign=None):
    parts = [model, region, period]
    if campaign:
        parts.insert(0, campaign)
    return " | ".join(parts)

def new_job(model, region, period, task_name=''):
    campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
    return {
        'id': make_job_id(model, region, period, campaign),
        'model': model,
        'region': region,
        'period': period,
        'task_name': task_name,
        'campaign': campaign,
        'status': 'PENDING',
        'enabled': True,
        'upload_gee': False,
        'progress': '0%'
    }

def classifications_base(model_id, campaign=None):
    return f"{CONFIG['gcs_library_classifications']}/{_campaign(campaign)}{model_id}"

def classified_tiles_dir(model_id, campaign=None):
    return f"{classifications_base(model_id, campaign)}/CLASSIFIED_TILES"

def tile_path(model_id, region, cell_id, period, campaign=None):
    return f"{classified_tiles_dir(model_id, campaign)}/tile_{region}_{cell_id}_{period}.tif"

def classified_region_dir(model_id, campaign=None):
    return f"{classifications_base(model_id, campaign)}/CLASSIFIED_REGION"

def region_path(model_id, region, period, campaign=None):
    return f"{classified_region_dir(model_id, campaign)}/region_{region}_{model_id}_{period}.tif"

def stats_dir(model_id, campaign=None):
    return f"{classifications_base(model_id, campaign)}/STATS"

def geral_stats_dir():
    return f"{CONFIG['gcs_library_classifications']}/GERAL_STATS"

def tile_stats_path(model_id, campaign=None):
    return f"{stats_dir(model_id, campaign)}/stats_tile.csv"

def region_stats_path(model_id, campaign=None):
    return f"{stats_dir(model_id, campaign)}/stats_region.csv"

def consolidated_stats_path():
    return f"{geral_stats_dir()}/consolidated_stats.csv"

def gcs_full(relative_path):
    """Path completo con bucket para operaciones GCSFS."""
    return f"{CONFIG['bucket']}/{relative_path}"


# --- TAREAS COMPARTIDAS (GCS) ---

def tareas_dir():
    """Directorio GCS donde se almacenan las tareas compartidas."""
    return f"{CONFIG['gcs_cache']}/tareas"

def tarea_path(model_id):
    """Path GCS relativo para la tarea de un modelo."""
    return f"{tareas_dir()}/{model_id}.json"

def save_tarea(model_id, regions, periods, fs=None):
    """Guarda una tarea compartida en GCS."""
    import json
    import datetime
    from M0_auth_config import _get_fs
    if fs is None:
        fs = _get_fs()
    path = gcs_full(tarea_path(model_id))
    tarea = {
        'model': model_id,
        'regions': sorted(set(regions)),
        'periods': sorted(set(periods)),
        'created_at': datetime.datetime.now().isoformat(timespec='seconds')
    }
    dir_path = path.rsplit('/', 1)[0]
    if not fs.exists(dir_path):
        fs.mkdir(dir_path)
    with fs.open(path, 'w') as f:
        json.dump(tarea, f, indent=2)
    return path

def delete_tarea(model_id, fs=None):
    """Elimina una tarea compartida de GCS."""
    from M0_auth_config import _get_fs
    if fs is None:
        fs = _get_fs()
    path = gcs_full(tarea_path(model_id))
    try:
        if fs.exists(path):
            fs.rm(path)
    except Exception:
        pass

def list_tareas(fs=None):
    """Lista todas las tareas compartidas en GCS. Retorna lista de dicts."""
    import json
    from M0_auth_config import _get_fs
    if fs is None:
        fs = _get_fs()
    dir_path = gcs_full(tareas_dir())
    results = []
    try:
        files = fs.glob(f"{dir_path}/*.json")
    except Exception:
        return results
    for fp in sorted(files):
        try:
            with fs.open(fp, 'r') as f:
                data = json.load(f)
            results.append(data)
        except Exception:
            pass
    return results
