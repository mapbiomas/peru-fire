"""
M_cache — Cache Manager
MapBiomas Fire Sentinel Monitor

Gerencia cache de estado de exports no GCS para carregamento rapido da interface.
"""

import os
import json
import datetime
import threading
from M0_auth_config import CONFIG

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
                import gcsfs
                gcs_path = CacheManager._get_gcs_path()
                project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
                fs = gcsfs.GCSFileSystem(project=project, token='browser' if 'COLAB_RELEASE_TAG' in os.environ else None)
                
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
        """Popula cache listando assets do GEE."""
        import ee, time
        from M0_auth_config import CONFIG, get_asset_mosaic_collection
        
        start_time = time.time()
        state = CacheManager.get_state()
        state['assets_monthly'] = []
        state['assets_annually'] = []
        
        bands = CONFIG.get('bands_all', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'])
        total_steps = len(bands) * 2 * 2
        current = 0
        
        if logger: logger("Iniciando sincronización GEE...", "info")
        
        for period_type in ['monthly', 'yearly']:
            for suffix in ["", "_BUFFER"]:
                for band in bands:
                    current += 1
                    if logger: 
                        elapsed = time.time() - start_time
                        eta = (elapsed / current) * (total_steps - current) if current > 0 else 0
                        # Formato compacto solicitado pelo usuário
                        logger(f"ETA: {int(eta):02d}s || [{current}/{total_steps}]")
                    
                    try:
                        # Gambiarra temporária para pegar a coleção correta
                        # No futuro, o ImageCollection deve ser um único mosaico multibanda (recomendado)
                        sensor_base = "SENTINEL2" + suffix
                        folder_period = "MONTHLY" if period_type == 'monthly' else "ANNUAL"
                        col_id = f"{CONFIG['asset_mosaics_base']}/{sensor_base}/{folder_period}/{band}"
                        
                        result = ee.data.listAssets({'parent': col_id})
                        for a in result.get('assets', []):
                            asset_name = a['name'].split('/')[-1]
                            # Se for asset multibanda no futuro, o nome é o ID. 
                            # Se for por banda (atual), removemos o sufixo da banda para o cache de "existe"
                            if asset_name.endswith(f"_{band}"):
                                asset_name = asset_name[:-(len(band)+1)]
                            
                            target_key = 'assets_monthly' if period_type == 'monthly' else 'assets_annually'
                            if asset_name not in state[target_key]:
                                state[target_key].append(asset_name)
                    except Exception:
                        continue
        
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
            import gcsfs
            project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
            fs = gcsfs.GCSFileSystem(project=project)
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
            try:
                import gcsfs
                import os
                gcs_path = CacheManager._get_gcs_path()
                project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
                fs = gcsfs.GCSFileSystem(project=project, token='google_default')
                
                if state is None:
                    state = CacheManager._state
                
                state['updated_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
                state['country'] = CONFIG['country']
                
                with fs.open(gcs_path, 'w') as f:
                    json.dump(state, f, indent=2)
                
                CacheManager._state = state
            except Exception:
                pass # Silencioso: se não salvar o cache, o sistema reconstrói na próxima

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
