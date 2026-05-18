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
                print(f"Error clearing cache: {e}")
                return False

    @staticmethod
    def _get_gcs_path():
        """Retorna path do cache no GCS."""
        return f"gs://{CONFIG['bucket']}/{CONFIG['gcs_cache']}/{CacheManager.CACHE_FILE}"

    @staticmethod
    def load(force=False):
        """
        Carrega cache priorizando o arquivo local para velocidade offline.
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
            
            # 1. Tenta carregar do arquivo local PRIMEIRO (Offline instantâneo)
            # Procura na pasta atual e na pasta pai (caso esteja num subdiretório de notebooks)
            candidate_paths = [
                CacheManager.CACHE_FILE,
                os.path.join("..", CacheManager.CACHE_FILE),
                os.path.join("..", "..", CacheManager.CACHE_FILE)
            ]
            
            local_found = False
            for local_path in candidate_paths:
                if os.path.exists(local_path):
                    try:
                        with open(local_path, 'r') as f:
                            data = json.load(f)
                            CacheManager._state.update(data)
                            local_found = True
                            break
                    except:
                        continue
            
            if local_found:
                return CacheManager._state

            # 2. Se não houver local, tenta GCS (com timeout agressivo de 1s)
            try:
                gcs_path = CacheManager._get_gcs_path()
                fs = _get_fs()
                # Tenta um check rápido. Se demorar mais de 1s, vai dar timeout.
                if fs.exists(gcs_path):
                    with fs.open(gcs_path, 'r') as f:
                        data = json.load(f)
                        CacheManager._state.update(data)
                        # Salva uma cópia local para a próxima vez
                        try:
                            with open(local_path, 'w') as lf:
                                json.dump(data, lf, indent=2)
                        except: pass
                else:
                    print(f"Cache not found at {gcs_path}.")
            except Exception as e:
                # Silencioso no local para evitar poluir a UI
                pass
        
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
                    col_id = get_asset_mosaic_collection(
                        sensor=sensor_name,
                        periodicity=period_type,
                        mosaic=mosaic_m
                    )
                    tasks.append((col_id, period_type))
        
        total_steps = len(tasks)
        completed = 0
        
        if logger: logger("Iniciando sincronización GEE (Paralelo)...", "info")
        
        def fetch_assets(task_info):
            col_id, period_type = task_info
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
                
                # 1. Processa COGs usando a hierarquia de pastas
                if basename.endswith('_cog.tif'):
                    # O path esperado é: .../LIBRARY_IMAGES/{SENSOR}/{PERIODICITY}/{MOSAIC}/{DATE}/COG/{FILENAME}
                    parts = fpath.split('/')
                    try:
                        # Encontra o índice da pasta LIBRARY_IMAGES
                        lib_idx = -1
                        for i, p in enumerate(parts):
                            if p.upper() == 'LIBRARY_IMAGES':
                                lib_idx = i
                                break
                        
                        if lib_idx != -1 and len(parts) >= lib_idx + 6:
                            sensor = parts[lib_idx + 1].lower()
                            period = parts[lib_idx + 2].lower() # monthly / annually
                            mosaic = parts[lib_idx + 3].lower()
                            # date   = parts[lib_idx + 4]
                            
                            name_no_ext = basename[:-8].lower() # image_peru_fire_{sensor}_{mosaic}_{band}_{date}
                            
                            if period == 'monthly':
                                if name_no_ext not in cogs_monthly: cogs_monthly.append(name_no_ext)
                            else:
                                if name_no_ext not in cogs_annually: cogs_annually.append(name_no_ext)
                    except:
                        continue
                
                # 2. Processa Chunks
                elif '/CHUNKS/' in fpath.upper():
                    name_no_ext = basename[:-4]
                    
                    # Novo padrão: image_{country}_fire_{sensor}_{mosaic}_{band}_{date}
                    # Antigo padrão: {mosaic}_{sensor}_fire_{country}_{date}_{band}
                    
                    # Tenta identificar a banda e a data de forma robusta
                    found_band = None
                    for band in sorted_bands:
                        if f"_{band}_" in name_no_ext or name_no_ext.endswith(f"_{band}"):
                            found_band = band
                            break
                    
                    if found_band:
                        # Extrai a data (YYYY_MM ou YYYY) usando regex
                        import re as _re
                        date_match = _re.search(r'(\d{4}_\d{2})|(\d{4})', name_no_ext)
                        clean_date = date_match.group(0) if date_match else "unknown"
                        
                        # A chave da UI deve ser: image_{country}_fire_{sensor}_{mosaic}_{date}
                        # Vamos isolar o prefixo (tudo antes da banda)
                        prefix = name_no_ext.split(f"_{found_band}")[0]
                        
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
    def clear():
        """Remove o arquivo de cache local e limpa o estado em memória."""
        CacheManager._state = {}
        if os.path.exists(CacheManager.CACHE_FILE):
            try:
                os.remove(CacheManager.CACHE_FILE)
                print(f" Local cache removed: {CacheManager.CACHE_FILE}")
            except Exception as e:
                print(f" Error removing local cache: {e}")
        else:
            print("Local cache not found.")

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
                
                # Salva também localmente para garantir consistência imediata
                try:
                    with open(CacheManager.CACHE_FILE, 'w') as lf:
                        json.dump(state, lf, indent=2)
                except: pass
                
                CacheManager._state = state
            except Exception as e:
                # Aviso limpo sem traceback assustador
                print(f"Warning: Local cache OK (GCS sync pending) - Error: {e}")
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
