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
from M0_auth_config import CONFIG, _get_fs

class CacheManager:
    CACHE_FILE = "state.json"
    _state = None
    _lock = threading.Lock() # Lock local para evitar race conditions no mesmo kernel

    @staticmethod
    def clear():
        """Deleta o arquivo de cache no GCS e reseta o estado local."""
        with CacheManager._lock:
            try:
                gcs_path = CacheManager._get_gcs_path()
                fs = _get_fs()
                if fs.exists(gcs_path):
                    fs.rm(gcs_path)
                CacheManager._state = None
                return True
            except Exception as e:
                print(f"Erro ao limpar cache: {e}")
                return False

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
        # Todos os métodos de mosaico disponíveis para este país
        mosaic_methods = CONFIG.get('mosaic_methods', ['minnbr', 'minnbr_buffer'])
        # CORRIGIDO: Escanear TODOS os sensores relevantes, não apenas o GLOBAL_OPTS atual
        # (o sensor padrão pode ser 'landsat' mas os dados podem ser de 'sentinel2')
        all_sensors = ['sentinel2', 'landsat']  # Expandir conforme necessário
        tasks = []
        
        for sensor_name in all_sensors:
            for period_type in ['monthly', 'yearly']:
                for mosaic_m in mosaic_methods:
                    for band in bands:
                        col_id = get_asset_mosaic_collection(
                            sensor=sensor_name.upper(),
                            periodicity=period_type,
                            band=band,
                            mosaic=mosaic_m.upper()
                        )
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
                        # O asset já tem nome completo incluindo a banda
                        # Normalizar para lowercase para compatibilidade com a UI
                        asset_name = a['name'].split('/')[-1].lower()
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
                    name_lower = asset_name.lower()
                    if name_lower not in state[target_key]:
                        state[target_key].append(name_lower)
                
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
        from M0_auth_config import CONFIG, _gcs_library_base

        bands_all = CONFIG.get('bands_all', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'])
        sorted_bands = sorted(bands_all, key=len, reverse=True)

        state = CacheManager.get_state()
        gcs_chunks = {}
        cogs_monthly = []
        cogs_annually = []

        try:
            fs = _get_fs()
            
            bucket = CONFIG['bucket']
            
            # CORRIGIDO: Escanear a raiz de TODOS os sensores/métodos
            # (antes usava _gcs_library_base() que dependia do GLOBAL_OPTS['SENSOR'] atual
            # e limitava o scan a apenas um sensor)
            base_search = f"{bucket}/{CONFIG['gcs_library_images']}"
            
            if logger: logger(f"Escaneando GCS: gs://{base_search} ...", "info")
            
            # Listagem recursiva é mais lenta mas garante sincronia total
            all_files = fs.find(base_search)
            
            for fpath in all_files:
                if not fpath.endswith('.tif'): continue
                
                # Identifica se é COG ou Chunk
                basename = fpath.split('/')[-1]
                
                # 1. Processa COGs
                if basename.endswith('_cog.tif'):
                    name_no_ext = basename[:-8].lower() # remove _cog.tif e normaliza case
                    if '/monthly/' in fpath:
                        if name_no_ext not in cogs_monthly: cogs_monthly.append(name_no_ext)
                    else:
                        if name_no_ext not in cogs_annually: cogs_annually.append(name_no_ext)
                
                # 2. Processa Chunks
                elif '/chunks/' in fpath:
                    name_no_ext = basename[:-4]
                    
                    # Novo padrão: image_{country}_fire_{sensor}_{mosaic}_{band}_{date}
                    # Antigo padrão: {mosaic}_{sensor}_fire_{country}_{date}_{band}
                    
                    found_band = None
                    for band in sorted_bands:
                        needle = f"_{band}_" # No novo padrão, a banda está cercada por underscores
                        if needle in name_no_ext:
                            found_band = band
                            break
                    
                    if found_band:
                        # Extrai a parte antes da banda e a data depois da banda
                        parts = name_no_ext.split(f"_{found_band}_")
                        prefix = parts[0]
                        date_part = parts[1]
                        
                        # BUG FIX: date_part pode conter coordenadas de chunk
                        # Ex: '2026_03_0000065536-0000131072' -> devemos usar apenas '2026_03'
                        import re as _re
                        date_match = _re.search(r'(\d{4}_\d{2})', date_part)
                        clean_date = date_match.group(1) if date_match else date_part.split('_0')[0]
                        
                        # A chave da UI: image_{country}_fire_{sensor}_{mosaic}_{date}
                        # Normalizar para lowercase para garantir compatibilidade com a busca da UI
                        mosaic_key = f"{prefix}_{clean_date}".lower()
                        
                        if mosaic_key not in gcs_chunks:
                            gcs_chunks[mosaic_key] = []
                        if found_band not in gcs_chunks[mosaic_key]:
                            gcs_chunks[mosaic_key].append(found_band)
                        continue

                    # Fallback para o padrão antigo: {mosaic}_{sensor}_fire_{country}_{date}_{band}
                    # Ex: minnbr_sentinel2_fire_peru_2026_01_dayOfYear...
                    found_legacy = False
                    for band in sorted_bands:
                        needle = f"_{band}"
                        if needle in name_no_ext:
                            # Tenta reconstruir a chave da UI (que usa o novo padrão)
                            # Mas para o Cache, precisamos que a chave case com o que o M1 gera.
                            # Se o arquivo é antigo, vamos mapeá-lo para a chave que a UI usa hoje.
                            parts = name_no_ext.split(needle)
                            main_part = parts[0] # minnbr_sentinel2_fire_peru_2026_01
                            
                            # Tenta extrair os componentes do nome antigo
                            p = main_part.split('_')
                            if len(p) >= 5:
                                m_type = p[0]
                                s_type = p[1]
                                c_code = p[3]
                                d_part = p[4]
                                if len(p) > 5: d_part += "_" + p[5] # para YYYY_MM
                                
                                # Chave compatível com mosaic_name atual: image_{country}_fire_{sensor}_{mosaic}_{date}
                                mosaic_key = f"image_{c_code}_fire_{s_type}_{m_type}_{d_part}"
                                
                                if mosaic_key not in gcs_chunks:
                                    gcs_chunks[mosaic_key] = []
                                if band not in gcs_chunks[mosaic_key]:
                                    gcs_chunks[mosaic_key].append(band)
                                found_legacy = True
                                break
                    if found_legacy: continue

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
                print(f"Aviso: Cache local OK (GCS sync pendente) - Erro: {e}")
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
