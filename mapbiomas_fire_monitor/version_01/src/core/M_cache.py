"""
M_cache — Cache Manager
MapBiomas Fire Sentinel Monitor

Gerencia cache de estado de exports no GCS para carregamento rapido da interface.
"""

import os
import json
import datetime
import threading
import logging
from M0_auth_config import CONFIG

def _get_fs():
    """Retorna uma instância GCSFileSystem corretamente autenticada para qualquer ambiente."""
    import gcsfs
    is_colab = 'COLAB_RELEASE_TAG' in os.environ or 'COLAB_BACKEND_VERSION' in os.environ
    if is_colab:
        # No Colab, não passamos project para evitar erros de billing desabilitado
        return gcsfs.GCSFileSystem(token='google_default', requests_timeout=15)
    else:
        project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
        return gcsfs.GCSFileSystem(project=project, requests_timeout=15)

class CacheManager:
    CACHE_FILE = "state.json"
    _state = None
    _lock = threading.Lock() # Lock local para evitar race conditions no mesmo kernel

    @staticmethod
    def _get_gcs_path():
        """Retorna path do cache no GCS."""
        return f"gs://{CONFIG['bucket']}/{CONFIG['gcs_cache']}/{CacheManager.CACHE_FILE}"

    @staticmethod
    def load(force=False):
        """
        Carrega cache do GCS.
        """
        if CacheManager._state is not None and not force:
            return CacheManager._state
        
        with CacheManager._lock:
            CacheManager._state = {
                "updated_at": None,
                "country": CONFIG['country'],
                "assets_monthly": [],
                "assets_annually": [],
                "gcs_chunks": {},
                "cogs_monthly": [],
                "cogs_annually": []
            }
            
            try:
                gcs_path = CacheManager._get_gcs_path()
                fs = _get_fs()
                
                if fs.exists(gcs_path):
                    with fs.open(gcs_path, 'r') as f:
                        data = json.load(f)
                        # Merge com o estado inicial para garantir chaves novas
                        CacheManager._state.update(data)
                else:
                    print(f"Cache não encontrado em {gcs_path}. Será criado ao sincronizar.")
            except Exception as e:
                print(f"⚠️ Aviso: Falha ao ler cache do GCS: {e}")
        
        return CacheManager._state

    @staticmethod
    def build_cache_from_gee(logger=None):
        """Popula cache listando assets do GEE em paralelo para performance."""
        import ee, time
        from concurrent.futures import ThreadPoolExecutor
        from M0_auth_config import CONFIG, GLOBAL_OPTS, get_asset_mosaic_collection
        
        start_time = time.time()
        state = CacheManager.get_state()
        state['assets_monthly'] = []
        state['assets_annually'] = []
        
        bands = CONFIG.get('bands_all', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'])
        tasks = []
        
        # Lemos o sensor UMA VEZ antes de iniciar as threads para evitar race conditions.
        # set_global_opts() já foi chamado pelo usuário antes de rodar a interface.
        sensor_name = (GLOBAL_OPTS.get('SENSOR', 'sentinel2')).upper()
        
        # Sempre verificamos tanto a coleção normal quanto a _BUFFER para o cache ser completo
        for period_type in ['monthly', 'yearly']:
            for suffix in ['', '_BUFFER']:
                full_sensor = f'{sensor_name}{suffix}'
                for band in bands:
                    col_id = f"{CONFIG['asset_mosaics_base']}/{full_sensor}/{period_type.upper()}/{band}"
                    tasks.append((col_id, period_type, band))
        
        total_steps = len(tasks)
        completed = 0
        
        if logger: logger("Iniciando sincronización GEE (Paralelo)...", "info")
        
        def fetch_assets(task_info):
            col_id, period_type, band = task_info
            assets_found = []
            page_token = None
            try:
                while True:
                    params = {'parent': col_id}
                    if page_token: params['pageToken'] = page_token
                    
                    result = ee.data.listAssets(params)
                    for a in result.get('assets', []):
                        asset_name = a['name'].split('/')[-1]
                        # Garantimos que o nome no cache tenha o sufixo da banda
                        # Isso permite que o M1 diferencie as bandas corretamente
                        if not asset_name.endswith(f"_{band}"):
                            asset_name = f"{asset_name}_{band}"
                        assets_found.append((period_type, asset_name))
                    
                    page_token = result.get('nextPageToken')
                    if not page_token: break
                return assets_found
            except Exception as e:
                # Log silencioso ou aviso se a coleção não existir
                return []

        # Executar em paralelo (máximo 8 threads para não sobrecarregar quota GEE)
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(fetch_assets, t) for t in tasks]
            for future in futures:
                res = future.result()
                for period_type, asset_name in res:
                    target_key = 'assets_monthly' if period_type == 'monthly' else 'assets_annually'
                    if asset_name not in state[target_key]:
                        state[target_key].append(asset_name)
                
                completed += 1
                if logger:
                    elapsed = time.time() - start_time
                    # Estimativa mais realista para paralelo
                    eta = (elapsed / completed) * (total_steps - completed) if completed > 0 else 0
                    logger(f"Tiempo Estimado: {int(eta):02d}s || [{completed}/{total_steps}]")
        
        CacheManager._state = state
        CacheManager.save()
        return CacheManager._state

    @staticmethod
    def build_cache_from_gcs(logger=None, years=None):
        """Escaneia o GCS para detectar chunks e COGs existentes."""
        from M0_auth_config import CONFIG

        bands_all = CONFIG.get('bands_all', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'])
        sorted_bands = sorted(bands_all, key=len, reverse=True)

        state = CacheManager.get_state()
        gcs_chunks = {}
        cogs_monthly = []
        cogs_annually = []

        try:
            fs = _get_fs()
            
            bucket = CONFIG['bucket']
            
            # Base para busca: sudamerica/peru/monitor/library_images/
            base_search = f"{bucket}/{CONFIG['gcs_mosaics']}"
            
            if logger: logger(f"Escaneando GCS recursivamente: gs://{base_search} ...", "info")
            
            # Listagem recursiva é mais lenta mas garante sincronia total
            all_files = fs.find(base_search)
            
            for fpath in all_files:
                if not fpath.endswith('.tif'): continue
                
                # Identifica se é COG ou Chunk
                basename = fpath.split('/')[-1]
                
                # 1. Processa COGs
                if basename.endswith('_cog.tif'):
                    name_no_ext = basename[:-8] # remove _cog.tif
                    if '/monthly/' in fpath:
                        if name_no_ext not in cogs_monthly: cogs_monthly.append(name_no_ext)
                    else:
                        if name_no_ext not in cogs_annually: cogs_annually.append(name_no_ext)
                
                # 2. Processa Chunks
                elif '/chunks/' in fpath:
                    name_no_ext = basename[:-4]
                    for band in sorted_bands:
                        needle = f"_{band}"
                        idx = name_no_ext.find(needle)
                        if idx != -1:
                            # Verifica se o que vem depois de _band não é outra letra (ex: swir1 vs swir)
                            after_band = idx + len(needle)
                            if after_band >= len(name_no_ext) or not name_no_ext[after_band].isalpha():
                                mosaic_part = name_no_ext[:idx]
                                if mosaic_part not in gcs_chunks:
                                    gcs_chunks[mosaic_part] = []
                                if band not in gcs_chunks[mosaic_part]:
                                    gcs_chunks[mosaic_part].append(band)
                                break

            state['gcs_chunks'] = gcs_chunks
            state['cogs_monthly'] = cogs_monthly
            state['cogs_annually'] = cogs_annually
            
            CacheManager._state = state
            CacheManager.save()

            if logger:
                total_chunks = sum(len(b) for b in gcs_chunks.values())
                logger(f"GCS Sincronizado: {len(cogs_monthly) + len(cogs_annually)} COGs, {total_chunks} fragmentos.", "success")

        except Exception as e:
            if logger: logger(f"Erro ao escanear GCS: {e}", "warning")

        return CacheManager._state

    @staticmethod
    def build_full_cache(logger=None, years=None):
        """Reconstrói o cache completo."""
        CacheManager.build_cache_from_gee(logger=logger)
        CacheManager.build_cache_from_gcs(logger=logger, years=years)
        return CacheManager._state

    @staticmethod
    def save(state=None):
        """Salva cache no GCS."""
        with CacheManager._lock:
            # Suprimir tracebacks internos do gcsfs durante o save
            _gcsfs_logger = logging.getLogger('gcsfs')
            _prev_level = _gcsfs_logger.level
            _gcsfs_logger.setLevel(logging.CRITICAL)
            try:
                gcs_path = CacheManager._get_gcs_path()
                fs = _get_fs()
                
                if state is None:
                    state = CacheManager._state
                
                state['updated_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
                state['country'] = CONFIG['country']
                
                with fs.open(gcs_path, 'w') as f:
                    json.dump(state, f, indent=2)
                
                CacheManager._state = state
            except Exception as e:
                # Aviso limpo sem traceback assustador
                print(f"⚠️ Cache local OK (GCS sync pendente)")
            finally:
                _gcsfs_logger.setLevel(_prev_level)

    @staticmethod
    def get_state():
        """Retorna estado atual."""
        if CacheManager._state is None:
            return CacheManager.load()
        return CacheManager._state

    @staticmethod
    def add_asset(name, period):
        state = CacheManager.get_state()
        key = 'assets_monthly' if period == 'monthly' else 'assets_annually'
        if name not in state[key]:
            state[key].append(name)
            CacheManager.save(state)

    @staticmethod
    def remove_asset(name, period):
        state = CacheManager.get_state()
        key = 'assets_monthly' if period == 'monthly' else 'assets_annually'
        if name in state[key]:
            state[key].remove(name)
            CacheManager.save(state)

    @staticmethod
    def add_gcs_chunk(name, bands):
        state = CacheManager.get_state()
        if name not in state['gcs_chunks']:
            state['gcs_chunks'][name] = []
        for band in bands:
            if band not in state['gcs_chunks'][name]:
                state['gcs_chunks'][name].append(band)
        CacheManager.save(state)

    @staticmethod
    def remove_gcs_chunk(name):
        state = CacheManager.get_state()
        if name in state['gcs_chunks']:
            del state['gcs_chunks'][name]
            CacheManager.save(state)

    @staticmethod
    def reset():
        CacheManager._state = None
