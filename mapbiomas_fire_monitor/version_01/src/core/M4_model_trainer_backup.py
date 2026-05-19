"""
M4 — Entrenador del Modelo (DNN)
MapBiomas Fuego Sentinel Monitor

Maneja:
  1. Seleção múltipla de amostras via Matriz (estilo M1/M2).
  2. Extração de píxeis de mosaicos GCS (COG) salvando em numpy.
  3. Divisão de treino / validação e normalização explícita.
  4. Persistência rica (pesos, amostras, píxeis, metadados).
  5. Análises complementares postergadas (Monitoramento).
"""

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

# TensorFlow movido para dentro dos métodos para evitar travamento de DLL no import global.
TF_AVAILABLE = None
TF_ERROR = None

def _get_tf():
    """Carrega o TensorFlow apenas quando necessário (Lazy Load)."""
    global TF_AVAILABLE, TF_ERROR
    if TF_AVAILABLE is not None: return tf if TF_AVAILABLE else None
    
    try:
        import tensorflow.compat.v1 as _tf
        _tf.compat.v1.disable_v2_behavior()
        globals()['tf'] = _tf
        TF_AVAILABLE = True
        return _tf
    except Exception as e:
        TF_AVAILABLE = False
        TF_ERROR = str(e)
        return None

import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import matplotlib.pyplot as plt
from datetime import datetime

import time
from M0_auth_config import CONFIG, GLOBAL_OPTS, gcs_path, model_path
from M_cache import _get_fs
from M_ui_components import PipelineStepUI

# ─── EXTRAÇÃO DE DADOS (GCS) ──────────────────────────────────────────────────

# Mapeamento de bandas permitidas por combinação Sensor+Mosaico
# Isso garante que a interface mostre apenas o que existe no GCS
SENSOR_MOSAIC_BANDS = {
    ('sentinel2', 'minnbr'):        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
    ('sentinel2', 'minnbr_buffer'): ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
    ('landsat',   'minnbr'):        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
    ('hls',       'minnbr'):        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'],
}

ALL_BANDS_LIST = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']

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
    except Exception:
        return ['monitor_01']

def _load_m4_cache():
    """Lê o cache local com busca em múltiplos níveis de diretório."""
    filename = "m4_ranking_cache.json"
    candidates = [filename, os.path.join("..", filename), os.path.join("..", "..", filename)]
    
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f: return json.load(f)
            except Exception: continue
    return {}

def _save_m4_cache(data):
    """Salva o estado no arquivo local mais próximo."""
    try:
        with open("m4_ranking_cache.json", 'w') as f:
            json.dump(data, f, indent=2)
    except Exception: pass
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
                except Exception:
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


# ─── NORMALIZACIÓN E DNN ──────────────────────────────────────────────────────

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

class ModelTrainer:
    def __init__(self, num_input, layers=None, lr=None, seed=42):
        _get_tf()
        self.num_input  = num_input
        self.layers     = layers or CONFIG['model_layers']
        self.lr         = lr     or CONFIG['model_lr']
        self.seed       = seed
        self.graph      = None
        self.session    = None
        self.norm_stats = None

    def _build_graph(self):
        tf.reset_default_graph()
        tf.set_random_seed(self.seed)

        self.x   = tf.placeholder(tf.float32, [None, self.num_input], name='x')
        self.y   = tf.placeholder(tf.float32, [None, 1],              name='y')
        self.keep_prob = tf.placeholder(tf.float32, name='keep_prob')

        layer = self.x
        for i, n_units in enumerate(self.layers):
            layer = tf.keras.layers.Dense(
                n_units,
                activation=tf.nn.relu,
                kernel_initializer=tf.keras.initializers.glorot_uniform(seed=self.seed),
                name=f'fc_{i}'
            )(layer)
            layer = tf.nn.dropout(layer, rate=1 - self.keep_prob)
        
        self.latent_tensor = layer # Captura para visualização ao vivo
        self.logits = tf.keras.layers.Dense(1, name='output')(layer)
        self.pred   = tf.nn.sigmoid(self.logits)

        self.loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(labels=self.y, logits=self.logits)
        )
        self.train_op = tf.train.AdamOptimizer(self.lr).minimize(self.loss)
        self.saver    = tf.train.Saver()

    def train(self, X_train, y_train, X_val=None, y_val=None, batch_size=None, n_iters=None, keep_prob=0.8, logger=None, update_chart_fn=None, snapshot_dir=None):
        self._X_raw = X_train
        self._y_raw = y_train
        
        batch_size = batch_size or CONFIG.get('model_batch', 1000)
        n_iters    = n_iters    or CONFIG.get('model_iters', 5000)

        # Normalização baseada SEMPRE no conjunto de treino para evitar data leakage
        self.norm_stats = compute_normalizer(X_train)
        X_tr = normalize(X_train, self.norm_stats)
        y_tr = y_train.reshape(-1, 1)

        if X_val is not None and y_val is not None:
            X_te = normalize(X_val, self.norm_stats)
            y_te = y_val.reshape(-1, 1)
        else:
            # Fallback para split interno se não for provido
            n = len(X_tr)
            idx = np.random.permutation(n)
            n_split = int(n * 0.8)
            X_te = X_tr[idx[n_split:]]
            y_te = y_tr[idx[n_split:]]
            X_tr = X_tr[idx[:n_split]]
            y_tr = y_tr[idx[:n_split]]

        n_train = len(X_tr)

        # Amostra fixa para visualização ao vivo (Playground Style)
        viz_idx = np.random.choice(len(X_te), min(500, len(X_te)), replace=False)
        X_viz, y_viz = X_te[viz_idx], y_te[viz_idx]

        self._build_graph()
        history = {'loss': [], 'acc': [], 'val_acc': [], 'steps': []}
        # Data accumulation for time-travel
        snapshots_data = {'y_true': y_viz.flatten()}

        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            self.session = sess

            for i in range(1, n_iters + 1):
                b_idx = np.random.randint(0, n_train, batch_size)
                _, loss_val = sess.run(
                    [self.train_op, self.loss],
                    feed_dict={self.x: X_tr[b_idx], self.y: y_tr[b_idx], self.keep_prob: keep_prob}
                )

                if i % max(1, n_iters // 20) == 0 or i == n_iters:
                    pred_tr = sess.run(self.pred, feed_dict={self.x: X_tr, self.y: y_tr, self.keep_prob: 1.0})
                    acc_tr = ((pred_tr > 0.5).astype(int) == y_tr.astype(int)).mean()

                    pred_te = sess.run(self.pred, feed_dict={self.x: X_te, self.y: y_te, self.keep_prob: 1.0})
                    acc_te = ((pred_te > 0.5).astype(int) == y_te.astype(int)).mean()

                    history['steps'].append(i)
                    history['loss'].append(float(loss_val))
                    history['acc'].append(float(acc_tr))
                    history['val_acc'].append(float(acc_te))

                    # Extração de dados para o Playground Live
                    embeds, preds_viz = sess.run(
                        [self.latent_tensor, self.pred], 
                        feed_dict={self.x: X_viz, self.keep_prob: 1.0}
                    )
                    
                    # Accumulate for time-travel
                    step_idx = len(history['steps']) - 1
                    snapshots_data[f'embeds_{step_idx}'] = embeds
                    snapshots_data[f'preds_{step_idx}'] = preds_viz.flatten()

                    if logger:
                        logger(f"Iter {i:5d}/{n_iters} | Loss: {loss_val:.4f} | Acc Treino: {acc_tr:.3f} | Validação: {acc_te:.3f}", "info")
                    
                    if update_chart_fn:
                        update_chart_fn(history, embeds, preds_viz.flatten(), y_viz)

            self._saved_vars = {v.name: sess.run(v) for v in tf.global_variables()}
            self._history = history
            self.snapshot_dir = snapshot_dir
            
            # Salva o arquivo de dados de snapshots se o diretório existir
            if snapshot_dir:
                np.savez_compressed(os.path.join(snapshot_dir, "snapshots_data.npz"), **snapshots_data)

        return history

    def evaluate(self):
        from sklearn.metrics import confusion_matrix, classification_report
        
        X_norm = normalize(self._X_raw, self.norm_stats)
        layer = X_norm
        for i in range(len(self.layers)):
            W = self._saved_vars[f'fc_{i}/kernel:0']
            b = self._saved_vars[f'fc_{i}/bias:0']
            layer = np.maximum(0, np.dot(layer, W) + b)
            
        W_out = self._saved_vars['output/kernel:0']
        b_out = self._saved_vars['output/bias:0']
        logits = np.dot(layer, W_out) + b_out
        # Sigmoid robusta para evitar overflow
        preds = (1 / (1 + np.exp(-np.clip(logits, -20, 20)))).flatten() > 0.5
        
        cm = confusion_matrix(self._y_raw, preds)
        rep = classification_report(self._y_raw, preds, output_dict=True, zero_division=0)
        return cm, rep

    def load(self, training_id, shortname):
        import subprocess, tempfile
        from M0_auth_config import GLOBAL_OPTS, model_path
        base_path = model_path(training_id, shortname)
        fs = _get_fs()

        with tempfile.TemporaryDirectory() as tmpdir:
            for fname in ['weights.npz', 'metadata.json']:
                src = gcs_path(f"{base_path}/{fname}")
                dest = os.path.join(tmpdir, fname)
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            with open(os.path.join(tmpdir, 'metadata.json')) as f:
                hp = json.load(f)
                
            self.num_input = hp['num_input']
            self.layers = hp['layers']
            self.lr = hp.get('lr', 0.001)
            self._bands_input = hp.get('bands_input')
            self.norm_stats = {int(k): tuple(v) for k, v in hp['norm_stats'].items()}
            
            self._saved_vars = dict(np.load(os.path.join(tmpdir, 'weights.npz')))
            
    def predict(self, X_raw):
        """Aplica a inferência (forward pass manual usando os pesos numpy)."""
        if not hasattr(self, '_saved_vars'):
            raise RuntimeError("Modelo não treinado/carregado.")
            
        layer = normalize(X_raw, self.norm_stats)
        for i in range(len(self.layers)):
            W = self._saved_vars[f'fc_{i}/kernel:0']
            b = self._saved_vars[f'fc_{i}/bias:0']
            layer = np.maximum(0, np.dot(layer, W) + b)
            
        W_out = self._saved_vars['output/kernel:0']
        b_out = self._saved_vars['output/bias:0']
        logits = np.dot(layer, W_out) + b_out
        
        # Sigmoid robusta para evitar overflow
        preds = 1 / (1 + np.exp(-np.clip(logits, -20, 20)))
        return preds.flatten()

    def get_embeddings(self, X_raw):
        """Extrai os embeddings (penúltima camada) usando os pesos numpy."""
        if not hasattr(self, '_saved_vars'):
            raise RuntimeError("Modelo não treinado/carregado.")
            
        layer = normalize(X_raw, self.norm_stats)
        # Passa por todas as camadas ocultas
        for i in range(len(self.layers)):
            W = self._saved_vars[f'fc_{i}/kernel:0']
            b = self._saved_vars[f'fc_{i}/bias:0']
            layer = np.maximum(0, np.dot(layer, W) + b)
            
        return layer

    @staticmethod
    def delete_model(training_id, shortname):
        """Deleta recursivamente a pasta do modelo no GCS usando GCSFS."""
        from M_cache import _get_fs
        from M0_auth_config import CONFIG
        fs = _get_fs()
        base_uri = model_path(training_id, shortname)
        # Caminho completo para o gcsfs (ex: bucket/models/...)
        full_path = f"{CONFIG['bucket']}/{base_uri}"
        
        print(f" Eliminando carpeta del modelo (GCSFS): {full_path}")
        try:
            if fs.exists(full_path):
                fs.rm(full_path, recursive=True)
            return True
        except Exception as e:
            raise RuntimeError(f"No se pudo eliminar de GCS: {e}")

    def save_projector_files(self, training_id, shortname, X, y, logger=None):
        """Gera e salva arquivos .tsv para o TensorBoard Projector no GCS."""
        import tempfile, subprocess
        from M0_auth_config import GLOBAL_OPTS
        base_path = model_path(training_id, shortname)
        
        if logger: logger("Generando embeddings para visualización (Projector)...", "info")
        embeddings = self.get_embeddings(X)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Vectors file (.tsv)
            vec_file = os.path.join(tmpdir, 'vectors.tsv')
            np.savetxt(vec_file, embeddings, delimiter='\t', fmt='%.6f')
            
            # 2. Metadata file (.tsv)
            meta_file = os.path.join(tmpdir, 'metadata.tsv')
            with open(meta_file, 'w', encoding='utf-8') as f:
                f.write("Index\tClass\tLabel\n")
                for i, val in enumerate(y):
                    label = "Fuego" if val == 1 else "No-Fuego"
                    f.write(f"{i}\t{val}\t{label}\n")
            
            # Upload to GCS
            dest_dir = f"{base_path}/projector"
            fs = _get_fs()
            for fname in ['vectors.tsv', 'metadata.tsv']:
                src = os.path.join(tmpdir, fname)
                dest = f"{CONFIG['bucket']}/{dest_dir}/{fname}"
                if logger: logger(f"  [Enviar] Subiendo {fname} a GCS...", "info")
                fs.put(src, dest)
            
            if logger: 
                logger(f"[OK] Arquivos do Projector salvos em: {dest_dir}", "info")
                logger(f"[Dica] Dica: Baixe-os e suba em https://projector.tensorflow.org/", "info")

    def save(self, training_id, shortname, comment="", logger=None):
        import subprocess, tempfile
        from M0_auth_config import GLOBAL_OPTS
        base_path = model_path(training_id, shortname)
        fs = _get_fs()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Weights
            np.savez(os.path.join(tmpdir, 'weights.npz'), **self._saved_vars)

            # 2. Metadata
            hp = {
                'training_id':  training_id,
                'shortname':    shortname,
                'country':      CONFIG['country'],
                'sensor':       ', '.join(GLOBAL_OPTS['SENSOR']) if isinstance(GLOBAL_OPTS['SENSOR'], list) else GLOBAL_OPTS['SENSOR'],
                'bands_input':  getattr(self, '_bands_input', CONFIG['bands_model_default']),
                'bands_config': getattr(self, '_bands_config', {}), # Nova configuração multisensor
                'num_input':    self.num_input,
                'layers':       self.layers,
                'lr':           self.lr,
                'training_date': datetime.now().isoformat(),
                'norm_stats':   {str(k): list(v) for k, v in self.norm_stats.items()},
                'history':      self._history,
                'sample_collections': getattr(self, '_sample_collections', []),
                'sample_count': getattr(self, '_sample_count', {}),
                'comment':      comment,
                'rating':       0, 
            }
            with open(os.path.join(tmpdir, 'metadata.json'), 'w') as f:
                json.dump(hp, f, indent=2)

            for fname in ['weights.npz', 'metadata.json']:
                src  = os.path.join(tmpdir, fname)
                dest = f"{CONFIG['bucket']}/{base_path}/{fname}"
                fs.put(src, dest)
            
            # 2.5 Metrics
            if logger: logger("Generación y guardado de métricas de evaluación...", "info")
            cm, rep = self.evaluate()
            
            # --- NOTA IA AUTOMÁTICA (Baseada em regras técnicas) ---
            acc = rep.get('accuracy', 0)
            f1_fire = rep.get('1', {}).get('f1-score', 0)
            auto_rating = 1
            if f1_fire > 0.90 and acc > 0.95: auto_rating = 5
            elif f1_fire > 0.80 and acc > 0.90: auto_rating = 4
            elif f1_fire > 0.70 and acc > 0.85: auto_rating = 3
            elif f1_fire > 0.50: auto_rating = 2

            # --- SNAPSHOT DE DIAGNÓSTICO E t-SNE PARA CARGA INSTANTÂNEA ---
            try:
                from sklearn.decomposition import PCA
                idx_snap = np.random.choice(len(self._X_raw), min(800, len(self._X_raw)), replace=False)
                emb_snap = self.get_embeddings(self._X_raw[idx_snap])
                prd_snap = self.predict(self._X_raw[idx_snap])
                pca_snap = PCA(n_components=3); coords_pca = pca_snap.fit_transform(emb_snap)
                diag_snapshot = {
                    'pca_coords': coords_pca.tolist(),
                    'tsne_coords': getattr(self, 'tsne_snapshot', None), 
                    'preds': prd_snap.flatten().tolist(),
                    'y_true': self._y_raw[idx_snap].flatten().tolist()
                }
            except Exception as e_snap:
                if logger: logger(f"[AVISO] No se pudo generar snapshot: {e_snap}", "info")
                diag_snapshot = None

            metrics = {
                'confusion_matrix': cm.tolist(),
                'classification_report': rep,
                'diagnostic_snapshot': diag_snapshot,
                'auto_rating': auto_rating, # Nova Nota IA
                'generated_at': datetime.now().isoformat()
            }
            with open(os.path.join(tmpdir, 'metrics.json'), 'w') as f:
                json.dump(metrics, f, indent=2)
            fs.put(os.path.join(tmpdir, 'metrics.json'), f"{CONFIG['bucket']}/{base_path}/metrics.json")
            
            # --- 2.7 TensorBoard Projector Files (Auto-Snapshot) ---
            try:
                # Gerar arquivos do Projector usando a última amostra de treino (X_raw)
                self.save_projector_files(training_id, shortname, self._X_raw, self._y_raw, logger=logger)
            except Exception as e_proj:
                if logger: logger(f"[AVISO] Nota: No se pudo gerar archivos del Projector: {e_proj}", "info")

            # --- 2.8 Iteration History (Snapshots) ---
            if hasattr(self, 'snapshot_dir') and self.snapshot_dir and os.path.exists(self.snapshot_dir):
                if logger: logger("Sincronizando historial de iteraciones com GCS...", "info")
                # Sincroniza PNGs (legado/preview) e o novo snapshots_data.npz
                all_files = [f for f in os.listdir(self.snapshot_dir) if f.endswith('.png') or f == 'snapshots_data.npz']
                for sf in all_files:
                    src_sf = os.path.join(self.snapshot_dir, sf)
                    dest_sf = f"{CONFIG['bucket']}/{base_path}/history/{sf}"
                    fs.put(src_sf, dest_sf)

            # 3. Extracted Pixels
            if logger: logger("Guardar una matriz de píxeles en GCS...", "info")
            np.save(os.path.join(tmpdir, 'X_data.npy'), self._X_raw)
            np.save(os.path.join(tmpdir, 'y_data.npy'), self._y_raw)
            
            for fname in ['X_data.npy', 'y_data.npy']:
                src  = os.path.join(tmpdir, fname)
                dest = f"{CONFIG['bucket']}/{base_path}/extracted_pixels/{fname}"
                fs.put(src, dest)
                
        # 4. Copy samples
        if logger: logger("Copiar archivos CSV de las muestras para su almacenamiento...", "info")
        collections = getattr(self, '_sample_collections', [])
        for coll in collections:
            campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'monitor_01')
            src = gcs_path(f"{CONFIG['gcs_library_samples']}/{campaign}/{coll}.csv")
            dest = gcs_path(f"{base_path}/samples/{coll}.csv")
            subprocess.run(['gsutil', 'cp', src, dest], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return hp

    @staticmethod
    def update_model_metadata(training_id, shortname, updates):
        """Atualiza campos específicos do metadata.json no GCS."""
        import json, subprocess, tempfile
        from M0_auth_config import gcs_path
        base_path = model_path(training_id, shortname)
        fs = _get_fs()
        
        try:
            # 1. Download atual
            path = f"{base_path}/metadata.json"
            with fs.open(path, 'r') as f:
                hp = json.load(f)
            
            # 2. Aplicar updates
            hp.update(updates)
            
            # 3. Upload novo
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_file = os.path.join(tmpdir, 'metadata.json')
                with open(tmp_file, 'w') as f:
                    json.dump(hp, f, indent=2)
                fs.put(tmp_file, f"{CONFIG['bucket']}/{path}")
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar metadados: {e}")
            return False


# ─── INTERFAZ PREMIUM ─────────────────────────────────────────────────────────

# --- VIEW_ANALYTICS UNIFICADA ---
        
def render_diagnostic_dashboard(history, embeds, preds, y_true, coords_override=None, save_path=None, viz_config=None):
    """
    Motor gráfico unificado para o grid 2x3 (Treino e Histórico).
    viz_config: dict com flags de visibilidade.
    """
    if viz_config is None:
        viz_config = {k: True for k in ['cm', 'history', 'prob', 'pr', 'pca2d', 'pca3d', 'pca3d_static', 'tsne3d_static']}
    from sklearn.metrics import confusion_matrix, precision_recall_curve, average_precision_score
    from sklearn.decomposition import PCA
    import matplotlib.pyplot as plt

    try:
        y_true_f = y_true.flatten() if len(y_true) > 0 else np.array([])
        preds_f = preds.flatten() if len(preds) > 0 else np.array([])
        if len(y_true_f) > 0:
            cm = confusion_matrix(y_true_f, (preds_f > 0.5).astype(int))
            cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        else:
            cm = np.zeros((2,2)); cm_norm = np.zeros((2,2))
    except Exception:
        cm = np.zeros((2,2)); cm_norm = np.zeros((2,2))

    # Determina quais subplots mostrar
    active_plots = []
    for k in ['cm', 'history', 'pca2d', 'prob', 'pr']:
        if viz_config.get(k): active_plots.append(k)
    
    # Expandir para 4 ângulos estáticos se solicitado
    for k in ['pca3d_static', 'tsne3d_static']:
        if viz_config.get(k):
            for i in range(4): active_plots.append(f"{k}_{i}")
    
    if not active_plots: return

    n = len(active_plots)
    
    # --- MATRIZ AUTO-AJUSTÁVEL (Lógica Progressiva) ---
    if n == 1:
        rows, cols = 1, 1
    else:
        for r in range(1, 10):
            # 2 gráficos = 1x2, 5-6 gráficos = 2x3, etc.
            if r * (r + 1) >= n:
                rows, cols = r, r + 1
                break
            # 3-4 gráficos = 2x2, 7-9 gráficos = 3x3, etc.
            if (r + 1) * (r + 1) >= n:
                rows, cols = r + 1, r + 1
                break
    
    fig = plt.figure(figsize=(18, 4.5 * rows))
    
    for idx, ptype in enumerate(active_plots):
        if ptype == 'cm':
            ax = fig.add_subplot(rows, cols, idx + 1)
            ax.matshow(cm_norm, cmap='Blues', alpha=0.8, vmin=0, vmax=1)
            for (i, j), z in np.ndenumerate(cm):
                ax.text(j, i, f"{z:,}\n({cm_norm[i,j]:.1%})", ha='center', va='center', weight='bold', color='black' if cm_norm[i,j] < 0.5 else 'white')
            ax.set_title('Matriz de Confusión (%)', pad=15, weight='bold')
            ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
            ax.set_xticklabels(['No-fuego', 'Fuego']); ax.set_yticklabels(['No-fuego', 'Fuego'])

        elif ptype == 'history':
            if history and 'steps' in history and len(history['steps']) > 0:
                ax = fig.add_subplot(rows, cols, idx + 1)
                ax.plot(history['steps'], history['acc'], color='#28a745', label='Acc', linewidth=2)
                if 'val_acc' in history: ax.plot(history['steps'], history['val_acc'], color='#28a745', label='Val', linestyle='--', alpha=0.6)
                ax.set_ylabel('Acurácia', color='#28a745', weight='bold')
                axb = ax.twinx()
                axb.plot(history['steps'], history['loss'], color='#dc3545', label='Loss', linewidth=1.5, alpha=0.7)
                axb.set_ylabel('Custo (Loss)', color='#dc3545', weight='bold')
                ax.set_title('Evolución Histórica', weight='bold')
                ax.grid(True, linestyle='--', alpha=0.3)

        elif ptype == 'pca2d':
            coords2 = None
            if coords_override is not None: coords2 = coords_override[:, :2]
            elif embeds is not None:
                try: pca = PCA(n_components=2); coords2 = pca.fit_transform(embeds)
                except Exception: pass
            if coords2 is not None:
                ax = fig.add_subplot(rows, cols, idx + 1)
                ax.scatter(coords2[:, 0], coords2[:, 1], c=preds_f, cmap='RdYlBu_r', s=25, alpha=0.7, edgecolors='white', linewidth=0.3, vmin=0, vmax=1)
                ax.set_title('Proyección Latente 2D', weight='bold', fontsize=10)
                ax.set_xticks([]); ax.set_yticks([])

        elif ptype == 'prob':
            ax = fig.add_subplot(rows, cols, idx + 1)
            if len(preds_f) > 0 and len(y_true_f) > 0:
                ax.hist(preds_f[y_true_f==0], bins=30, alpha=0.5, color='#007bff', label='No-Fuego', density=True)
                ax.hist(preds_f[y_true_f==1], bins=30, alpha=0.5, color='#ff4d4d', label='Fuego', density=True)
            ax.set_title('Distribución de Probabilidades', weight='bold', fontsize=10)
            ax.set_xlabel('Confianza'); ax.legend(fontsize=8); ax.grid(True, alpha=0.2)

        elif ptype == 'pr':
            try:
                precision, recall, _ = precision_recall_curve(y_true_f, preds_f)
                ap_score = average_precision_score(y_true_f, preds_f)
                ax = fig.add_subplot(rows, cols, idx + 1)
                ax.plot(recall, precision, color='#17a2b8', linewidth=2, label=f'AP={ap_score:.3f}')
                ax.fill_between(recall, precision, alpha=0.2, color='#17a2b8')
                ax.set_title('Curva Precision-Recall', weight='bold', fontsize=10)
                ax.set_xlabel('Recall'); ax.legend(loc='lower left', fontsize=8); ax.grid(True, alpha=0.3)
            except Exception: pass
        elif '3d_static' in ptype:
            from mpl_toolkits.mplot3d import Axes3D
            is_pca = 'pca' in ptype
            angle_idx = int(ptype.split('_')[-1])
            angles = [(20, 45), (20, 135), (20, 225), (20, 315)]
            elev, azim = angles[angle_idx]
            
            coords3 = None
            if coords_override is not None and coords_override.shape[1] >= 3: 
                coords3 = coords_override[:, :3]
            elif is_pca and embeds is not None:
                try: pca = PCA(n_components=3); coords3 = pca.fit_transform(embeds)
                except Exception: pass
            if coords3 is not None:
                ax = fig.add_subplot(rows, cols, idx + 1, projection='3d')
                ax.scatter(coords3[:, 0], coords3[:, 1], coords3[:, 2], c=preds_f, cmap='RdYlBu_r', s=10, alpha=0.6)
                ax.view_init(elev=elev, azim=azim)
                t = "PCA 3D" if is_pca else "t-SNE 3D"
                ax.set_title(f"{t} (Ang {azim}°)", fontsize=9, weight='bold')
                ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])

    plt.tight_layout()
    if not save_path:
        display(fig)
    plt.close(fig)

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=100, bbox_inches='tight')

def render_model_card_html(hp, metrics, only_header=False):
    """Gera o HTML do card de metadados sem emojis."""
    style = """
    <style>
        .dash-card-header { background: #2c3e50; color: white; padding: 10px 15px; font-size: 14px; font-weight: bold; border-radius: 8px 8px 0 0; border: 1px solid #2c3e50; }
        .dash-card-body { border: 1px solid #dee2e6; border-top: none; background: white; padding: 15px; font-family: sans-serif; }
        .meta-text { margin: 3px 0; font-size: 12px; color: #444; }
        .meta-label { font-weight: bold; color: #222; width: 110px; display: inline-block; }
    </style>
    """
    if only_header:
        return f"{style}<div class='dash-card-header'>Ficha del modelo: {hp.get('training_id')} / {hp.get('shortname')}</div>"
    
    date_str = hp.get('training_date', 'Entrenando...')
    if date_str and 'T' in date_str: date_str = date_str[:16].replace('T', ' ')
    
    html_content = f"""
    {style}
    <div class="dash-card-body">
        <div style="display: flex; flex-wrap: wrap; gap: 15px;">
            <div style="flex: 2; min-width: 300px;">
                <p class="meta-text"><span class="meta-label">Estado/Fecha:</span> {date_str}</p>
                <p class="meta-text"><span class="meta-label">Muestras:</span> {', '.join(hp.get('sample_collections', []))}</p>
                <p class="meta-text"><span class="meta-label">Bandas:</span> {', '.join([f"{b} ({hp.get('bands_config', {}).get(b, {}).get('sensor', 'N/A').upper()})" for b in hp.get('bands_input', [])])}</p>
                <p class="meta-text"><span class="meta-label">Capas:</span> {hp.get('layers')} | <b>LR:</b> {hp.get('lr')}</p>
                <p class="meta-text"><span class="meta-label">Píxeles:</span> {hp.get('sample_count', {}).get('burned', 0)} (F) | {hp.get('sample_count', {}).get('not_burned', 0)} (NF)</p>
                <div style="margin-top:8px; padding:8px; background:#fff3cd; border-radius:4px; border:1px solid #ffeeba;">
                    <p class="meta-text" style="color:#856404; font-weight:bold; margin-bottom:3px;">Comentario:</p>
                    <p class="meta-text" style="color:#856404; font-style:italic;">{hp.get('comment', 'Sin comentarios.')}</p>
                </div>
            </div>
        </div>
    </div>
    """
    return html_content

def view_analytics(model_info, out_widget=None, clear_before=True, viz_config=None, epoch_index=None, ui=None):
    """
    Visualiza as métricas e o card de um modelo salvo no GCS.
    viz_config: dict opcional com flags de visibilidade.
    epoch_index: índice da época para renderizar dados passados (Time Machine).
    """
    if viz_config is None:
        viz_config = {k: True for k in ['title', 'scores', 'cm', 'history', 'prob', 'pr', 'pca2d', 'pca3d', 'tsne3d']}
    
    fs = _get_fs()
    from M0_auth_config import CONFIG
    try:
        import urllib.parse
        m_path = model_info['path']
        m_path = urllib.parse.unquote(m_path)
        clean_path = m_path.replace('gs://', '').replace(f"{CONFIG['bucket']}/", '').lstrip('/')
        if 'b/' in clean_path and '/o/' in clean_path: clean_path = clean_path.split('/o/')[-1]
        
        # 1. Carrega Metadados e Métricas Base
        with fs.open(f"{CONFIG['bucket']}/{clean_path}/metadata.json", 'r') as f: hp = json.load(f)
            try:
                with fs.open(f"{CONFIG['bucket']}/{clean_path}/metrics.json", 'r') as f: metrics = json.load(f)
            except Exception:
                metrics = {}
        # 2. Carrega Dados de Snapshots para o Time Machine se solicitado
        snap_data = None
        if epoch_index is not None:
            try:
                with fs.open(f"{CONFIG['bucket']}/{clean_path}/history/snapshots_data.npz", 'rb') as f:
                    snap_data = dict(np.load(f, allow_pickle=True))
            except Exception:
                pass # Se não existir, usa os dados finais das métricas

        def _render_content():
            # ui é recebido como parâmetro de view_analytics (evita import __main__)
            # --- SISTEMA DE RATINGS (KPIs COMPACTOS) ---
            h_rating = hp.get('rating', 0)
            a_rating = metrics.get('auto_rating', 0)
            rep = metrics.get('classification_report', {})
            
            # --- OVERRIDE DE DADOS SE EPOCH_INDEX ATIVO ---
            preds_final = np.array(metrics.get('diagnostic_snapshot', {}).get('preds', []))
            y_true_final = np.array(metrics.get('diagnostic_snapshot', {}).get('y_true', []))
            pca_coords_final = np.array(metrics.get('diagnostic_snapshot', {}).get('pca_coords', []))
            tsne_coords_final = np.array(metrics.get('diagnostic_snapshot', {}).get('tsne_coords', []))
            
            if snap_data and f'preds_{epoch_index}' in snap_data:
                preds_final = snap_data[f'preds_{epoch_index}']
                y_true_final = snap_data['y_true']
                embeds_step = snap_data[f'embeds_{epoch_index}']
                # Re-calcula PCA simples para o Time Machine (CPU-bound mas rápido para poucas amostras)
                from sklearn.decomposition import PCA
                pca_tmp = PCA(n_components=3)
                pca_coords_final = pca_tmp.fit_transform(embeds_step)
                tsne_coords_final = None # t-SNE é muito lento para recalcular no slider
            
            # --- KPI BUILDER ---
            def make_kpi_card(title, value, color, icon=None):
                icon_html = f"<i class='fa fa-{icon}' style='margin-right:5px; opacity:0.5;'></i>" if icon else ""
                return widgets.HTML(f"""
                <div class="kpi-box" style="border-left: 5px solid {color}; padding: 10px; background: white; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); flex: 1; min-width: 120px;">
                    <div style="font-size: 10px; color: #7f8c8d; text-transform: uppercase; font-weight: bold; margin-bottom: 2px;">{title}</div>
                    <div style="font-size: 18px; font-weight: bold; color: #2c3e50;">{icon_html}{value}</div>
                </div>
                """)

            kpi_acc = make_kpi_card("Accuracy", f"{rep.get('accuracy', 0):.1%}", "#2c3e50", icon="crosshairs")
            kpi_prec = make_kpi_card("Precision", f"{rep.get('1', {}).get('precision', 0):.1%}", "#8e44ad", icon="bullseye")
            kpi_rec = make_kpi_card("Recall", f"{rep.get('1', {}).get('recall', 0):.1%}", "#e67e22", icon="search-plus")
            kpi_f1 = make_kpi_card("F1-Score", f"{rep.get('1', {}).get('f1-score', 0):.1%}", "#16a085", icon="balance-scale")
            kpi_auto = make_kpi_card("Nota IA", f"{a_rating}/5", "#34495e", icon="flash")

            # Nota Humana Interativa no KPI
            user_stars_container = widgets.HBox([], layout=widgets.Layout(margin='0', align_items='center'))
            def _show_stars():
                btns = []
                for i in range(1, 6):
                    btn = widgets.Button(description="" if i <= h_rating else "", 
                                       layout=widgets.Layout(width='22px', height='22px', margin='0', padding='0'),
                                       style={'button_color': '#f1c40f' if i <= h_rating else '#fff'})
                    def _hnd_click(b, val=i):
                        btn_ok = widgets.Button(description="OK", layout=widgets.Layout(width='35px', height='22px'), button_style='success')
                        btn_no = widgets.Button(description="X", layout=widgets.Layout(width='25px', height='22px'), button_style='danger')
                        def _do_ok(_):
                            user_stars_container.children = [widgets.HTML("<i class='fa fa-spinner fa-spin'></i>")]
                            if ModelTrainer.update_model_metadata(hp['training_id'], hp['shortname'], {'rating': val}):
                                if ui: ui._refresh_canvas_hub()
                                hp['rating'] = val; _show_stars()
                            else: _show_stars()
                        btn_ok.on_click(_do_ok); btn_no.on_click(lambda _: _show_stars())
                        user_stars_container.children = [btn_no, btn_ok]
                    btn.on_click(_hnd_click); btns.append(btn)
                user_stars_container.children = btns

            _show_stars()
            kpi_human_box = widgets.VBox([
                widgets.HTML("<div style='font-size: 10px; color: #7f8c8d; text-transform: uppercase; font-weight: bold; margin-bottom: 2px;'>Nota Humana</div>"),
                user_stars_container
            ], layout=widgets.Layout(background='white', padding='10px', border_left='5px solid #f1c40f', border_radius='4px', box_shadow='0 2px 4px rgba(0,0,0,0.08)', flex='1.5'))

            unified_grid = widgets.HBox(
                [kpi_acc, kpi_prec, kpi_rec, kpi_f1, kpi_auto, kpi_human_box],
                layout=widgets.Layout(gap='8px', margin='10px 0', width='100%', flex_wrap='wrap')
            )

            # --- CARD HEADER & BODY ---
            display(HTML(render_model_card_html(hp, metrics, only_header=True)))
            if viz_config.get('title'):
                display(HTML(render_model_card_html(hp, metrics)))
            
            if viz_config.get('scores'):
                display(unified_grid)

            # --- CICLO DE VIDA (GESTÃO OPCIONAL) ---
            if viz_config.get('management'):
                display(HTML("<h4 style='color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px; margin-top:20px;'> Gestión del Ciclo de Vida</h4>"))
                def _set_intent(mode):
                    def __h(_):
                        if ui:
                            ui.retrain_intent = {'mode': mode, 'hp': hp}
                            ui._load_config_into_widgets(hp)
                            ui.tab.selected_index = 1 # Novo Treino
                    return __h

                btn_retr = widgets.Button(description="Retreinar", icon="refresh", layout=widgets.Layout(width='120px'), button_style='info')
                btn_reex = widgets.Button(description="Re-extraer", icon="database", layout=widgets.Layout(width='120px'), button_style='info')
                btn_borr = widgets.Button(description="Limpiar&Ret", icon="trash", layout=widgets.Layout(width='130px'), button_style='danger')
                btn_retr.on_click(_set_intent('retrain')); btn_reex.on_click(_set_intent('re-extract')); btn_borr.on_click(_set_intent('borrar'))

                # Botão de Deletar com Countdown
                del_out = widgets.Output()
                def _show_del_btn():
                    del_out.clear_output()
                    btn_del = widgets.Button(description="Deletar Modelo", icon="trash", layout=widgets.Layout(width='140px'), button_style='danger')
                    def _on_del_click(_):
                        import threading
                        btn_conf = widgets.Button(description="Confirmar!", button_style='warning', layout=widgets.Layout(width='100px'))
                        btn_canc = widgets.Button(description="X", button_style='info', layout=widgets.Layout(width='30px'))
                        msg = widgets.HTML("<span style='color:red; font-size:10px; margin-left:5px;'>5s</span>")
                        del_out.clear_output()
                        with del_out: display(widgets.HBox([btn_conf, btn_canc, msg]))
                        stop = [False]
                        def _do_conf(_):
                            stop[0] = True
                            del_out.clear_output()
                            with del_out: display(widgets.HTML("<i>Borrando...</i>"))
                            ModelTrainer.delete_model(hp['training_id'], hp['shortname'])
                            if ui: 
                                ui.selected_models.pop(hp['training_id'], None)
                                ui._update_canvas()
                        btn_conf.on_click(_do_conf); btn_canc.on_click(lambda _: _show_del_btn())
                        def _timer():
                            for i in range(5, 0, -1):
                                if stop[0]: return
                                msg.value = f"<span style='color:red; font-size:10px; margin-left:5px;'>{i}s</span>"; time.sleep(1)
                            if not stop[0]: _do_conf(None)
                        threading.Thread(target=_timer, daemon=True).start()
                    btn_del.on_click(_on_del_click)
                    with del_out: display(btn_del)
                _show_del_btn()

                display(widgets.HBox([btn_retr, btn_reex, btn_borr, widgets.HTML("<div style='width:20px'></div>"), del_out], 
                                    layout=widgets.Layout(margin='5px 0 15px 0', align_items='center')))

            # --- GRUPOS DE GRÁFICOS ---
            # 1. MÉTRICAS CLÁSSICAS (Incluindo Estáticas 3D)
            classic_keys = ['cm', 'history', 'prob', 'pr', 'pca3d_static', 'tsne3d_static']
            if any(viz_config.get(k) for k in classic_keys):
                display(HTML("<h4 style='color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px;'> Métricas Clásicas y Proyecciones Estáticas</h4>"))
                
                # Trunca o histórico caso o slider de tempo esteja ativado
                history_data = hp.get('history', {})
                if history_data and epoch_index is not None and 'steps' in history_data:
                    try:
                        limit = epoch_index + 1
                        history_data = {k: v[:limit] for k, v in history_data.items()}
                    except Exception: pass
                render_diagnostic_dashboard(history_data, None, preds_final, y_true_final, 
                                          coords_override=tsne_coords_final if viz_config.get('tsne3d_static') else (pca_coords_final if viz_config.get('pca3d_static') or viz_config.get('pca2d') else None), 
                                          viz_config=viz_config)

            # 2. ESPAÇO LATENTE (INTERATIVO SIDE-BY-SIDE)
            latent_keys = ['pca3d', 'tsne3d']
            if any(viz_config.get(k) for k in latent_keys):
                display(HTML("<h4 style='color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px; margin-top:20px;'> Espacio Latente Interactivo</h4>"))
                import plotly.graph_objects as go
                fire_colorscale = [[0, '#2c3e50'], [0.5, '#bdc3c7'], [1, '#e67e22']]
                
                out_pca = widgets.Output(layout=widgets.Layout(width='50%'))
                out_tsne = widgets.Output(layout=widgets.Layout(width='50%'))
                display(widgets.HBox([out_pca, out_tsne], layout=widgets.Layout(width='100%')))

                if viz_config.get('pca3d') and pca_coords_final is not None and len(pca_coords_final) > 0:
                    fig_pca = go.Figure(data=[go.Scatter3d(
                        x=pca_coords_final[:,0], y=pca_coords_final[:,1], z=pca_coords_final[:,2], mode='markers',
                        marker=dict(size=3, color=preds_final, colorscale=fire_colorscale, opacity=0.7),
                        text=[f"Real: {l}<br>Pred: {p:.2%}" for l, p in zip(y_true_final, preds_final)]
                    )])
                    fig_pca.update_layout(title="PCA 3D Interactive", margin=dict(l=0, r=0, b=0, t=30), height=400)
                    with out_pca: display(HTML(fig_pca.to_html(include_plotlyjs=True, full_html=False)))

                if viz_config.get('tsne3d') and tsne_coords_final is not None and len(tsne_coords_final) > 0:
                    fig_tsne = go.Figure(data=[go.Scatter3d(
                        x=tsne_coords_final[:,0], y=tsne_coords_final[:,1], z=tsne_coords_final[:,2], mode='markers',
                        marker=dict(size=3, color=preds_final, colorscale=fire_colorscale, opacity=0.7),
                        text=[f"Real: {l}<br>Pred: {p:.2%}" for l, p in zip(y_true_final, preds_final)]
                    )])
                    fig_tsne.update_layout(title="t-SNE 3D Interactive", margin=dict(l=0, r=0, b=0, t=30), height=400)
                    with out_tsne: display(HTML(fig_tsne.to_html(include_plotlyjs=True, full_html=False)))

            # --- TENSORBOARD PROJECTOR ---
            # (Opcional: Adicionar links se necessário)

        if out_widget:
            if clear_before: out_widget.clear_output(wait=True)
            with out_widget: _render_content()
        else:
            _render_content()
    except Exception as e:
        msg = f"[ERRO] Erro ao carregar analíticos: {e}"
        if out_widget:
            with out_widget: print(msg)
        else: print(msg)




class ModelTrainerUI(PipelineStepUI):
    def __init__(self):
        super().__init__(
            title="M4 - Entrenador del Modelo (DNN)", 
            description="Centro de Operaciones de Entrenamiento y Auditoría de Modelos."
        )
        self.trainer_instance = None
        self.chk_dict = {}
        self.search_query_samples = ""
        self.search_query_models = "" 
        self.sort_column = "acc"      
        self.sort_ascending = False   
        self.sampling_campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', 'monitor_01')
        
        # --- INTENÇÃO DE RETREINAMENTO ---
        self.retrain_intent = {'mode': None, 'hp': None} # Guarda a intenção atual de re-treinamento
        self.cb_retrain = widgets.Checkbox(value=False, layout={'display': 'none'})
        self.cb_reextract = widgets.Checkbox(value=False, layout={'display': 'none'})
        self.cb_borrar_retrain = widgets.Checkbox(value=False, layout={'display': 'none'})
        self.cb_retrain.observe(self._on_intent_cb_change, names='value')
        self.cb_reextract.observe(self._on_intent_cb_change, names='value')
        self.cb_borrar_retrain.observe(self._on_intent_cb_change, names='value')
        
        # --- ESTADO DEL CANVAS ---
        self.selected_models = {} # ID -> info (Active in Canvas)
        self.canvas_history = {} # ID -> info (Ever viewed in session)
        self.canvas_search_query = ""
        self.canvas_sort_col = "acc"
        self.canvas_sort_asc = False
        self.canvas_output = widgets.Output(layout=widgets.Layout(background_color='white', padding='20px'))
        self.analytics_dashboard_output = widgets.Output() # Para carregar card após treino
        self._live_plots_out = widgets.Output()            # Para evitar "piscar" no treino
        self.canvas_slider_val = 0
        self.band_chk_map = {} # (sensor, mosaic, band) -> checkbox
        
        # --- CONFIGURACIÓN DE VISIBILIDAD ---
        self.viz_config = {
            'title': True, 'scores': True, 'cm': True, 'history': True, 
            'prob': True, 'pr': True, 
            'pca2d': False, 'pca3d': False, 'tsne3d': False,
            'pca3d_static': False, 'tsne3d_static': False,
            'management': False
        }
        
        # --- WIDGETS DO CANVAS (CONTROLES GLOBAIS) ---
        self.w_global_slider = widgets.IntSlider(
            value=0, min=0, max=10, description='Época:',
            layout=widgets.Layout(width='98%', margin='5px 0 15px 0'),
            style={'description_width': 'initial'}
        )
        self.w_global_slider.observe(self._on_global_slider_change, names='value')
        
        self.w_apply_btn = widgets.Button(
            description="Aplicar Visibilidad", icon="play",
            button_style='success', layout=widgets.Layout(width='180px')
        )
        self.w_apply_btn.on_click(lambda _: self._update_canvas())
        
        # Sidebar containers
        self.canvas_available_box = widgets.VBox([], layout=widgets.Layout(flex='1', border='1px solid #ddd', overflow_y='auto'))
        self.canvas_selected_box = widgets.VBox([], layout=widgets.Layout(flex='1', border='1px solid #ddd', overflow_y='auto'))
        
        self.main_area.children = [widgets.HTML("<i>Cargando interfaz...</i>")]

    def _load_config_into_widgets(self, hp):
        """Carrega os parâmetros de um modelo de volta para os widgets de configuração."""
        self.w_training_id.value = hp.get('training_id', '')
        self.w_shortname.value = hp.get('shortname', '')
        self.w_layers.value = ",".join(map(str, hp.get('layers', [64, 32])))
        self.w_lr.value = str(hp.get('lr', 0.001))
        self.w_iters.value = str(hp.get('n_iters', 5000))
        self.w_batch.value = str(hp.get('batch_size', 1000))
        self.w_comment.value = hp.get('comment', '')
        
        # Muestras
        sc = hp.get('sample_collections', [])
        for name, chk in self.chk_dict.items():
            chk.value = name in sc
            
        # Bandas
        b_cfg = hp.get('bands_config', {})
        for (s, m, p, b), chk in self.band_chk_map.items():
            chk.value = (b in b_cfg and b_cfg[b]['sensor'] == s and b_cfg[b]['mosaic'] == m)

        # Sync Intent Checkboxes
        mode = self.retrain_intent.get('mode')
        # Temporarily unobserve to avoid feedback loops
        for cb in [self.cb_retrain, self.cb_reextract, self.cb_borrar_retrain]:
            cb.unobserve(self._on_intent_cb_change, names='value')
            cb.value = False
            
        if mode == 'retrain': self.cb_retrain.value = True
        elif mode == 're-extract': self.cb_reextract.value = True
        elif mode == 'borrar': self.cb_borrar_retrain.value = True
        
        for cb in [self.cb_retrain, self.cb_reextract, self.cb_borrar_retrain]:
            cb.observe(self._on_intent_cb_change, names='value')

    def display(self):
        # 1. NOVO TREINO (Fluxo Completo)
        hp_sec = self._build_hp_section()
        dest_sec = self._build_dest_section()
        
        # Build areas sem fazer chamadas ao GCS (usando cache ou vazio)
        self.samples_area = self._build_matrix()
        self.extraction_area = self._build_extraction_matrix()
        
        self.new_training_tab = widgets.VBox([
            widgets.HTML("<h2 style='color:#2c3e50;'> 1. Selección de Muestras</h2>"),
            self.samples_area,
            widgets.HTML("<br><h2 style='color:#2c3e50;'> 2. Matriz de Extracción (Multisensor GCS)</h2>"),
            self.extraction_area,
            widgets.HTML("<br><h2 style='color:#2c3e50;'> 3. Configuración do Modelo</h2>"),
            hp_sec,
            widgets.HTML("<br><h2 style='color:#2c3e50;'> 4. Destino GCS</h2>"),
            dest_sec,
        ], layout=widgets.Layout(padding='20px', background_color='white'))
        
        # 2. CANVAS (Visualização + Ranking Sidebar)
        # --- SIDEBAR (ESQUERDA) ---
        self.w_canvas_search = widgets.Text(placeholder='Buscar en repositorio...', layout=widgets.Layout(width='100%'))
        self.w_canvas_search.observe(lambda c: self._on_canvas_search_change(c['new']), names='value')
        
        self.w_canvas_sort = widgets.Dropdown(
            options=[('Acurácia', 'acc'), ('F1-Fire', 'f1'), ('ID', 'id')],
            value=self.canvas_sort_col,
            description='Ordenar:',
            layout=widgets.Layout(width='100%'),
            style={'description_width': '60px'}
        )
        def _on_sort_change(change):
            self.canvas_sort_col = change['new']
            self._refresh_canvas_hub()
        self.w_canvas_sort.observe(_on_sort_change, names='value')

        btn_sync = widgets.Button(description="Sincronizar GCS", icon="refresh", layout=widgets.Layout(width='100%'), button_style='primary')
        btn_sync.on_click(lambda _: self._sync_repository(show_loader=True, force_refresh=True))

        btn_all_canvas = widgets.Button(description="Todos", icon="check-square", layout=widgets.Layout(width='48%'), button_style='info')
        btn_none_canvas = widgets.Button(description="Limpiar", icon="square-o", layout=widgets.Layout(width='48%'), button_style='warning')
        btn_all_canvas.on_click(lambda _: self._on_canvas_batch_action('all'))
        btn_none_canvas.on_click(lambda _: self._on_canvas_batch_action('none'))
        
        sidebar_vbox = widgets.VBox([
            widgets.HTML("<b style='font-size:13px; color:#2c3e50;'>Ranking / Repositorio</b>"),
            self.w_canvas_search,
            self.w_canvas_sort,
            btn_sync,
            self.canvas_available_box,
            widgets.HBox([btn_all_canvas, btn_none_canvas], layout=widgets.Layout(justify_content='space-between', margin='5px 0')),
            widgets.HTML("<b style='font-size:13px; color:#2c3e50; margin-top:10px;'>Seleccionados em Canvas</b>"),
            self.canvas_selected_box
        ], layout=widgets.Layout(width='320px', padding='10px', background_color='#fcfcfc', border_right='2px solid #eee'))

        main_canvas_vbox = widgets.VBox([
            widgets.HTML("<h3 style='color:#2c3e50; margin:0 0 10px 0;'> Centro de Treinamentos y Auditoría</h3>"),
            self._build_viz_toolbar(), 
            self.w_global_slider,      
            self.canvas_output         
        ], layout=widgets.Layout(flex='1', padding='15px'))

        self.canvas_area = widgets.HBox([sidebar_vbox, main_canvas_vbox], 
                                       layout=widgets.Layout(background_color='white', border='1px solid #ddd', min_height='800px'))

        # 3. ASSEMBLY TABS
        self.tab = widgets.Tab()
        self.tab.children = [
            self._build_guide_tab(),
            self.new_training_tab,
            self.canvas_area,
        ]
        self.tab.set_title(0, ' Guia de Uso')
        self.tab.set_title(1, ' Novo Treinamento')
        self.tab.set_title(2, ' Treinamentos')
        
        self.tab.selected_index = 0
        self.main_area.children = [self.tab]
        super().display()
        
        # REMOVIDO: Sincronização automática no display() para evitar travamento.
        # Agora o usuário clica em sincronizar ou os dados vêm do cache.

    def _build_guide_tab(self):
        """Constrói uma interface de documentação interativa para o usuário."""
        html = """
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; background: #fdfdfd; color: #2c3e50; line-height: 1.6;">
            <h1 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">Guia de Uso de Operación: M4 Model Trainer</h1>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-top: 20px;">
                <!-- Seção 1: Fluxo de Trabalho -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #3498db; margin-top:0;">Estructura de la Plataforma</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>Guia de Uso:</b> Esta pantalla de orientación y documentación.</li>
                        <li><b>Novo Treino:</b> Configuración de nuevos experimentos, selección de muestras y bandas.</li>
                        <li><b>Trenamientos:</b> Ranking histórico con métricas detalladas y gestión de modelos.</li>
                        <li><b>Canvas:</b> Mesa de auditoría paralela para comparar múltiples modelos en profundidad.</li>
                    </ul>
                </div>

                <!-- Seção 2: Conceptos Técnicos -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #9b59b6; margin-top:0;">Conceptos Técnicos</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>TensorFlow:</b> Motor de IA de Google para cálculos matemáticos masivos.</li>
                        <li><b>DNN (Deep Neural Network):</b> Red profunda que imita el aprendizaje humano.</li>
                        <li><b>Neuronas:</b> Unidades que procesan señales y activan patrones de aprendizaje.</li>
                    </ul>
                </div>

                <!-- Seção 3: Hiperparámetros -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #e67e22; margin-top:0;">Hiperparámetros (DNN)</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>Layers:</b> Arquitectura de la red. Más capas captan detalles más finos.</li>
                        <li><b>Learning Rate (LR):</b> Controla qué tan rápido se ajusta el modelo.</li>
                        <li><b>Epochs:</b> Ciclos de entrenamiento completos sobre el set de muestras.</li>
                        <li><b>Batch Size:</b> Bloques de datos procesados antes de cada actualización.</li>
                    </ul>
                </div>

                <!-- Seção 4: Métricas de Calidad -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #27ae60; margin-top:0;">Diccionario de Calidad</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>Accuracy:</b> Porcentaje total de aciertos globales.</li>
                        <li><b>Precision:</b> Fidelidad: ¿Cuánto del fuego marcado es real? (Evita falsos).</li>
                        <li><b>Recall:</b> Cobertura: ¿Cuánto del fuego real se encontró? (Evita omisiones).</li>
                        <li><b>F1-Score:</b> Media armónica. El mejor balance entre Precision y Recall.</li>
                        <li><b>Nota IA:</b> Auditoría automática que castiga severamente las omisiones.</li>
                        <li><b>Nota Humana:</b> Evaluación subjetiva (1-5) sobre el Espacio Latente.</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: #e8f4fd; border-left: 5px solid #3498db; border-radius: 4px; font-size:14px;">
                <b>[Dica] Pro-Tip del Auditor:</b> Use el <b>Canvas</b> para cargar un modelo antiguo (benchmark) y su modelo nuevo. Compare si la separación de clases en t-SNE 3D ha mejorado o si hay nuevas zonas de confusión.
            </div>
        </div>
        """
        return widgets.HTML(html)

    def _on_select_all_samples(self, _):
        """Seleciona apenas as amostras que estão visíveis pelo filtro."""
        visible_keys = [s for s in self.chk_dict.keys() if self.search_query_samples.lower() in s.lower()]
        for k in visible_keys:
            self.chk_dict[k].value = True

    def _on_select_none_samples(self, _):
        """Limpa apenas as amostras que estão visíveis pelo filtro."""
        visible_keys = [s for s in self.chk_dict.keys() if self.search_query_samples.lower() in s.lower()]
        for k in visible_keys:
            self.chk_dict[k].value = False

    def _on_search_samples_change(self, change):
        self.search_query_samples = change['new']
        self._refresh_samples_panes()

    def _on_search_models_change(self, change):
        self.search_query_models = change['new']
        self._refresh_canvas_hub()

    def _on_sort_change(self, change):
        if change['name'] == 'value':
            self.sort_column = change['new']
            self._refresh_canvas_hub()
            
    def _on_sort_order_change(self, change):
        self.sort_ascending = not self.sort_ascending
        self._refresh_canvas_hub()

    def _on_intent_cb_change(self, change):
        """Ensures exclusivity between retraining intent checkboxes."""
        if not change['new']: return
        owner = change['owner']
        for cb in [self.cb_retrain, self.cb_reextract, self.cb_borrar_retrain]:
            if cb != owner:
                cb.unobserve(self._on_intent_cb_change, names='value')
                cb.value = False
                cb.observe(self._on_intent_cb_change, names='value')
        
        # Update retrain_intent mode
        mode = 'retrain' if self.cb_retrain.value else \
               're-extract' if self.cb_reextract.value else \
               'borrar' if self.cb_borrar_retrain.value else None
        self.retrain_intent['mode'] = mode

    def _refresh_matrix_only(self):
        """Atualiza especificamente a seção da matriz de extração."""
        if hasattr(self, 'extraction_matrix_container'):
            new_matrix = self._build_extraction_matrix()
            self.extraction_matrix_container.children = [new_matrix]

    def _build_matrix_content(self):
        """Constrói apenas a lista de linhas filtradas."""
        L = widgets.Layout
        samples_available = list_sample_collections_gcs()
        matrix_rows = []
        
        for s in samples_available:
            if self.search_query_samples and self.search_query_samples.lower() not in s.lower():
                continue
                
            if s not in self.chk_dict:
                self.chk_dict[s] = widgets.Checkbox(value=False, indent=False, layout=L(width='18px', height='18px', margin='0'))
            
            chk = self.chk_dict[s]
            status_cell = PipelineStepUI.make_status_cell(chk, 'OK', 'mfm-ok', width='120px')
            
            row = widgets.HBox([
                widgets.HTML(f'<div style="width:350px;font-family:monospace;">{s}</div>'),
                status_cell
            ], layout=L(align_items='center', margin='2px 0', border_bottom='1px solid #dee2e6'))
            matrix_rows.append(row)
            
        if not matrix_rows:
            return widgets.HTML('<div style="padding:10px; color:#999;"><i>No se han encontrado resultados con este filtro.</i></div>')
            
        return widgets.VBox(matrix_rows)

    def _build_matrix(self):
        L = widgets.Layout
        css = PipelineStepUI.get_status_css()
        
        # BARRA DE BUSCA E SELETOR DE CAMPANHA
        self.txt_search_samples = widgets.Text(
            value=self.search_query_samples,
            placeholder='Buscar muestras...',
            layout=L(width='100%')
        )
        self.txt_search_samples.observe(self._on_search_samples_change, names='value')

        self.w_campaign = widgets.Dropdown(
            options=list_campaigns_gcs(),
            value=self.sampling_campaign,
            layout=L(width='150px'),
            style={'description_width': 'initial'}
        )
        
        def _on_campaign_change(change):
            from M0_auth_config import GLOBAL_OPTS
            new_c = change['new']
            GLOBAL_OPTS['SAMPLING_CAMPAIGN'] = new_c
            self.sampling_campaign = new_c
            # Limpa cache para forçar refresh real das amostras da nova campanha
            cache = _load_m4_cache()
            if 'known_samples' in cache: del cache['known_samples']
            _save_m4_cache(cache)
            # Refresh UI
            self._refresh_samples_panes()
            
        self.w_campaign.observe(_on_campaign_change, names='value')

        btn_all = widgets.Button(description="Todos", icon="check-square", layout=L(width='70px'), button_style='info')
        btn_none = widgets.Button(description="Limpiar", icon="square-o", layout=L(width='75px'), button_style='warning')
        btn_all.on_click(self._on_select_all_samples)
        btn_none.on_click(self._on_select_none_samples)
        
        self.txt_search_samples.layout.flex = '1'
        sample_toolbar = widgets.HBox([
            widgets.HTML("<b style='margin-right:5px;'>Campanha:</b>"), 
            self.w_campaign, 
            widgets.HTML("<div style='width:10px'></div>"),
            self.txt_search_samples, 
            btn_all, btn_none
        ], layout=L(gap='4px', margin='0 0 5px 0', width='100%', align_items='center'))

        self.available_samples_container = widgets.VBox([], layout=L(
            border='1px solid #ddd', height='300px', overflow_y='auto', padding='0'
        ))
        self.selected_samples_container = widgets.VBox([], layout=L(
            border='1px solid #ddd', height='300px', overflow_y='auto', padding='0'
        ))

        left_pane = widgets.VBox([
            widgets.HTML("<b style='font-size:12px; color:#555;'> Muestras Disponibles</b>"),
            sample_toolbar,
            self.available_samples_container
        ], layout=L(flex='1'))

        right_pane = widgets.VBox([
            widgets.HTML("<b style='font-size:12px; color:#555;'>[OK] Muestras Seleccionadas</b>"),
            widgets.HTML("<div style='height:42px;'></div>"), # Alinhador com a toolbar
            self.selected_samples_container
        ], layout=L(flex='1'))

        dual_pane = widgets.HBox([left_pane, right_pane], layout=L(gap='20px', padding='10px'))
        
        self._refresh_samples_panes()
        
        return widgets.VBox([css, dual_pane])

    def _refresh_samples_panes(self):
        L = widgets.Layout
        samples_available = list_sample_collections_gcs()
        
        # Left Pane (Available)
        available_widgets = []
        for s in samples_available:
            if self.search_query_samples and self.search_query_samples.lower() not in s.lower():
                continue
            if s in self.chk_dict and self.chk_dict[s].value:
                continue # Already selected
                
            btn = widgets.Button(description=f"+ {s}", layout=L(width='100%', min_height='28px', margin='1px 0'), style={'button_color': '#f8f9fa'})
            def _add(b, name=s):
                if name not in self.chk_dict: self.chk_dict[name] = widgets.Checkbox(value=False)
                self.chk_dict[name].value = True
                self._refresh_samples_panes()
            btn.on_click(_add)
            available_widgets.append(btn)
        
        self.available_samples_container.children = available_widgets

        # Right Pane (Selected)
        selected_widgets = []
        for s, chk in self.chk_dict.items():
            if chk.value:
                btn = widgets.Button(description=s, layout=L(width='100%', min_height='28px', margin='1px 0'), style={'button_color': '#e3f2fd'})
                def _remove(b, name=s):
                    self.chk_dict[name].value = False
                    self._refresh_samples_panes()
                btn.on_click(_remove)
                selected_widgets.append(btn)
        
        self.selected_samples_container.children = selected_widgets

    def _build_extraction_matrix(self):
        """Constrói a matriz dinâmica priorizando o cache local 'state.json'."""
        L = widgets.Layout
        from M_cache import CacheManager
        
        # --- CABEÇALHO COM BOTÃO DE SYNC ---
        btn_sync = widgets.Button(
            description="Sincronizar Catálogo (GCS)",
            icon="sync",
            button_style='success',
            layout=L(width='220px', height='30px')
        )
        sync_out = widgets.Output()
        
        def _on_sync_click(b):
            btn_sync.description = "Sincronizando..."
            btn_sync.disabled = True
            with sync_out:
                clear_output()
                print("Escaneando GCS... Aguarde.")
                CacheManager.build_cache_from_gcs() # Força scan real no GCS
                self._refresh_matrix_only()         # Atualiza a UI
                print("¡Catálogo Sincronizado!")
            btn_sync.description = "Sincronizar Catálogo (GCS)"
            btn_sync.disabled = False

        btn_sync.on_click(_on_sync_click)
        
        header = widgets.HBox([
            widgets.HTML("<b style='font-size:14px; color:#2c3e50;'>2. Matriz de Extracción (Multisensor GCS)</b>"),
            widgets.HTML("<div style='width:20px;'></div>"),
            btn_sync,
            sync_out
        ], layout=L(align_items='center', margin='10px 0'))

        available_combos = {} # (sensor, mosaic, period) -> set(bands)
        
        try:
            # 1. Tenta carregar o cache. O CacheManager agora tentará local primeiro.
            state = CacheManager.load()
            all_cogs = state.get('cogs_monthly', []) + state.get('cogs_annually', [])
            
            if not all_cogs:
                raise ValueError("Cache vazio")

            def _parse_cog_agnostic(name):
                """Parse agnóstico: identifica banda e sensor pelo padrão do arquivo."""
                # padrão: image_peru_fire_{sensor}_{mosaic}_{band}_{date}
                p = name.lower().split('fire_')[-1].split('_')
                if len(p) < 4: return None
                
                # O sensor é sempre o primeiro
                sensor = p[0]
                # A data costuma ser os últimos 1 ou 2 campos (YYYY ou YYYY_MM)
                date_idx = -1
                if p[-2].isdigit() and len(p[-2]) == 4: date_idx = -2 # YYYY_MM
                elif p[-1].isdigit() and len(p[-1]) == 4: date_idx = -1 # YYYY
                
                if date_idx == -1:
                    band = p[-2]
                    mosaic = "_".join(p[1:-2])
                else:
                    band = p[-3]
                    mosaic = "_".join(p[1:-3])
                
                return {'sensor': sensor, 'mosaic': mosaic, 'band': band}

            # Processar Mensais
            for cog_name in state.get('cogs_monthly', []):
                p = _parse_cog_agnostic(cog_name)
                if p:
                    combo = (p['sensor'], p['mosaic'], 'mensal')
                    if combo not in available_combos: available_combos[combo] = set()
                    available_combos[combo].add(p['band'])

            # Processar Anuais
            for cog_name in state.get('cogs_annually', []):
                p = _parse_cog_agnostic(cog_name)
                if p:
                    combo = (p['sensor'], p['mosaic'], 'anual')
                    if combo not in available_combos: available_combos[combo] = set()
                    available_combos[combo].add(p['band'])
        except Exception:
            # Fallback offline fixo se nem o cache existir
            available_combos = {
                ('sentinel2', 'minnbr'): set(['red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']),
                ('sentinel2', 'minnbr_buffer'): set(['red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']),
                ('landsat', 'minnbr'): set(['red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'])
            }

        if not available_combos:
            return widgets.HTML('<div style="padding:20px; color:#999;"><i>No se han encontrado COGs en el repositorio GCS.</i></div>')

        self.band_chk_map = {} 
        matrix_rows = []
        
        # PRIORIDADE DE BANDAS (Ordem sugerida)
        BANDS_PRIORITY = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
        
        for (s, m, p) in sorted(available_combos.keys()):
            found_bands = available_combos[(s, m, p)]
            label_text = f"{s.upper()} {m.replace('_', ' ').title()} ({p.title()})"
            label_html = widgets.HTML(f'<div style="width:200px; font-weight:bold; color:#333; font-size:11px;">{label_text}</div>')
            
            # Ordenação dinâmica: Prioritárias primeiro, resto depois (em ordem alfabética)
            sorted_bands = sorted(list(found_bands), key=lambda x: BANDS_PRIORITY.index(x) if x in BANDS_PRIORITY else 100 + ord(x[0]))
            
            band_widgets = []
            for b in sorted_bands:
                chk = widgets.Checkbox(value=False, indent=False, layout=L(width='18px', height='18px', margin='0'))
                if s == 'sentinel2' and m == 'minnbr': chk.value = True
                
                self.band_chk_map[(s, m, p, b)] = chk
                
                status_cell = PipelineStepUI.make_status_cell(chk, b.upper(), 'mfm-ok', width='110px')
                band_widgets.append(status_cell)
            
            row = widgets.HBox([label_html] + band_widgets, layout=L(align_items='center', padding='5px 0', border_bottom='1px solid #eee'))
            matrix_rows.append(row)

        matrix_vbox = widgets.VBox(matrix_rows, layout=L(
            border='1px solid #dee2e6', padding='10px', margin='10px 0',
            background_color='#fff', border_radius='4px', max_height='400px', 
            overflow_y='auto', overflow_x='auto'
        ))
        
        return widgets.VBox([header, matrix_vbox])

    def _build_hp_section(self):
        L = widgets.Layout
        self.w_iters = widgets.Text(value="7000", description='Iteraciones:', style={'description_width': '150px'}, layout=L(width='350px'))
        self.w_batch = widgets.Text(value="1000", description='Tamaño de Lote:', style={'description_width': '150px'}, layout=L(width='350px'))
        self.w_lr = widgets.Text(value="0.001", description='Tasa de Aprendizaje:', style={'description_width': '150px'}, layout=L(width='350px'))
        self.w_layers = widgets.Text(value="7, 14, 7", description='Capas Ocultas:', style={'description_width': '150px'}, layout=L(width='350px'))
        
        return widgets.VBox([
            widgets.HTML("<b style='font-size:14px; color:#2c3e50;'> Hiperparámetros (DNN)</b>"),
            widgets.HBox([self.w_iters, self.w_batch], layout=L(gap='10px')),
            widgets.HBox([self.w_lr, self.w_layers], layout=L(gap='10px')),
        ], layout=L(padding='15px', border='1px solid #eee', border_radius='8px', margin='0 0 15px 0', flex='1'))

    def _suggest_next_id(self):
        """Sugere o MENOR ID de treino (001, 002...) disponível (preenchendo lacunas)."""
        models = list_trained_models()
        used_ids = set()
        import re
        for m in models:
            # Garante compatibilidade caso o cache ainda tenha o formato antigo
            m_id = m if isinstance(m, str) else m.get('training_id', '')
            match = re.search(r'training_(\d{3})', m_id)
            if match:
                used_ids.add(int(match.group(1)))
        
        # Encontra o primeiro buraco na sequência começando de 1
        for i in range(1, 1000):
            if i not in used_ids:
                return f"{i:03d}"
        return "001"

    def _build_dest_section(self):
        L = widgets.Layout
        next_id = self._suggest_next_id()
        self.w_training_id = widgets.Text(value=next_id, description='ID Training:', style={'description_width': '120px'}, layout=L(width='300px'))
        self.w_shortname = widgets.Text(value='peru_v1', description='Nome:', layout=L(width='200px'))
        
        # Smart Naming Hook
        def _hook_smart_naming(change):
            self._auto_generate_shortname()
            
        # Bind to samples
        for chk in self.chk_dict.values():
            chk.observe(_hook_smart_naming, names='value')
            
        # Bind to bands
        for chk in self.band_chk_map.values():
            chk.observe(_hook_smart_naming, names='value')

        self.w_comment = widgets.Textarea(placeholder='Comentários...', layout=L(width='98%', height='60px'))
        
        return widgets.VBox([
            widgets.HTML("<b style='font-size:14px; color:#2c3e50;'>Destino de los Resultados</b>"),
            widgets.HBox([self.w_training_id, self.w_shortname], layout=L(gap='15px')),
            self.w_comment,
        ], layout=L(padding='15px', border='1px solid #eee', border_radius='8px', margin='0 0 15px 0'))

    def _refresh_ui(self):
        self._refresh_canvas_hub(show_loader=True)
        

    def make_spinner(self, msg="Cargando..."):
        return widgets.HTML(f"""
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="mfm-loader-mini"></div>
                <span style="color: #666; font-size: 11px; font-weight: bold;">{msg}</span>
            </div>
            <style>
            .mfm-loader-mini {{
                border: 2px solid #f3f3f3;
                border-top: 2px solid #3498db;
                border-radius: 50%;
                width: 14px;
                height: 14px;
                animation: mfm-spin 0.8s linear infinite;
            }}
            @keyframes mfm-spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            </style>
        """)

    def _on_canvas_batch_action(self, mode):
        """Ação em lote no repositório do Canvas."""
        q = self.canvas_search_query.lower()
        if mode == 'all':
            for rid, info in self.canvas_history.items():
                if q in rid.lower() or q in info.get('shortname','').lower():
                    self.selected_models[rid] = info
        elif mode == 'none':
            self.selected_models = {}
        
        self._refresh_canvas_hub()
        self._update_canvas()

    def _sync_repository(self, show_loader=False, force_refresh=False):
        if show_loader: self.show_loader("Sincronizando Repositorio...")
        
        # list_trained_models e list_sample_collections_gcs agora respeitam o cache por padrão
        models = list_trained_models(force_refresh=force_refresh)
        
        # Atualiza também a lista de amostras se for um refresh forçado
        if force_refresh:
            list_sample_collections_gcs(force_refresh=True)
            self.samples_area = self._build_matrix() # Reconstroi a matriz de amostras
            self.new_training_tab.children = [
                self.new_training_tab.children[0], # Title
                self.samples_area,                 # New Matrix
                *self.new_training_tab.children[2:]# Rest
            ]

        fs = _get_fs()
        
        cache = _load_m4_cache()
        metadata_cache = cache.get('metadata', {})
        
        updated_cache = False
        for m_id in models:
            # Só baixa metadados se for novo OU se pedirmos refresh total
            if m_id not in metadata_cache or force_refresh:
                try:
                    from M0_auth_config import CONFIG
                    m_path = cache.get('meta', {}).get(m_id, {}).get('path', '')
                    if not m_path: continue
                    clean_path = m_path.replace('gs://', '').replace(f"{CONFIG['bucket']}/", '').lstrip('/')
                    with fs.open(f"{CONFIG['bucket']}/{clean_path}/metadata.json", 'r') as f:
                        meta = json.load(f)
                    try:
                        with fs.open(f"{CONFIG['bucket']}/{clean_path}/metrics.json", 'r') as f:
                            metrics = json.load(f)
                        meta['metrics'] = metrics
                    except Exception: pass
                    metadata_cache[m_id] = meta
                    updated_cache = True
                except Exception: pass
        if updated_cache:
            cache['metadata'] = metadata_cache
            _save_m4_cache(cache)
            
        if show_loader: self.hide_loader()
        self._refresh_canvas_hub()


    def _update_canvas_live(self, history, embeds, preds, y_true, samples, b_cfg):
        """Atualiza apenas o painel de gráficos vivos, sem tocar na estrutura estável do canvas."""
        # Inicializa a estrutura estática do cabeçalho UMA só VEZ por sessão de treino
        if not getattr(self, '_live_initialized', False):
            self._live_header_html = widgets.HTML()
            self._live_plots_out = widgets.Output()
            self.canvas_output.clear_output(wait=True)
            with self.canvas_output:
                display(HTML("<h2 style='color:#2c3e50; border-bottom:3px solid #3498db; padding-bottom:5px; margin-bottom:15px;'>Entrenamiento en Vivo</h2>"))
                display(self._live_header_html)
                display(self._live_plots_out)
            self._live_initialized = True

        # 1. HEADER DO TREINO ATUAL (Metadados Live via Reatividade .value para não piscar)
        from sklearn.metrics import classification_report
        try:
            rep = classification_report(y_true, (preds > 0.5).astype(int), output_dict=True, zero_division=0)
        except Exception:
        rep = {}
        hp_live = {
            'training_id': self.w_training_id.value, 'shortname': self.w_shortname.value,
            'sample_collections': samples, 'bands_input': sorted(b_cfg.keys()),
            'layers': self.w_layers.value, 'lr': self.w_lr.value,
            'sample_count': self.trainer_instance._sample_count, 'comment': self.w_comment.value,
            'training_date': '[LIVE] Entrenamiento en curso...'
        }
        
        if self.viz_config.get('title'): 
            self._live_header_html.value = render_model_card_html(hp_live, {'classification_report': rep})
        else:
            self._live_header_html.value = ""

        # Atualiza SOMENTE o sub-container de gráficos
        self._live_plots_out.clear_output(wait=True)
        with self._live_plots_out:
            
            # Atualiza métricas no ranking lateral (LIVE)
            if hasattr(self, 'live_training_info') and self.live_training_info:
                self.live_training_info['acc'] = history['val_acc'][-1] if history['val_acc'] else 0
                self.live_training_info['f1'] = rep.get('1', {}).get('f1-score', 0)
                self._refresh_canvas_hub()
            
            # --- SLIDER COMO BARRA DE PROGRESSO ---
            current_step = len(history.get('steps', [])) - 1
            if current_step >= 0:
                if self.w_global_slider.max < current_step:
                    self.w_global_slider.max = current_step
                # Desabilita o observer temporariamente para evitar recálculo de canvas
                self.w_global_slider.unobserve(self._on_global_slider_change, names='value')
                self.w_global_slider.value = current_step
                self.w_global_slider.observe(self._on_global_slider_change, names='value')

            render_diagnostic_dashboard(history, embeds, preds, y_true, viz_config=self.viz_config)
            
            # 2. MODELOS DO RANKING (Comparação em Tempo Real)
            if self.selected_models:
                display(HTML("<div style='margin:50px 0; border-top:3px solid #3498db;'></div>"))
                for mid, info in self.selected_models.items():
                    view_analytics(info, out_widget=None, clear_before=False, viz_config=self.viz_config)
                    display(HTML("<div style='margin:40px 0; border-top:1px dashed #ccc;'></div>"))

    def _on_canvas_search_change(self, val):
        self.canvas_search_query = val
        self._refresh_canvas_hub()

    def _on_global_slider_change(self, change):
        self.canvas_slider_val = change['new']
        # Se não estamos em treino ativo, atualiza todos os cards
        if not getattr(self, '_live_initialized', False):
            self._update_canvas()

    def _refresh_canvas_hub(self):
        """Redesenha o Ranking no Painel Lateral do Canvas."""
        # 1. Carregar lista e metadados
        m_ids = list_trained_models()
        cache = _load_m4_cache()
        
        full_data = []
        for mid in m_ids:
            # Garante que mid seja string mesmo se vier um dicionário de um cache antigo
            if isinstance(mid, dict): mid = mid.get('training_id')
            if not mid: continue
            
            # O path e outros dados extras foram movidos para a sub-chave 'meta'
            meta = cache.get('meta', {}).get(mid, {})
            # Se não estiver no cache, info mínima
            if not meta and mid in self.canvas_history:
                meta = self.canvas_history[mid]
            
            # As métricas e dados pós-treino salvos no GCS ficam sob 'metadata'
            metadata_rich = cache.get('metadata', {}).get(mid, {})
            if metadata_rich:
                meta.update(metadata_rich)
            
            metrics = meta.get('metrics', {})
            rep = metrics.get('classification_report', {})
            acc = rep.get('accuracy', 0)
            f1 = rep.get('1', {}).get('f1-score', 0)
            
            full_data.append({
                'id': mid, 'acc': acc, 'f1': f1, 'meta': meta,
                'shortname': meta.get('shortname', ''),
                'path': meta.get('path', '')
            })
            # Atualiza histórico local
            if mid not in self.canvas_history: self.canvas_history[mid] = meta
            
        # 2. Filtrar
        q = self.canvas_search_query.lower()
        if q:
            full_data = [d for d in full_data if q in d['id'].lower() or q in d['shortname'].lower()]
            
        # 0. Adicionar Treino ao Vivo (se existir)
        if hasattr(self, 'live_training_info') and self.live_training_info:
            full_data.append(self.live_training_info)

        # 3. Ordenar
        rev = not self.canvas_sort_asc
        if self.canvas_sort_col == 'acc':
            full_data.sort(key=lambda x: x['acc'], reverse=rev)
        elif self.canvas_sort_col == 'f1':
            full_data.sort(key=lambda x: x['f1'], reverse=rev)
        else:
            full_data.sort(key=lambda x: x['id'], reverse=self.canvas_sort_asc)

        # 4. Construir Widgets
        available_widgets = []
        selected_widgets = []
        
        for d in full_data:
            mid = d['id']
            is_selected = mid in self.selected_models
            
            # KPI string minimalista
            kpi_str = f"Acc: {d['acc']:.1%} | F1: {d['f1']:.2f}" if d['acc'] > 0 else "Sin métricas"
            
            # Botão de Ação
            btn = widgets.Button(
                icon='plus' if not is_selected else 'times',
                tooltip='Adicionar ao Canvas' if not is_selected else 'Remover do Canvas',
                layout=widgets.Layout(width='32px', height='32px', margin='0 5px 0 0'),
                button_style='success' if not is_selected else 'danger'
            )
            
            if not is_selected:
                btn.on_click(lambda _, r=mid, i=d: self._on_canvas_batch_action('add', r, i))
            else:
                btn.on_click(lambda _, r=mid: self._on_canvas_batch_action('remove', r))
                
            info_html = widgets.HTML(f"""
                <div style='line-height:1.2; cursor:default; width:100%;'>
                    <div style='font-size:11px; font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{mid}</div>
                    <div style='font-size:10px; color:#666;'>{kpi_str}</div>
                </div>
            """, layout=widgets.Layout(flex='1'))
            
            row = widgets.HBox([btn, info_html], layout=widgets.Layout(
                align_items='center', padding='4px', border_bottom='1px solid #eee',
                background_color='#fff' if not is_selected else '#e3f2fd'
            ))
            
            if is_selected: selected_widgets.append(row)
            else: available_widgets.append(row)
            
        self.canvas_available_box.children = available_widgets
        self.canvas_selected_box.children = selected_widgets

    def _on_canvas_batch_action(self, action, rid=None, info=None):
        """Gerencia ações de adição/remoção individual ou em lote no Canvas."""
        if action == 'add' and rid:
            self.selected_models[rid] = info
        elif action == 'remove' and rid:
            self.selected_models.pop(rid, None)
        elif action == 'all':
            q = self.canvas_search_query.lower()
            for r, i in self.canvas_history.items():
                if q in r.lower() or q in i.get('shortname','').lower():
                    self.selected_models[r] = i
        elif action == 'none':
            self.selected_models = {}
            
        self._refresh_canvas_hub()
        self._update_canvas()

    
    def _auto_generate_shortname(self, *_):
        # Base format: [region]_[n]bands_[method]
        # Example: peru_r1_4bands_minnbr
        
        selected_samples = [name for name, chk in self.chk_dict.items() if chk.value]
        if not selected_samples:
            self.w_shortname.value = ""
            return
            
        first_sample = selected_samples[0]
        region_part = first_sample.replace('_samples', '').replace('library_samples_', '')
        if len(selected_samples) > 1:
            region_part += f'_multi'
            
        methods = set()
        bands_count = 0
        for (s, m, p, b), chk in self.band_chk_map.items():
            if chk.value:
                bands_count += 1
                methods.add(m)
                
        if bands_count == 0:
            return
            
        method_part = list(methods)[0] if len(methods) == 1 else 'mixed'
        
        new_name = f"{region_part}_{bands_count}bands_{method_part}"
        self.w_shortname.value = new_name

    def _build_viz_toolbar(self):
        L = widgets.Layout
        
        # 1. Labels e Criação
        labels = {
            'title': 'Metadatos', 'scores': 'KPIs', 'cm': 'Confusion', 
            'history': 'Historial', 'prob': 'Prob', 'pr': 'PR-Curve', 
            'pca2d': 'PCA 2D', 'pca3d_static': 'PCA 3D (Est)', 'pca3d': 'PCA 3D (Int)',
            'tsne3d_static': 't-SNE 3D (Est)', 'tsne3d': 't-SNE 3D (Int)',
            'management': 'Gestión'
        }
        
        chks = {}
        for key, label in labels.items():
            cb = widgets.Checkbox(value=self.viz_config[key], description=label, layout=L(width='auto', margin='0 5px 0 0'))
            def _on_local_change(change, k=key):
                self.viz_config[k] = change['new']
            cb.observe(_on_local_change, names='value')
            chks[key] = cb
            
        def _set_all(val):
            for k in labels.keys():
                chks[k].value = val
                self.viz_config[k] = val

        # 2. Agrupamento por Categorias (Linhas)
        def _make_row(title, keys):
            return widgets.HBox([
                widgets.HTML(f"<b style='width:160px; display:inline-block; color:#2c3e50; font-size: 13px;'>{title}:</b>"),
                widgets.HBox([chks[k] for k in keys], layout=L(flex_flow='row wrap'))
            ], layout=L(align_items='center', margin='2px 0'))
            
        row1 = _make_row("Metadatos", ['title', 'scores'])
        row2 = _make_row("Estatísticas Básicas", ['cm', 'history', 'prob', 'pr'])
        row3 = _make_row("Espaço Latente PCA", ['pca2d', 'pca3d_static', 'pca3d'])
        row4 = _make_row("Espaço Latente t-SNE", ['tsne3d_static', 'tsne3d'])
        row5 = _make_row("Gestión", ['management'])
        
        chk_container = widgets.VBox([row1, row2, row3, row4, row5])
        
        # 3. Botões de Ação na parte inferior
        btn_all = widgets.Button(description="Todos", layout=L(width='70px'), button_style='info')
        btn_none = widgets.Button(description="Nenhum", layout=L(width='70px'), button_style='warning')
        btn_all.on_click(lambda _: _set_all(True))
        btn_none.on_click(lambda _: _set_all(False))
        
        btn_container = widgets.HBox([btn_all, btn_none, widgets.HTML("<div style='width:20px'></div>"), self.w_apply_btn], layout=L(margin='15px 0 0 0', align_items='center'))
        
        return widgets.VBox([
            widgets.HTML("<h4 style='margin:0 0 10px 0; color:#34495e; border-bottom:1px solid #ddd; padding-bottom:5px;'>Opciones de Visualización</h4>"),
            chk_container,
            btn_container
        ], layout=L(margin='10px 0', padding='15px', background_color='#f8f9fa', border_radius='5px', border='1px solid #dee2e6'))

    def _update_canvas(self):
        """Renderiza o GridBox responsivo com os cards dos modelos selecionados."""
        self._live_initialized = False
        self._refresh_canvas_hub()
        self.canvas_output.clear_output(wait=True)
        
        with self.canvas_output:
            if not self.selected_models and not self.trainer_instance:
                display(HTML("<div style='padding:100px; text-align:center; background:white; border-radius:8px;'> <span style='font-size:50px;'></span><br><h3 style='color:#999;'>Canvas vazio</h3><p style='color:#ccc;'>Busque y seleccione modelos en el panel lateral para visualizarlos aquí.</p></div>"))
                return
            
            # --- AJUSTE DINÂMICO DO SLIDER GLOBAL ---
            max_steps = 1
            for mid, info in self.selected_models.items():
                h = info.get('history', {})
                if 'steps' in h and len(h['steps']) > 0:
                    max_steps = max(max_steps, len(h['steps']))
            self.w_global_slider.max = max_steps - 1
            
            # --- CONSTRUÇÃO DOS CARDS ---
            cards = []
            for mid, info in self.selected_models.items():
                # Cada card é um Output individual para isolar erros e estilos
                card_out = widgets.Output(layout=widgets.Layout(
                    border='1px solid #eee', padding='10px', border_radius='8px', background_color='#fff'
                ))
                with card_out:
                    view_analytics(info, out_widget=None, clear_before=False, viz_config=self.viz_config, epoch_index=self.canvas_slider_val)
                cards.append(card_out)
            
            # Grid responsivo: ocupa o espaço disponível, quebrando linhas conforme necessário
            grid = widgets.GridBox(cards, layout=widgets.Layout(
                grid_template_columns='repeat(auto-fill, minmax(550px, 1fr))',
                grid_gap='20px',
                width='100%'
            ))
            display(grid)

def start_training(ui):
    _get_tf() # Garante que TF_AVAILABLE foi definido
    if not TF_AVAILABLE:
        print("\n" + "="*70)
        print(" [AVISO] AMBIENTE LOCAL INCOMPATIBLE")
        print(" O seu processador não possui as instruções AVX/AVX2 requeridas pelo TensorFlow.")
        print(" POR FAVOR: Execute este treinamento no Google Colab.")
        if TF_ERROR: print(f" Detalhes: {TF_ERROR}")
        print("="*70 + "\n")
        return
    # -----------------------------------------------------------------
    # 1⃣ Retraining intent (checked via the UI state)
    # -----------------------------------------------------------------
    intent = ui.retrain_intent
    if intent.get('mode'):
        hp = intent.get('hp')
        
        # Determine training ID and shortname for the target model
        target_id = hp['training_id'] if hp else ui.w_training_id.value
        target_short = hp['shortname'] if hp else ui.w_shortname.value
        
        # If 'borrar' mode is selected, delete the target model first.
        if intent['mode'] == 'borrar':
            print(f" Borrando modelo previo: {target_id} ({target_short})")
            ModelTrainer.delete_model(target_id, target_short)
            
        # If hp is provided, load its full configuration into the widgets.
        if hp:
            ui._load_config_into_widgets(hp)
            selected_samples = hp.get('sample_collections', [])
            
        print(f" Modo '{intent['mode']}' activado para {target_id}")
        
        # Reset the intent so it does not fire again accidentally.
        ui.retrain_intent = {'mode': None, 'hp': None}
        # Reset the checkboxes visually too
        for cb in [ui.cb_retrain, ui.cb_reextract, ui.cb_borrar_retrain]:
            cb.unobserve(ui._on_intent_cb_change, names='value')
            cb.value = False
            cb.observe(ui._on_intent_cb_change, names='value')
    
    # 2⃣ Get parameters from UI
    if not intent.get('mode') or not hp:
        selected_samples = [name for name, chk in ui.chk_dict.items() if chk.value]

    if not selected_samples:
        print("Error: Ninguna muestra seleccionada.")
        return

    # 3⃣ Constrói o dicionário de configuração de bandas a partir da Matriz Dinâmica
    bands_config = {}
    sensors_used = set()
    for (s, m, p, b), chk in ui.band_chk_map.items():
        if chk.value:
            # p_norm será 'monthly' ou 'yearly'
            p_norm = 'monthly' if p == 'mensal' else 'yearly'
            # A extração espera: bands_config[band_name] = {'sensor': ..., 'mosaic': ..., 'periodicity': ...}
            bands_config[b] = {
                'sensor': s,
                'mosaic': m,
                'periodicity': p_norm
            }
            sensors_used.add(s)
            
    if not bands_config:
        print("Error: No se han seleccionado bandas en la Matriz de Extracción.")
        return
        
    # Atualiza o sensor global para refletir o que está sendo usado no treinamento
    if len(sensors_used) == 1:
        GLOBAL_OPTS['SENSOR'] = [list(sensors_used)[0]]
    elif len(sensors_used) > 1:
        GLOBAL_OPTS['SENSOR'] = ['multisensor']
        
    # --- PREPARAR INTERFACE PARA NOVO TREINO ---
    ui.selected_models = {}       # Limpa seleções anteriores
    ui.tab.selected_index = 2     # Vai para a aba Treinamentos (renomeada)
    
    # Registra o treino como "LIVE" para aparecer no ranking lateral
    sensor_suffix = GLOBAL_OPTS['SENSOR'][0].lower()
    ui.live_training_info = {
        'id': f"training_{ui.w_training_id.value}_{ui.w_shortname.value}_{sensor_suffix}",
        'shortname': ui.w_shortname.value,
        'acc': 0, 'f1': 0, 'is_live': True,
        'meta': {'path': ''} # Sem path ainda
    }
    
    ui._live_initialized = False  # Reseta estrutura estável para nova sessão
    ui.canvas_output.clear_output(wait=True)
    ui._refresh_canvas_hub()      # Atualiza a barra lateral mostrando o "LIVE"

    layers = [int(x.strip()) for x in ui.w_layers.value.split(',')]
    iters = int(ui.w_iters.value)
    batch = int(ui.w_batch.value)
    lr = float(ui.w_lr.value)
    
    print(f"Extrayendo píxeles de {len(selected_samples)} colecciones usando Matriz Flexible ({len(bands_config)} bandas). Aguarde...")
    
    def _logger(msg, level="info"):
        print(msg)
        
    X, y = extract_pixels_from_gcs(selected_samples, bands_config, logger=_logger)
    
    if len(X) == 0:
        print("Fallo al extraer píxeles.")
        return
        
    print(f"Éxito: {len(X)} píxeles extraídos (Fuego: {y.sum()} | No-fuego: {(y==0).sum()}).")
    
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    ui.trainer_instance = ModelTrainer(num_input=len(bands_config), layers=layers, lr=lr)
    ui.trainer_instance._bands_input = sorted(bands_config.keys())
    ui.trainer_instance._bands_config = bands_config
    ui.trainer_instance._sample_collections = selected_samples
    ui.trainer_instance._sample_count = {'burned': int(y.sum()), 'not_burned': int((y==0).sum())}
    
    print("Entrenando DNN...")
    
    # Snapshot Directory
    m_id = ui.w_training_id.value
    m_short = ui.w_shortname.value
    snap_dir = f"library_images/models/{m_id}_{m_short}"
    os.makedirs(snap_dir, exist_ok=True)

    def update_chart(history, embeds=None, preds=None, y_true=None):
        ui._update_canvas_live(history, embeds, preds, y_true, selected_samples, bands_config)

    # Iniciar Treino
    ui.trainer_instance.train(X_train, y_train, X_val=X_val, y_val=y_val, 
                              batch_size=batch, n_iters=iters, logger=_logger, 
                              update_chart_fn=update_chart, snapshot_dir=snap_dir)
    
    # --- AUDITORIA FINAL COM t-SNE (INTERATIVO) ---
    print("\n Entrenamiento completado. Generando auditoría t-SNE final de alta resolución...")
    ui._live_initialized = False
    ui._live_plots_out.clear_output(wait=True)
    with ui._live_plots_out:
        import plotly.graph_objects as go
        from sklearn.manifold import TSNE
        try:
            display(HTML("<h4 style='color:#2c3e50; margin-top:20px; font-weight:bold;'>[LIVE] Auditoría t-SNE (Espacio Latente Final)</h4>"))
            display(HTML("<p style='font-size:11px; color:#666;'>Calculando proyección no-lineal para mejor visualización de clústeres...</p>"))
            
            idx_v = np.random.choice(len(X_val), min(600, len(X_val)), replace=False)
            X_v_sub = X_val[idx_v]
            y_v_sub = y_val[idx_v]
            
            emb_v = ui.trainer_instance.get_embeddings(X_v_sub)
            prd_v = ui.trainer_instance.predict(X_v_sub)
            
            print("  - Calculando manifold t-SNE (esto puede tardar)...")
            tsne = TSNE(n_components=3, perplexity=30, random_state=42, max_iter=1000)
            coords_tsne = tsne.fit_transform(emb_v)
            
            ui.trainer_instance.tsne_snapshot = coords_tsne.tolist()
            
            print("  - Generando figura interactiva...")
            fig_tsne = go.Figure(data=[go.Scatter3d(
                x=coords_tsne[:,0], y=coords_tsne[:,1], z=coords_tsne[:,2],
                mode='markers',
                marker=dict(size=4, color=prd_v.flatten(), colorscale='RdBu_r', opacity=0.8, showscale=True),
                text=[f"Clase: {'Fuego' if l==1 else 'No-fuego'}<br>Pred: {p:.2%}" for l, p in zip(y_v_sub, prd_v.flatten())]
            )])
            fig_tsne.update_layout(
                margin=dict(l=0, r=0, b=0, t=30),
                scene=dict(xaxis_title='t-SNE 1', yaxis_title='t-SNE 2', zaxis_title='t-SNE 3')
            )
            display(HTML(fig_tsne.to_html(include_plotlyjs=True, full_html=False)))
            print("[OK] Auditoría t-SNE lista.")
        except Exception as e:
            print(f"[AVISO] No se pudo gerar t-SNE final: {e}")

    print("Guardando estructura (muestras, píxeles, metadatos, métricas) en GCS...")
    try:
        ui.trainer_instance.save(ui.w_training_id.value, ui.w_shortname.value, comment=ui.w_comment.value, logger=_logger)
        print("¡Modelo y Model Card guardados exitosamente!")
        
        # Inserir o modelo fresquinho na Mesa do Canvas automaticamente
        final_id = f"training_{ui.w_training_id.value}_{ui.w_shortname.value}_{GLOBAL_OPTS['SENSOR'][0].lower()}"
        ui.selected_models = {
            final_id: {'training_id': final_id, 'path': model_path(ui.w_training_id.value, ui.w_shortname.value)}
        }
        
        ui.live_training_info = None  # Remove o status de LIVE após conclusão
        ui._live_initialized = False
        ui._sync_repository(show_loader=False)
        ui._update_canvas()  # Pinta o card final!
        
    except Exception as e:
        print(f"Error al guardar: {e}")


def run_ui():
    ui = ModelTrainerUI()
    ui.display()
    return ui
