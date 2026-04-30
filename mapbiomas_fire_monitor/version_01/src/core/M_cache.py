"""
M_cache — Cache Manager
MapBiomas Fire Sentinel Monitor

Gerencia cache de estado de exports no GCS para carregamento rapido da interface.

O que é o cache?
----------------
O cache é um arquivo JSON salvo no GCS que mantém o registro de todos os assets
e chunks GCS já exportados. Ele permite que a interface do M1 carregue em segundos
(antes demorava ~2 minutos listando todos os arquivos).

Local do cache:
    gs://mapbiomas-fire/sudamerica/{country}/monitor/.cache/state.json

Estrutura:
{
  "updated_at": "2026-04-07T12:00:00Z",
  "country": "peru",
  "assets_monthly": ["s2_fire_peru_2024_01", ...],
  "assets_annually": ["s2_fire_peru_2024", ...],
  "gcs_chunks": {
    "s2_fire_peru_2024_01": ["red", "nir", "swir1", ...]
  }
}

Como funciona?
--------------
1. Ao carregar a interface: lê o cache do GCS (segundos). Se não existir, lista GEE e cria
2. Ao exportar: atualiza o cache automaticamente
3. Ao deletar: atualiza o cache automaticamente

Quando renovar o cache?
-----------------------
- Se a interface mostrar dados desatualizados
- Se houver exports/deleções feitas fora do notebook
- Se o cache foi corrompido ou deletado

Como renovar:
-------------
# Opção 1: Deletar o arquivo de cache no GCS
# O sistema recriará automaticamente ao carregar a interface

# Opção 2: Via código (requer gcsfs)
import gcsfs
fs = gcsfs.GCSFileSystem()
cache_path = "gs://mapbiomas-fire/sudamerica/peru/monitor/.cache/state.json"
fs.rm(cache_path)  # Deleta o cache

# Opção 3: Limpar cache em memória (reiniciar kernel)
from M_cache import CacheManager
CacheManager.reset()
"""

import json
import datetime
from M0_auth_config import CONFIG


class CacheManager:
    CACHE_FILE = "state.json"
    _state = None

    @staticmethod
    def _get_gcs_path():
        """Retorna path do cache no GCS."""
        gcs_base = CONFIG.get('gcs_base', f"sudamerica/{CONFIG['country']}/monitor")
        return f"gs://{CONFIG['bucket']}/{gcs_base}/.cache/{CacheManager.CACHE_FILE}"

    @staticmethod
    def load():
        """
        Carrega cache do GCS (rapido).
        Se cache nao existir, retorna dict vazio (sem listar GEE).
        Use build_cache_from_gee() para popular o cache na primeira vez.
        """
        if CacheManager._state is not None:
            return CacheManager._state
        
        CacheManager._state = {
            "updated_at": None,
            "country": CONFIG['country'],
            "assets_monthly": [],
            "assets_annually": [],
            "gcs_chunks": {}
        }
        
        try:
            import gcsfs
            gcs_path = CacheManager._get_gcs_path()
            # No Colab, usar o gcs_project (billing) separado do ee_project
            project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
            fs = gcsfs.GCSFileSystem(project=project)
            
            if fs.exists(gcs_path):
                with fs.open(gcs_path, 'r') as f:
                    CacheManager._state = json.load(f)
            else:
                # Se não existir, não é um erro, apenas retorna estado padrão
                pass
        except Exception as e:
            # Em vez de apenas 'pass', vamos pelo menos avisar se houver erro de permissão
            print(f"⚠️ Aviso: Falha ao ler cache do GCS: {e}")
        
        return CacheManager._state

    @staticmethod
    def build_cache_from_gee():
        """Popula cache listando assets do GEE (para primeira execucao)."""
        import ee
        from M0_auth_config import CONFIG, get_asset_mosaic_collection
        
        CacheManager._state['assets_monthly'] = []
        CacheManager._state['assets_annually'] = []
        bands = CONFIG.get('bands_all', ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'])
        
        # Listar assets mensais
        for band in bands:
            col_id = get_asset_mosaic_collection('monthly', band)
            try:
                result = ee.data.listAssets({'parent': col_id})
                for a in result.get('assets', []):
                    asset_name = a['name'].split('/')[-1]
                    if asset_name not in CacheManager._state['assets_monthly']:
                        CacheManager._state['assets_monthly'].append(asset_name)
            except Exception:
                pass
                
        # Listar assets anuais
        for band in bands:
            col_id = get_asset_mosaic_collection('yearly', band)
            try:
                result = ee.data.listAssets({'parent': col_id})
                for a in result.get('assets', []):
                    asset_name = a['name'].split('/')[-1]
                    if asset_name not in CacheManager._state['assets_annually']:
                        CacheManager._state['assets_annually'].append(asset_name)
            except Exception:
                pass
        
        CacheManager.save()
        return CacheManager._state

    @staticmethod
    def build_cache_from_gcs(logger=None, years=None):
        """Escaneia o GCS para detectar chunks existentes e atualizar o cache gcs_chunks."""
        from M0_auth_config import GLOBAL_OPTS, CONFIG, gcs_chunks_prefix

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

            for period in ['monthly', 'yearly']:
                # 1. SCAN CHUNKS
                base_prefix = gcs_chunks_prefix(period)
                full_base = f"{bucket}/{base_prefix}"

                if logger:
                    logger(f"Escaneando GCS (chunks): {full_base} ...", "info")

                try:
                    if fs.exists(full_base):
                        year_dirs = fs.ls(full_base, detail=False)
                        for y_dir in year_dirs:
                            y_val = y_dir.split('/')[-1]
                            if not y_val.isdigit(): continue
                            if years and int(y_val) not in years: continue

                            if period == 'monthly':
                                month_dirs = fs.ls(y_dir, detail=False)
                                for m_dir in month_dirs:
                                    m_val = m_dir.split('/')[-1]
                                    if not m_val.isdigit(): continue
                                    files = fs.ls(m_dir, detail=False)
                                    CacheManager._process_gcs_files(files, sorted_bands, gcs_chunks)
                            else:
                                files = fs.ls(y_dir, detail=False)
                                CacheManager._process_gcs_files(files, sorted_bands, gcs_chunks)
                except Exception as e:
                    if logger:
                        logger(f"Aviso ao listar chunks GCS ({period}): {e}", "warning")

                # 2. SCAN COGS
                from M0_auth_config import gcs_mosaic_prefix
                base_cog_prefix = gcs_mosaic_prefix(period)
                full_base_cog = f"{bucket}/{base_cog_prefix}"
                
                if logger:
                    logger(f"Escaneando GCS (cogs): {full_base_cog} ...", "info")

                try:
                    if fs.exists(full_base_cog):
                        year_dirs_cog = fs.ls(full_base_cog, detail=False)
                        for y_dir in year_dirs_cog:
                            y_val = y_dir.split('/')[-1]
                            if not y_val.isdigit(): continue
                            if years and int(y_val) not in years: continue

                            if period == 'monthly':
                                month_dirs_cog = fs.ls(y_dir, detail=False)
                                for m_dir in month_dirs_cog:
                                    m_val = m_dir.split('/')[-1]
                                    if not m_val.isdigit(): continue
                                    files_cog = fs.ls(m_dir, detail=False)
                                    CacheManager._process_cogs_files(files_cog, sorted_bands, cogs_monthly)
                            else:
                                files_cog = fs.ls(y_dir, detail=False)
                                CacheManager._process_cogs_files(files_cog, sorted_bands, cogs_annually)
                except Exception as e:
                    if logger:
                        logger(f"Aviso ao listar cogs GCS ({period}): {e}", "warning")

            state['gcs_chunks'] = gcs_chunks
            state['cogs_monthly'] = cogs_monthly
            state['cogs_annually'] = cogs_annually
            
            # Sincronizar também com o GEE
            if logger: logger("Sincronizando status GEE...", "info")
            gee_state = CacheManager.build_cache_from_gee()
            state['assets_monthly'] = gee_state.get('assets_monthly', [])
            state['assets_annually'] = gee_state.get('assets_annually', [])

            CacheManager._state = state
            CacheManager.save(state)

            if logger:
                total = sum(len(b) for b in gcs_chunks.values())
                logger(f"GCS escaneado: {len(gcs_chunks)} mosaicos, {total} bandas.", "success")

        except ImportError:
            if logger: logger("gcsfs não disponível.", "warning")
        except Exception as e:
            if logger: logger(f"Erro ao escanear GCS: {e}", "warning")

        return CacheManager._state

    @staticmethod
    def _process_gcs_files(files, sorted_bands, gcs_chunks):
        """Helper para parsear nomes de arquivos e identificar bandas."""
        for fpath in files:
            if not fpath.endswith('.tif'): continue
            basename = fpath.split('/')[-1]
            name_no_ext = basename[:-4]

            for band in sorted_bands:
                needle = f"_{band}"
                idx = name_no_ext.find(needle)
                if idx != -1:
                    after_band = idx + len(needle)
                    if after_band >= len(name_no_ext) or not name_no_ext[after_band].isalpha():
                        # mosaico_part: sentinel2_fire_peru_2024_01
                        mosaic_part = name_no_ext[:idx]
                        if mosaic_part not in gcs_chunks:
                            gcs_chunks[mosaic_part] = []
                        if band not in gcs_chunks[mosaic_part]:
                            gcs_chunks[mosaic_part].append(band)
                        break

    @staticmethod
    def _process_cogs_files(files_cog, sorted_bands, cogs_list):
        """Helper para parsear nomes de cogs."""
        for fpath in files_cog:
            if not fpath.endswith('_cog.tif'): continue
            basename = fpath.split('/')[-1]
            name_no_ext = basename[:-8] # remove _cog.tif
            if name_no_ext not in cogs_list:
                cogs_list.append(name_no_ext)

    @staticmethod
    def build_full_cache(logger=None, years=None):
        """Reconstrói o cache completo: lista assets GEE + escaneia chunks GCS."""
        CacheManager.build_cache_from_gee()
        CacheManager.build_cache_from_gcs(logger=logger, years=years)
        return CacheManager._state

    @staticmethod
    def save(state=None):
        """
        Salva cache no GCS (apenas se ja existir).
        """
        try:
            import gcsfs
            gcs_path = CacheManager._get_gcs_path()
            project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
            fs = gcsfs.GCSFileSystem(project=project)
            
            if state is None:
                state = CacheManager._state
            
            state['updated_at'] = datetime.datetime.utcnow().isoformat() + 'Z'
            state['country'] = CONFIG['country']
            
            with fs.open(gcs_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            CacheManager._state = state
        except:
            pass

    @staticmethod
    def get_state():
        """Retorna estado atual em memoria."""
        if CacheManager._state is None:
            return CacheManager.load()
        return CacheManager._state

    @staticmethod
    def add_asset(name, period):
        """Adiciona asset ao cache apos export."""
        state = CacheManager.get_state()
        
        if period == 'monthly':
            if name not in state['assets_monthly']:
                state['assets_monthly'].append(name)
        else:
            if name not in state['assets_annually']:
                state['assets_annually'].append(name)
        
        CacheManager.save(state)

    @staticmethod
    def remove_asset(name, period):
        """Remove asset do cache apos delete."""
        state = CacheManager.get_state()
        
        if period == 'monthly':
            if name in state['assets_monthly']:
                state['assets_monthly'].remove(name)
        else:
            if name in state['assets_annually']:
                state['assets_annually'].remove(name)
        
        CacheManager.save(state)

    @staticmethod
    def add_gcs_chunk(name, bands):
        """Adiciona chunks GCS ao cache apos export."""
        state = CacheManager.get_state()
        
        if name not in state['gcs_chunks']:
            state['gcs_chunks'][name] = []
        
        for band in bands:
            if band not in state['gcs_chunks'][name]:
                state['gcs_chunks'][name].append(band)
        
        CacheManager.save(state)

    @staticmethod
    def remove_gcs_chunk(name):
        """Remove chunks GCS do cache apos delete."""
        state = CacheManager.get_state()
        
        if name in state['gcs_chunks']:
            del state['gcs_chunks'][name]
        
        CacheManager.save(state)

    @staticmethod
    def is_asset_exported(name, period):
        """Verifica se asset ja foi exportado."""
        state = CacheManager.get_state()
        
        if period == 'monthly':
            return name in state['assets_monthly']
        else:
            return name in state['assets_annually']

    @staticmethod
    def has_gcs_bands(name, bands):
        """Verifica se todos os bands foram exportados para GCS."""
        state = CacheManager.get_state()
        
        if name not in state['gcs_chunks']:
            return False
        
        existing = set(state['gcs_chunks'][name])
        required = set(bands)
        
        return required.issubset(existing)

    @staticmethod
    def reset():
        """Limpa cache em memoria."""
        CacheManager._state = None
