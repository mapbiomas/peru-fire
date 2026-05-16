import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import rasterio
from rasterio.mask import mask
from M0_auth_config import CONFIG, GLOBAL_OPTS, gcs_path, model_path
from M_cache import _get_fs


def list_sample_collections_gcs(force_refresh=False):
    """Lista amostras com prioridade TOTAL offline. Só toca no GCS se force_refresh=True."""
    cache = _load_m4_cache()
    if cache.get('known_samples') and not force_refresh:
        return cache['known_samples']
    
    try:
        from M0_auth_config import CONFIG, GLOBAL_OPTS
        # Timeout curtíssimo para não travar a UI se a rede estiver lenta
        fs = _get_fs()
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'monitor_01')
        path = f"{CONFIG['bucket']}/{CONFIG['gcs_library_samples']}/{campaign}"
        
        if not fs.exists(path):
            return []
            
        files = fs.ls(path) # ls simples não costuma travar tanto quanto find
        samples = sorted([f.split('/')[-1].replace('.csv', '') for f in files if f.endswith('.csv')], reverse=True)
        
        cache['known_samples'] = samples
        _save_m4_cache(cache)
        return samples
    except Exception:
        # Se falhar qualquer coisa (rede, timeout), usa o que tem no cache ou vazio
        return cache.get('known_samples', [])

def list_campaigns_gcs():
    """Lista as campanhas (subpastas) disponíveis em LIBRARY_SAMPLES no GCS."""
    try:
        from M0_auth_config import CONFIG
        fs = _get_fs()
        path = f"{CONFIG['bucket']}/{CONFIG['gcs_library_samples']}"
        if not fs.exists(path):
            return ['monitor_01']
        
        items = fs.ls(path)
        campaigns = []
        for item in items:
            name = item['name'] if isinstance(item, dict) else item
            if not name.endswith('.csv') and not name.endswith('.json') and not name.endswith('.npz'):
                c_name = name.split('/')[-1]
                if c_name and not c_name.startswith('.'):
                    campaigns.append(c_name)
        
        if not campaigns: return ['monitor_01']
        return sorted(list(set(campaigns)))
    except:
        return ['monitor_01']

def extract_pixels_from_gcs(sample_groups, bands_config, logger=None):
    """
    Extrai píxeis do GCS baseado em uma configuração flexível de bandas.
    Validando existência prévia para evitar erros silenciosos.
    """
    from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name
    from M_cache import CacheManager
    
    fs = _get_fs()
    state = CacheManager.load() or {}
    cogs_avail = state.get('cogs_monthly', []) + state.get('cogs_annually', [])
    
    dfs = []
    for group in sample_groups:
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'monitor_01')
        sample_path = f"{CONFIG['bucket']}/{CONFIG['gcs_library_samples']}/{campaign}/{group}.csv"
        if logger: logger(f"Leyendo muestras: {group}.csv", "info")
        try:
            with fs.open(sample_path, 'r') as f:
                temp_df = pd.read_csv(f)
                
                # --- CORREÇÃO DE DATA (PERIOD) ---
                # Extrai a data do nome do arquivo (ex: ..._2025_10.csv)
                # O padrão é que os últimos dois campos (ou um) sejam a data
                file_parts = group.split('_')
                file_date = ""
                if file_parts[-2].isdigit() and len(file_parts[-2]) == 4: # YYYY_MM
                    file_date = f"{file_parts[-2]}_{file_parts[-1]}"
                elif file_parts[-1].isdigit() and len(file_parts[-1]) == 4: # YYYY
                    file_date = file_parts[-1]
                
                if not temp_df.empty and 'period' in temp_df.columns:
                    p_found = temp_df['period'].unique().tolist()
                    
                    # Se encontrarmos uma data absurda (como 2026_04) mas o arquivo diz outra coisa,
                    # forçamos a data do arquivo para que a extração funcione.
                    if file_date and any(int(p.split('_')[0]) > 2025 for p in p_found):
                        if logger: logger(f"  [AVISO] Se ha detectado una fecha futura {p_found} no CSV. Corrigiendo para {file_date}...", "warning")
                        temp_df['period'] = file_date
                        p_found = [file_date]
                    
                    if logger: logger(f"  [Buscar] Contenido: {len(temp_df)} puntos | Períodos: {p_found}", "info")
                dfs.append(temp_df)
        except Exception as e:
            if logger: logger(f"Error al leer {group}: {e}", "error")
            
    if not dfs: return np.array([]), np.array([])
        
    df = pd.concat(dfs, ignore_index=True)
    df['geometry'] = df['.geo'].apply(lambda x: shape(json.loads(x)))
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
    
    X_all, y_all = [], []
    periods = gdf['period'].unique()
    bands_sorted = sorted(bands_config.keys())
    
    for p in periods:
        subset = gdf[gdf['period'] == p]
        
        # --- INTELIGÊNCIA: VALIDAR SE A DATA FAZ SENTIDO ---
        # Se as amostras vieram de um arquivo chamado ..._2025_10.csv, 
        # mas o 'p' (period) dentro dele é 2026_04, priorizamos a data do arquivo
        # se ela for detectada.
        
        # Buscamos a data no nome do grupo/arquivo original (via subset['_source_group'])
        # Nota: vamos injetar essa info na leitura do CSV
        
        geometries = subset.geometry.tolist()
        labels = subset['fire'].tolist()
        
        parts = str(p).split('_')
        y = int(parts[0]); m = int(parts[1]) if len(parts) > 1 else None
        periodicity = 'monthly' if m else 'annually'
        
        # --- VERIFICAÇÃO PRÉVIA DE DISPONIBILIDADE ---
        missing_bands = []
        band_paths = {}
        
        for b in bands_sorted:
            s_name = bands_config[b].get('sensor').lower()
            m_type = bands_config[b].get('mosaic').lower()
            
            # Constrói o ID único do COG (ex: image_peru_fire_sentinel2_minnbr_2025_10_blue)
            cog_id = f"{mosaic_name(y, m, periodicity, band=b, mosaic=m_type, sensor=s_name)}".lower()
            
            if cog_id not in cogs_avail:
                missing_bands.append(f"{s_name}/{m_type}/{b}")
                continue
            
            # Constrói o path real do COG usando os auxiliares do M0
            from M0_auth_config import monthly_cog_path, yearly_cog_path
            if periodicity == 'monthly':
                rel_folder = monthly_cog_path(y, m, mosaic=m_type, sensor=s_name)
            else:
                rel_folder = yearly_cog_path(y, mosaic=m_type, sensor=s_name)
            
            # O arquivo real no GCS é sensível a maiúsculas (Case Sensitive)
            b_correct = 'dayOfYear' if b.lower() == 'dayofyear' else b
            m_file_name = f"{mosaic_name(y, m, periodicity, band=b_correct, mosaic=m_type, sensor=s_name)}_cog.tif"
            band_paths[b] = f"gs://{CONFIG['bucket']}/{rel_folder}/{m_file_name}"

        if missing_bands:
            if logger: logger(f"[AVISO] Saltar período {p}: Faltan {len(missing_bands)} bandas ({', '.join(missing_bands)})", "warning")
            continue

        if logger: logger(f"[OK] Mosaicos OK para {p}: {len(band_paths)} bandas listas para la extracción.", "info")
        if logger: logger(f"[GCS] Extrayendo {len(geometries)} muestras de {p}...", "info")
        
        # --- LEITURA REAL DAS BANDAS ---
        if logger: logger(f"[OK] Mosaicos OK para {p}: {len(band_paths)} bandas listas para la extracción.", "info")
        if logger: logger(f"[GCS] Extrayendo {len(geometries)} muestras de {p}...", "info")
        
        sources = {}
        local_files = []
        
        try:
            # 1. Abrir todos os datasets para o período
            for b in bands_sorted:
                cog_path = band_paths[b]
                is_colab = 'COLAB_RELEASE_TAG' in os.environ
                src_path = f"/vsigs/{cog_path.replace('gs://', '')}" if is_colab else None
                
                if not is_colab:
                    from M0_auth_config import get_temp_dir
                    local_file = os.path.join(get_temp_dir(), os.path.basename(cog_path))
                    if logger: logger(f"  [Baixar] Bajando banda {b}...", "info")
                    fs.get(cog_path, local_file)
                    src_path = local_file
                    local_files.append(local_file)
                
                sources[b] = rasterio.open(src_path)

            # 2. Extração Síncrona (Garante que cada pixel tenha todas as bandas)
            band_pixels_acc = [[] for _ in bands_sorted]
            labels_acc = []
            
            for geom, label in zip(geometries, labels):
                try:
                    temp_data = {}
                    combined_mask = None
                    
                    # Lemos todas as bandas para esta geometria
                    valid_geom = True
                    for b in bands_sorted:
                        out_image, _ = mask(sources[b], [geom], crop=True, filled=False)
                        if out_image.mask.all():
                            valid_geom = False; break
                        
                        # Acumulamos a máscara (OR lógico nos bits de NoData)
                        if combined_mask is None:
                            combined_mask = out_image.mask[0]
                        else:
                            combined_mask = combined_mask | out_image.mask[0]
                        
                        temp_data[b] = out_image.data[0]
                    
                    if valid_geom and combined_mask is not None:
                        final_valid_mask = ~combined_mask
                        num_valid = np.sum(final_valid_mask)
                        
                        if num_valid > 0:
                            for i, b in enumerate(bands_sorted):
                                band_pixels_acc[i].extend(temp_data[b][final_valid_mask])
                            labels_acc.extend([label] * num_valid)
                except:
                    continue
            
            # 3. Empilhar dados do período
            if labels_acc:
                X_period = np.column_stack([np.array(b_px) for b_px in band_pixels_acc])
                X_all.append(X_period)
                y_all.append(np.array(labels_acc))
                
        except Exception as e:
            if logger: logger(f"[ERRO] Error crítico en período {p}: {e}", "error")
        finally:
            for s in sources.values(): s.close()
            for f in local_files:
                if os.path.exists(f): os.remove(f)

    if not X_all: return np.array([]), np.array([])
    return np.concatenate(X_all, axis=0), np.concatenate(y_all, axis=0)

def compute_normalizer(X):
    stats = {}
    for i in range(X.shape[1]):
        col = X[:, i]
        stats[i] = (float(col.mean()), float(col.std() + 1e-8))
    return stats

def normalize(X, stats):
    X_norm = X.copy().astype(np.float32)
    for i, (mean, std) in stats.items():
        X_norm[:, i] = (X_norm[:, i] - mean) / std
    return X_norm

