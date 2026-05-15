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

import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import matplotlib.pyplot as plt
from datetime import datetime

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

def list_sample_collections_gcs():
    """Lista arquivos CSV de amostras curadas no GCS."""
    from M0_auth_config import CONFIG
    try:
        fs = _get_fs()
        path = f"{CONFIG['bucket']}/{CONFIG['gcs_library_samples']}"
        files = fs.ls(path)
        return sorted([f.split('/')[-1].replace('.csv', '') for f in files if f.endswith('.csv')], reverse=True)
    except Exception:
        return []

def list_trained_models():
    """Lista modelos já treinados no GCS."""
    from M0_auth_config import _gcs_models_base
    try:
        fs = _get_fs()
        path = f"{CONFIG['bucket']}/{_gcs_models_base()}"
        models = []
        if fs.exists(path):
            trainings = fs.ls(path)
            for t_dir in trainings:
                t_name = t_dir.split('/')[-1]
                if t_name.startswith('training_'):
                    models.append({'training_id': t_name, 'path': t_dir})
        return models
    except Exception:
        return []

def extract_pixels_from_gcs(sample_groups, bands_config, logger=None):
    """
    Extrai píxeis do GCS baseado em uma configuração flexível de bandas.
    Validando existência prévia para evitar erros silenciosos.
    """
    from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name
    from M_cache import CacheManager
    
    fs = _get_fs()
    state = CacheManager.load() or {}
    gcs_chunks = state.get('gcs_chunks', {})
    
    dfs = []
    for group in sample_groups:
        sample_path = f"{CONFIG['bucket']}/{CONFIG['gcs_library_samples']}/{group}.csv"
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
                        if logger: logger(f"  ⚠️ Se ha detectado una fecha futura {p_found} no CSV. Corrigiendo para {file_date}...", "warning")
                        temp_df['period'] = file_date
                        p_found = [file_date]
                    
                    if logger: logger(f"  🔍 Contenido: {len(temp_df)} puntos | Períodos: {p_found}", "info")
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
            config = bands_config[b]
            s_name = config.get('sensor').lower()
            m_type = config.get('mosaic').lower()
            
            # Constrói o nome base do mosaico para buscar no cache
            # image_peru_fire_{sensor}_{mosaic}_{date}
            m_base_name = f"image_peru_fire_{s_name}_{m_type}_{p}"
            
            # Verifica no cache se esta banda existe para este mosaico
            if m_base_name not in gcs_chunks or b not in gcs_chunks[m_base_name]:
                missing_bands.append(f"{s_name}/{m_type}/{b}")
                continue
            
            # Constrói o path real do COG
            m_file_name = f"{mosaic_name(y, m, periodicity, band=b, mosaic=m_type, sensor=s_name)}_cog.tif"
            rel_folder = f"{CONFIG['gcs_library_images']}/{s_name}/{periodicity}/{m_type}/{p}/cog"
            band_paths[b] = f"gs://{CONFIG['bucket']}/{rel_folder}/{m_file_name}"

        if missing_bands:
            if logger: logger(f"⚠️ Saltar período {p}: Faltan {len(missing_bands)} bandas ({', '.join(missing_bands)})", "warning")
            continue

        if logger: logger(f"✅ Mosaicos OK para {p}: {len(band_paths)} bandas listas para la extracción.", "info")
        if logger: logger(f"📡 Extrayendo {len(geometries)} muestras de {p}...", "info")
        
        # --- LEITURA REAL DAS BANDAS ---
        if logger: logger(f"✅ Mosaicos OK para {p}: {len(band_paths)} bandas listas para la extracción.", "info")
        if logger: logger(f"📡 Extrayendo {len(geometries)} muestras de {p}...", "info")
        
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
                    if logger: logger(f"  📥 Bajando banda {b}...", "info")
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
            if logger: logger(f"❌ Error crítico en período {p}: {e}", "error")
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

                    if logger:
                        logger(f"Iter {i:5d}/{n_iters} | Loss: {loss_val:.4f} | Acc Treino: {acc_tr:.3f} | Validação: {acc_te:.3f}", "info")
                    
                    if update_chart_fn:
                        update_chart_fn(history, embeds, preds_viz.flatten(), y_viz)
                    
                    if snapshot_dir:
                        snap_path = os.path.join(snapshot_dir, f"iteration_{i:05d}.png")
                        render_diagnostic_dashboard(history, embeds, preds_viz.flatten(), y_viz, save_path=snap_path)

            self._saved_vars = {v.name: sess.run(v) for v in tf.global_variables()}
            self._history = history
            self.snapshot_dir = snapshot_dir

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
        
        print(f"🧹 Eliminando carpeta del modelo (GCSFS): {full_path}")
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
                if logger: logger(f"  📤 Subiendo {fname} a GCS...", "info")
                fs.put(src, dest)
            
            if logger: 
                logger(f"✅ Arquivos do Projector salvos em: {dest_dir}", "info")
                logger(f"💡 Dica: Baixe-os e suba em https://projector.tensorflow.org/", "info")

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
                'sensor':       GLOBAL_OPTS['SENSOR'],
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
                if logger: logger(f"⚠️ No se pudo generar snapshot: {e_snap}", "info")
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
                if logger: logger(f"⚠️ Nota: No se pudo gerar archivos del Projector: {e_proj}", "info")

            # --- 2.8 Iteration History (Snapshots) ---
            if hasattr(self, 'snapshot_dir') and self.snapshot_dir and os.path.exists(self.snapshot_dir):
                if logger: logger("Sincronizando historial de iteraciones com GCS...", "info")
                snap_files = [f for f in os.listdir(self.snapshot_dir) if f.endswith('.png')]
                for sf in snap_files:
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
            src = gcs_path(f"{CONFIG['gcs_library_samples']}/{coll}.csv")
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
            print(f"❌ Erro ao atualizar metadados: {e}")
            return False


# ─── INTERFAZ PREMIUM ─────────────────────────────────────────────────────────

# --- VIEW_ANALYTICS UNIFICADA ---
        
def render_diagnostic_dashboard(history, embeds, preds, y_true, coords_override=None, save_path=None, viz_config=None):
    """
    Motor gráfico unificado para o grid 2x3 (Treino e Histórico).
    viz_config: dict com flags de visibilidade.
    """
    if viz_config is None:
        viz_config = {k: True for k in ['cm', 'history', 'prob', 'pr', 'pca2d', 'pca3d']}
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
    except:
        cm = np.zeros((2,2)); cm_norm = np.zeros((2,2))

    # Determina quais subplots mostrar
    active_plots = []
    if viz_config.get('cm'): active_plots.append('cm')
    if viz_config.get('history'): active_plots.append('history')
    if viz_config.get('pca2d'): active_plots.append('pca2d')
    if viz_config.get('prob'): active_plots.append('prob')
    if viz_config.get('pr'): active_plots.append('pr')
    
    if not active_plots: return

    n = len(active_plots)
    cols = 3
    rows = (n + cols - 1) // cols
    
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
                except: pass
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
            except: pass

    plt.tight_layout()
    plt.show()

    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
    else:
        plt.show()

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

def view_analytics(model_info, out_widget=None, clear_before=True, viz_config=None):
    """
    Visualiza as métricas e o card de um modelo salvo no GCS.
    viz_config: dict opcional com flags de visibilidade.
    """
    if viz_config is None:
        viz_config = {k: True for k in ['title', 'scores', 'cm', 'history', 'prob', 'pr', 'pca2d', 'pca3d', 'tsne3d']}
    fs = _get_fs()
    from M0_auth_config import CONFIG
    try:
        import urllib.parse
        m_path = model_info['path']
        m_path = urllib.parse.unquote(m_path)
        clean_path = m_path.replace('gs://', '').replace('mapbiomas-fire/', '').lstrip('/')
        if 'b/' in clean_path and '/o/' in clean_path: clean_path = clean_path.split('/o/')[-1]
        
        try:
            with fs.open(f"{CONFIG['bucket']}/{clean_path}/metadata.json", 'r') as f: hp = json.load(f)
            with fs.open(f"{CONFIG['bucket']}/{clean_path}/metrics.json", 'r') as f: metrics = json.load(f)
        except:
            with fs.open(f"{CONFIG['bucket']}/{clean_path}/hyperparameters.json", 'r') as f: hp = json.load(f)
            with fs.open(f"{CONFIG['bucket']}/{clean_path}/metrics.json", 'r') as f: metrics = json.load(f)

        def _render_content():
            # --- CHECKBOXES DE ACCIÓN (LIFECYCLE) ---
            try:
                import __main__
                ui = getattr(__main__, 'ui', None)
            except: ui = None

            if ui:
                chk_retrain = widgets.Checkbox(description="Retreinar (mismos píxeles)", value=(ui.retrain_intent['mode']=='retrain' and ui.retrain_intent['hp'].get('training_id')==hp['training_id']), indent=False)
                chk_reextract = widgets.Checkbox(description="Re-extraer & Retreinar", value=(ui.retrain_intent['mode']=='re-extract' and ui.retrain_intent['hp'].get('training_id')==hp['training_id']), indent=False)
                chk_borrar = widgets.Checkbox(description="Borrar & Retreinar", value=(ui.retrain_intent['mode']=='borrar' and ui.retrain_intent['hp'].get('training_id')==hp['training_id']), indent=False)
                
                def _make_exclusive(changed_chk, mode):
                    def _handler(change):
                        if change['new']:
                            # Desmarca os outros
                            for c in [chk_retrain, chk_reextract, chk_borrar]:
                                if c != changed_chk: c.value = False
                            # Salva a intenção global
                            ui.retrain_intent = {'mode': mode, 'hp': hp}
                            ui._load_config_into_widgets(hp) # Pre-carrega na aba 1
                        else:
                            # Se desmarcou o atual e os outros estão falsos, limpa a intenção
                            if not any([chk_retrain.value, chk_reextract.value, chk_borrar.value]):
                                ui.retrain_intent = {'mode': None, 'hp': None}
                    return _handler
                
                chk_retrain.observe(_make_exclusive(chk_retrain, 'retrain'), names='value')
                chk_reextract.observe(_make_exclusive(chk_reextract, 're-extract'), names='value')
                chk_borrar.observe(_make_exclusive(chk_borrar, 'borrar'), names='value')
                
                action_row = widgets.HBox([
                    widgets.HTML("<b style='color:#e67e22; font-size:12px; margin-right:15px;'>⚙️ Acción Pendiente (Run start_training):</b>"),
                    chk_retrain, chk_reextract, chk_borrar
                ], layout=widgets.Layout(margin='0 0 15px 0', padding='10px', background='#fff3cd', border='1px solid #ffeeba', border_radius='4px', align_items='center'))
                display(action_row)

            # --- SISTEMA DE VOTACIÓN "SAFO" (SUBCARDS) ---
            h_rating = hp.get('rating', 0)
            a_rating = metrics.get('auto_rating', 0)
            
            # --- GRID UNIFICADO DE KPIs Y AUDITORÍA ---
            rep = metrics.get('classification_report', {})
            
            def make_kpi_card(title, value, color):
                return widgets.HTML(f"""
                <div class="kpi-box" style="border-left: 5px solid {color}; padding: 15px; background: white; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); height: 100%;">
                    <div style="font-size: 11px; color: #6c757d; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;">{title}</div>
                    <div style="font-size: 22px; font-weight: bold; color: #212529;">{value}</div>
                </div>
                """)

            kpi_acc = make_kpi_card("Acurácia Global", f"{rep.get('accuracy', 0):.1%}", "#28a745")
            kpi_prec = make_kpi_card("Precisión (Fuego)", f"{rep.get('1', {}).get('precision', 0):.1%}", "#dc3545")
            kpi_rec = make_kpi_card("Recall (Fuego)", f"{rep.get('1', {}).get('recall', 0):.1%}", "#ffc107")
            kpi_f1 = make_kpi_card("F1-Score (Fuego)", f"{rep.get('1', {}).get('f1-score', 0):.1%}", "#17a2b8")

            # Estrelas IA (Subcard Professional)
            ai_btns = []
            for s_idx in range(1, 6):
                char = "★" if s_idx <= a_rating else "☆"
                b = widgets.Button(description=char, layout=widgets.Layout(width='26px', height='26px', margin='0', padding='0'))
                b.style.button_color = '#bdc3c7' if s_idx <= a_rating else '#fff'
                ai_btns.append(b)
            
            ai_panel = widgets.VBox([
                widgets.HTML("<div style='font-size:11px; color:#6c757d; font-weight:bold; margin-bottom:5px; text-transform:uppercase;'>Evaluación IA</div>"),
                widgets.HBox(ai_btns, layout=widgets.Layout(margin='0'))
            ], layout=widgets.Layout(background='white', padding='15px', border_left='5px solid #bdc3c7', border_radius='4px', box_shadow='0 2px 5px rgba(0,0,0,0.1)', flex='1'))
            
            # Estrelas Humanas (Subcard Professional con Confirmación)
            user_btns = []
            user_stars_container = widgets.HBox([], layout=widgets.Layout(margin='0')) # Container para trocar entre estrelas e confirmação
            
            def _show_stars():
                btns = []
                for i in range(1, 6):
                    btn = widgets.Button(description="★" if i <= h_rating else "☆", 
                                       layout=widgets.Layout(width='26px', height='26px', margin='0', padding='0'),
                                       style={'button_color': '#f1c40f' if i <= h_rating else '#fff'})
                    def _hnd_click(b, val=i):
                        # Mostrar confirmação
                        btn_back = widgets.Button(description="<-", layout=widgets.Layout(width='35px', height='26px'), button_style='info')
                        btn_ok = widgets.Button(description="OK", layout=widgets.Layout(width='45px', height='26px'), button_style='success')
                        conf_msg = widgets.HTML(f"<b style='color:#d4ac0d; font-size:11px; margin-right:5px;'>¿Confirmar {val}?</b>")
                        
                        def _do_ok(_):
                            user_stars_container.children = [self.make_spinner("Guardando...")]
                            if ModelTrainer.update_model_metadata(hp['training_id'], hp['shortname'], {'rating': val}):
                                if ui: ui._refresh_models_list()
                                # Simplesmente atualiza a visão local do card
                                hp['rating'] = val # Update local ref
                                _show_stars()
                            else:
                                _show_stars() # Reverter em caso de erro

                        def _do_back(_): _show_stars()
                        
                        btn_ok.on_click(_do_ok); btn_back.on_click(_do_back)
                        user_stars_container.children = [conf_msg, btn_back, btn_ok]
                    
                    btn.on_click(_hnd_click)
                    btns.append(btn)
                user_stars_container.children = btns

            _show_stars()
                
            user_panel = widgets.VBox([
                widgets.HTML("<div style='font-size:11px; color:#6c757d; font-weight:bold; margin-bottom:5px; text-transform:uppercase;'>Auditoría Humana</div>"),
                user_stars_container
            ], layout=widgets.Layout(background='white', padding='15px', border_left='5px solid #f1c40f', border_radius='4px', box_shadow='0 2px 5px rgba(0,0,0,0.1)', flex='1'))
            
            # --- CICLO DE VIDA (Nuevas acciones integradas al Card) ---
            def _set_intent(mode):
                def __h(_):
                    if ui:
                        ui.retrain_intent = {'mode': mode, 'hp': hp}
                        ui._load_config_into_widgets(hp)
                        ui.tab.selected_index = 0 # Volver a Novo Treino
                        print(f"✅ Intento '{mode}' cargado para {hp['training_id']}. Revise la pestaña 'Novo Treino'.")
                return __h

            btn_retr = widgets.Button(description="Retreinar", icon="refresh", layout=widgets.Layout(width='140px'), button_style='info')
            btn_reex = widgets.Button(description="Re-extraer", icon="database", layout=widgets.Layout(width='140px'), button_style='info')
            btn_borr = widgets.Button(description="Borrar & Retreinar", icon="trash", layout=widgets.Layout(width='180px'), button_style='danger')
            
            btn_retr.on_click(_set_intent('retrain'))
            btn_reex.on_click(_set_intent('re-extract'))
            btn_borr.on_click(_set_intent('borrar'))


            # --- INTEGRACIÓN DE CARD E CICLO DE VIDA ---
            # O Header é sempre exibido
            display(HTML(render_model_card_html(hp, metrics, only_header=True)))
            
            if viz_config.get('title'):
                body_html = HTML(render_model_card_html(hp, metrics))
                
                # Painel de Ciclo de Vida integrado (sem emojis no texto)
                lifecycle_box = widgets.VBox([
                    widgets.HTML("<div style='font-size:11px; color:#6c757d; font-weight:bold; margin-bottom:5px; text-transform:uppercase;'>Ciclo de Vida</div>"),
                    widgets.HBox([btn_retr, btn_reex, btn_borr], layout=widgets.Layout(gap='10px'))
                ], layout=widgets.Layout(background='#fdfdfd', padding='15px', border='1px solid #dee2e6', border_top='none', border_radius='0 0 8px 8px', margin='-20px 0 20px 0'))
                
                display(body_html)
                display(lifecycle_box)
            else:
                # Se os metadados estiverem ocultos, adicionamos um espaçador pequeno para o header não ficar colado
                display(HTML("<div style='margin-bottom:15px;'></div>"))

            if viz_config.get('scores'): display(unified_grid)
            
            # --- DIAGNÓSTICO ---
            snap = metrics.get('diagnostic_snapshot')
            if snap:
                import plotly.graph_objects as go
                # Paleta: #2c3e50 (No Fogo) -> #bdc3c7 (Dúvida) -> #e67e22 (Fogo)
                fire_colorscale = [
                    [0, '#2c3e50'],   # Azul Escuro / No Fire
                    [0.5, '#bdc3c7'], # Cinza / Unsure
                    [1, '#e67e22']    # Laranja / Fire
                ]
                pca_coords = np.array(snap.get('pca_coords', []))
                tsne_coords = np.array(snap.get('tsne_coords', []))
                preds = np.array(snap['preds'])
                y_sub = np.array(snap['y_true'])
                render_diagnostic_dashboard(hp.get('history', {}), None, preds, y_sub, coords_override=pca_coords, viz_config=viz_config)
                # PCA 3D Interactiva
                if viz_config.get('pca3d') and pca_coords is not None and len(pca_coords) > 0:
                    fig_pca = go.Figure(data=[go.Scatter3d(
                        x=pca_coords[:,0], y=pca_coords[:,1], z=pca_coords[:,2], mode='markers',
                        marker=dict(size=4, color=preds, colorscale=fire_colorscale, opacity=0.8, showscale=True,
                                   colorbar=dict(title="Confianza", tickvals=[0, 0.5, 1], ticktext=["No Fogo", "Duda", "Fogo"])),
                        text=[f"<b>Real:</b> {'🔥 Fuego' if l==1 else '🌿 No Fuego'}<br><b>Pred:</b> {p:.2%}" for l, p in zip(y_sub, preds)]
                    )])
                    fig_pca.update_layout(title="Auditoría PCA 3D (Interactiva)", margin=dict(l=0, r=0, b=0, t=30), scene=dict(xaxis_title='PC1', yaxis_title='PC2', zaxis_title='PC3'))
                    display(HTML(fig_pca.to_html(include_plotlyjs=True, full_html=False)))

                # t-SNE 3D Interactiva
                if viz_config.get('tsne3d') and tsne_coords is not None and len(tsne_coords) > 0:
                    coords_p = tsne_coords
                    fig_tsne = go.Figure(data=[go.Scatter3d(
                        x=coords_p[:,0], y=coords_p[:,1], z=coords_p[:,2], mode='markers',
                        marker=dict(size=4, color=preds, colorscale=fire_colorscale, opacity=0.8, showscale=True,
                                   colorbar=dict(title="Confianza", tickvals=[0, 0.5, 1], ticktext=["No Fogo", "Duda", "Fogo"])),
                        text=[f"<b>Real:</b> {'🔥 Fuego' if l==1 else '🌿 No Fuego'}<br><b>Pred:</b> {p:.2%}" for l, p in zip(y_sub, preds)]
                    )])
                    fig_tsne.update_layout(title="Auditoría t-SNE 3D (Interactiva)", margin=dict(l=0, r=0, b=0, t=30), scene=dict(xaxis_title='T1', yaxis_title='T2', zaxis_title='T3'))
                    display(HTML(fig_tsne.to_html(include_plotlyjs=True, full_html=False)))
            else:
                try:
                    with fs.open(f"{CONFIG['bucket']}/{clean_path}/weights.npz", 'rb') as f: weights = dict(np.load(f))
                    trainer_tmp = ModelTrainer(num_input=hp['num_input'], layers=hp['layers'])
                    trainer_tmp._saved_vars = weights
                    trainer_tmp.norm_stats = {int(k): tuple(v) for k, v in hp['norm_stats'].items()}
                    X_sub = np.random.randn(300, hp['num_input']); y_sub = np.zeros(300)
                    embeds = trainer_tmp.get_embeddings(X_sub); preds = trainer_tmp.predict(X_sub)
                    render_diagnostic_dashboard(hp.get('history', {}), embeds, preds, y_sub, viz_config=viz_config)
                except: pass

            # --- SLIDER DE HISTÓRICO (TIME MACHINE) ---
            snap_dir = f"library_images/models/{hp['training_id']}_{hp['shortname']}"
            if os.path.exists(snap_dir):
                snaps = sorted([f for f in os.listdir(snap_dir) if f.endswith('.png')])
                if snaps:
                    slider = widgets.IntSlider(min=0, max=len(snaps)-1, description='Época:', layout=widgets.Layout(width='100%'))
                    img_out = widgets.Output()
                    def _show_snap(change):
                        with img_out:
                            clear_output(wait=True)
                            fname = snaps[change['new']]
                            with open(os.path.join(snap_dir, fname), 'rb') as f:
                                display(widgets.Image(value=f.read(), format='png'))
                    slider.observe(_show_snap, names='value')
                    display(widgets.VBox([
                        widgets.HTML("<b style='color:#2c3e50; font-size:14px; margin-top:15px;'>🕰️ Historial de Entrenamiento (Slider Temporal)</b>"),
                        slider, img_out
                    ], layout=widgets.Layout(padding='10px', background='#f9f9f9', border='1px solid #ddd', border_radius='8px')))
                    _show_snap({'new': 0})

            # --- TENSORBOARD PROJECTOR ---
            vec_url = f"https://storage.googleapis.com/mapbiomas-fire/{clean_path}/projector/vectors.tsv"
            meta_url = f"https://storage.googleapis.com/mapbiomas-fire/{clean_path}/projector/metadata.tsv"

        if out_widget:
            if clear_before: out_widget.clear_output(wait=True)
            with out_widget: _render_content()
        else:
            _render_content()
    except Exception as e:
        if out_widget:
            with out_widget: print(f"❌ Erro ao carregar analíticos: {e}")
        else: print(f"❌ Erro ao carregar analíticos: {e}")




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
        
        # --- INTENÇÃO DE RETREINAMENTO ---
        self.retrain_intent = {'mode': None, 'hp': None} # Guarda a intenção atual de re-treinamento
        
        # --- ESTADO DEL CANVAS ---
        self.selected_models = {} # ID -> info (Active in Canvas)
        self.canvas_history = {} # ID -> info (Ever viewed in session)
        self.canvas_search_query = ""
        self.canvas_output = widgets.Output(layout=widgets.Layout(background_color='white', padding='20px'))
        self.analytics_dashboard_output = widgets.Output() # Para carregar card após treino
        self._live_plots_out = widgets.Output()            # Para evitar "piscar" no treino
        
        # --- CONFIGURACIÓN DE VISIBILIDAD ---
        self.viz_config = {
            'title': True, 'scores': True, 'cm': True, 'history': True, 
            'prob': True, 'pr': True, 'pca2d': True, 'pca3d': True, 'tsne3d': True
        }
        
        self.canvas_available_box = widgets.VBox([], layout=widgets.Layout(height='300px', border='1px solid #ddd', padding='0', overflow_y='auto'))
        self.canvas_selected_box = widgets.VBox([], layout=widgets.Layout(height='300px', border='1px solid #ddd', padding='0', overflow_y='auto'))
        
        self.main_area.children = [widgets.HTML("<i>Cargando interfaz...</i>")]

    def _load_config_into_widgets(self, hp):
        """Carrega os parâmetros de um modelo de volta para os widgets de configuração."""
        self.w_training_id.value = hp.get('training_id', '')
        self.w_shortname.value = hp.get('shortname', '')
        self.w_layers.value = ",".join(map(str, hp.get('layers', [64, 32])))
        self.w_lr.value = str(hp.get('lr', 0.001))
        self.w_iters.value = str(hp.get('iters', 5000))
        self.w_batch.value = str(hp.get('batch', 1000))
        self.w_comment.value = hp.get('comment', '')
        
        # Muestras
        sc = hp.get('sample_collections', [])
        for name, chk in self.chk_dict.items():
            chk.value = name in sc
            
        # Bandas
        b_cfg = hp.get('bands_config', {})
        for (s, m, b), chk in self.band_chk_map.items():
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
        # 1. TRENAMIENTOS (Ranking)
        self.analytics_area = widgets.VBox([], layout=widgets.Layout(padding='10px', background_color='white'))
        
        # 2. CANVAS (Visualización)
        self.w_canvas_search = widgets.Text(placeholder='🔍 Buscar en repositorio...', layout=widgets.Layout(width='100%'))
        self.w_canvas_search.observe(lambda c: self._on_canvas_search_change(c['new']), names='value')
        
        btn_all_canvas = widgets.Button(description="Todos", icon="check-square", layout=widgets.Layout(width='90px'), button_style='info')
        btn_none_canvas = widgets.Button(description="Limpiar", icon="square-o", layout=widgets.Layout(width='90px'), button_style='warning')
        
        btn_all_canvas.on_click(lambda _: self._on_canvas_batch_action('all'))
        btn_none_canvas.on_click(lambda _: self._on_canvas_batch_action('none'))
        
        canvas_toolbar = widgets.HBox([self.w_canvas_search, btn_all_canvas, btn_none_canvas], layout=widgets.Layout(gap='5px', margin='0 0 10px 0'))

        left_pane = widgets.VBox([
            widgets.HTML("<b style='font-size:12px;'>📂 Repositorio / Historial</b>"),
            canvas_toolbar,
            self.canvas_available_box
        ], layout=widgets.Layout(flex='1'))
        
        right_pane = widgets.VBox([
            widgets.HTML("<b style='font-size:12px;'>✅ Seleccionados en Canvas</b>"),
            widgets.HTML("<div style='height:42px;'></div>"), # Alinhador com a toolbar
            self.canvas_selected_box
        ], layout=widgets.Layout(flex='1'))
        
        self.canvas_area = widgets.VBox([
            widgets.HTML("<h3 style='color:#2c3e50; margin:0;'>🎨 Canvas Hub: Auditoría Paralela</h3>"),
            widgets.HBox([left_pane, right_pane], layout=widgets.Layout(gap='20px', padding='10px')),
            widgets.HTML("<hr>"),
            self.canvas_output
        ], layout=widgets.Layout(padding='15px', background_color='white'))
        
        # 3. NOVO TREINO (Fluxo Completo)
        hp_sec = self._build_hp_section()
        dest_sec = self._build_dest_section()
        self.samples_area = self._build_matrix()
        self.extraction_area = self._build_extraction_matrix()
        
        self.new_training_tab = widgets.VBox([
            widgets.HTML("<h2 style='color:#2c3e50;'>📂 1. Selección de Muestras</h2>"),
            self.samples_area,
            widgets.HTML("<br><h2 style='color:#2c3e50;'>🛰️ 2. Matriz de Extracción (Multisensor)</h2>"),
            self.extraction_area,
            widgets.HTML("<br><h2 style='color:#2c3e50;'>⚙️ 3. Configuración del Modelo</h2>"),
            hp_sec,
            widgets.HTML("<br><h2 style='color:#2c3e50;'>📍 4. Destino GCS</h2>"),
            dest_sec,
        ], layout=widgets.Layout(padding='20px', background_color='white'))
        
        self.guide_tab = self._build_guide_tab()
        
        self.tab = widgets.Tab(children=[
            self.guide_tab,        # Índice 0
            self.new_training_tab, # Índice 1
            self.analytics_area,    # Índice 2
            self.canvas_area        # Índice 3
        ])
        self.tab.set_title(0, "Guia")
        self.tab.set_title(1, "Novo Treino")
        self.tab.set_title(2, "Trenamientos")
        self.tab.set_title(3, "Canvas")
        
        self.tab.selected_index = 0 # Começa no Guia para orientação
        
        self.main_area.children = [self.tab]
        self._refresh_models_list()
        display(self.main_area)

    def _build_guide_tab(self):
        """Constrói uma interface de documentação interativa para o usuário."""
        html = """
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; background: #fdfdfd; color: #2c3e50; line-height: 1.6;">
            <h1 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">Guia de Operación: M4 Model Trainer</h1>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-top: 20px;">
                <!-- Seção 1: Fluxo de Trabalho -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #3498db; margin-top:0;">Estructura de la Plataforma</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>Guia:</b> Esta pantalla de orientación y documentación.</li>
                        <li><b>Novo Treino:</b> Configuración de nuevos experimentos, selección de muestras y bandas.</li>
                        <li><b>Trenamientos:</b> Ranking histórico con métricas detalladas y gestión de modelos (favoritos/borrar).</li>
                        <li><b>Canvas:</b> Mesa de auditoría paralela para comparar múltiples modelos en profundidad.</li>
                    </ul>
                </div>

                <!-- Seção 2: Hiperparâmetros -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #e67e22; margin-top:0;">Hiperparámetros (DNN)</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>Layers:</b> Define la profundidad de la red (neuronas por capa). Arquitecturas más grandes aprenden más pero son más lentas.</li>
                        <li><b>Learning Rate (LR):</b> La velocidad de ajuste de los pesos. Si es muy alto, el modelo diverge; si es muy bajo, no aprende.</li>
                        <li><b>Epochs:</b> Cuántas veces el modelo verá todo el dataset.</li>
                        <li><b>Batch Size:</b> Cuántas muestras se procesan antes de cada actualización.</li>
                    </ul>
                </div>

                <!-- Seção 3: Métricas de Qualidade -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #27ae60; margin-top:0;">Métricas de Calidad</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>Accuracy:</b> Precisión global de aciertos. Cuidado: puede engañar en datasets desbalanceados.</li>
                        <li><b>Precision:</b> Capacidad de NO clasificar como fuego algo que no lo es (evita falsos positivos).</li>
                        <li><b>Recall:</b> Capacidad de encontrar TODO el fuego real (evita omisiones).</li>
                        <li><b>F1-Score:</b> El equilibrio perfecto. Es la media armónica entre Precision y Recall.</li>
                    </ul>
                </div>

                <!-- Seção 4: Auditoría Visual -->
                <div style="background: white; border: 1px solid #eee; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <h3 style="color: #9b59b6; margin-top:0;">Auditoría de Espacio Latente</h3>
                    <ul style="padding-left: 20px; font-size:13px;">
                        <li><b>PCA y t-SNE:</b> Proyectan datos de 100+ dimensiones a 3D.</li>
                        <li><b>Interpretación:</b> Buscamos "nubes" de colores bien separadas.</li>
                        <li><b>Colores:</b> <b>Azul Petróleo</b> (No Fogo) vs <b>Laranja/Rojo</b> (Fuego).</li>
                        <li><b>Puntos Intermedios (Gris):</b> Muestras donde el modelo tiene baja confianza (duda).</li>
                    </ul>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: #e8f4fd; border-left: 5px solid #3498db; border-radius: 4px; font-size:14px;">
                <b>💡 Pro-Tip del Auditor:</b> Use el <b>Canvas</b> para cargar un modelo antiguo (benchmark) y su modelo nuevo. Compare si la separación de clases en t-SNE 3D ha mejorado o si hay nuevas zonas de confusión.
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
        self._refresh_models_list()

    def _on_sort_change(self, change):
        if change['name'] == 'value':
            self.sort_column = change['new']
            self._refresh_models_list()
            
    def _on_sort_order_change(self, change):
        self.sort_ascending = not self.sort_ascending
        self._refresh_models_list()

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
        new_matrix = self._build_matrix_content()
        self.matrix_container.children = [new_matrix]

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
        
        # BARRA DE BUSCA E BOTÕES DE LOTE (Estilo Canvas Hub)
        self.txt_search_samples = widgets.Text(
            value=self.search_query_samples,
            placeholder='🔍 Buscar muestras...',
            layout=L(width='100%')
        )
        self.txt_search_samples.observe(self._on_search_samples_change, names='value')

        btn_all = widgets.Button(description="Todos", icon="check-square", layout=L(width='90px'), button_style='info')
        btn_none = widgets.Button(description="Limpiar", icon="square-o", layout=L(width='90px'), button_style='warning')
        btn_all.on_click(self._on_select_all_samples)
        btn_none.on_click(self._on_select_none_samples)
        
        sample_toolbar = widgets.HBox([self.txt_search_samples, btn_all, btn_none], layout=L(gap='5px', margin='0 0 10px 0'))

        self.available_samples_container = widgets.VBox([], layout=L(
            border='1px solid #ddd', height='300px', overflow_y='auto', padding='0'
        ))
        self.selected_samples_container = widgets.VBox([], layout=L(
            border='1px solid #ddd', height='300px', overflow_y='auto', padding='0'
        ))

        left_pane = widgets.VBox([
            widgets.HTML("<b style='font-size:12px; color:#555;'>📂 Muestras Disponibles</b>"),
            sample_toolbar,
            self.available_samples_container
        ], layout=L(flex='1'))

        right_pane = widgets.VBox([
            widgets.HTML("<b style='font-size:12px; color:#555;'>✅ Muestras Seleccionadas</b>"),
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
                
            btn = widgets.Button(description=f"➕ {s}", layout=L(width='100%', min_height='28px', margin='1px 0'), style={'button_color': '#f8f9fa'})
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
                btn = widgets.Button(description=f"❌ {s}", layout=L(width='100%', min_height='28px', margin='1px 0'), style={'button_color': '#e3f2fd'})
                def _remove(b, name=s):
                    self.chk_dict[name].value = False
                    self._refresh_samples_panes()
                btn.on_click(_remove)
                selected_widgets.append(btn)
        
        self.selected_samples_container.children = selected_widgets

    def _build_extraction_matrix(self):
        """Constrói a matriz dinâmica baseada no que existe no GCS."""
        L = widgets.Layout
        from M_cache import CacheManager
        self.state = CacheManager.load() or {}
        
        # Obtém o estado atual do cache
        gcs_data = self.state.get('gcs_chunks', {}) # Chave: nome_base, Valor: lista_bandas
        
        # Agrupa por sensor e mosaico
        available_combos = {}
        for m_name, bands in gcs_data.items():
            # Ex: image_peru_fire_sentinel2_minnbr_buffer_2026_03
            # Ex: image_peru_fire_sentinel2_minnbr_2026_03
            parts = m_name.split('_')
            if len(parts) >= 6:
                sensor = parts[3]
                # Pega do índice 4 até o penúltimo antes da data (YYYY_MM)
                # No caso de 2026_03, a data ocupa dois slots
                if parts[-2].isdigit() and len(parts[-2]) == 4: # Formato YYYY_MM
                    mosaic = "_".join(parts[4:-2])
                else: # Formato YYYY
                    mosaic = "_".join(parts[4:-1])
                
                combo = (sensor, mosaic)
                if combo not in available_combos:
                    available_combos[combo] = set()
                for b in bands: available_combos[combo].add(b)
        
        if not available_combos:
            return widgets.HTML('<div style="padding:20px; color:#999;"><i>Nenhum dado encontrado no GCS. Sincronize os dados no M1 ou M2 primeiro.</i></div>')

        # Ordem sugerida (Espectral) - Opcional e flexível
        BANDS_PRIORITY = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']
        
        self.band_chk_map = {} # (sensor, mosaic, band) -> checkbox
        matrix_rows = []
        
        for (s, m), bands in sorted(available_combos.items()):
            label_text = f"{s.upper()} {m.replace('_', ' ').title()}"
            label_html = widgets.HTML(f'<div style="width:200px; font-weight:bold; color:#333; font-size:12px;">{label_text}</div>')
            
            # Ordenação inteligente: prioridade primeiro, o resto alfabético no fim
            sorted_bands = sorted(list(bands), key=lambda x: BANDS_PRIORITY.index(x) if x in BANDS_PRIORITY else 999 + ord(x[0]))
            
            band_widgets = []
            for b in sorted_bands:
                chk = widgets.Checkbox(value=False, indent=False, layout=L(width='18px', height='18px', margin='0'))
                self.band_chk_map[(s, m, b)] = chk
                
                # Célula de status onde o texto é o nome da banda
                # Usamos mfm-ok (verde) quando selecionado, mfm-null quando não
                status_cell = PipelineStepUI.make_status_cell(chk, b.upper(), 'mfm-ok', width='90px')
                band_widgets.append(status_cell)
                
            row = widgets.HBox([label_html] + band_widgets, layout=L(align_items='center', padding='5px 0', border_bottom='1px solid #eee'))
            matrix_rows.append(row)
            
        return widgets.VBox(matrix_rows, layout=L(
            border='1px solid #dee2e6', padding='10px', margin='10px 0',
            background_color='#fff', border_radius='4px', max_height='400px', overflow_y='auto'
        ))

    def _build_hp_section(self):
        L = widgets.Layout
        self.w_iters = widgets.Text(value="7000", description='Iteraciones:', style={'description_width': '150px'}, layout=L(width='350px'))
        self.w_batch = widgets.Text(value="1000", description='Tamaño de Lote:', style={'description_width': '150px'}, layout=L(width='350px'))
        self.w_lr = widgets.Text(value="0.001", description='Tasa de Aprendizaje:', style={'description_width': '150px'}, layout=L(width='350px'))
        self.w_layers = widgets.Text(value="7, 14, 7", description='Capas Ocultas:', style={'description_width': '150px'}, layout=L(width='350px'))
        
        return widgets.VBox([
            widgets.HTML("<b style='font-size:14px; color:#2c3e50;'>⚙️ Hiperparámetros (DNN)</b>"),
            widgets.HBox([self.w_iters, self.w_batch], layout=L(gap='10px')),
            widgets.HBox([self.w_lr, self.w_layers], layout=L(gap='10px')),
        ], layout=L(padding='15px', border='1px solid #eee', border_radius='8px', margin='0 0 15px 0', flex='1'))

    def _suggest_next_id(self):
        """Sugere o MENOR ID de treino (001, 002...) disponível (preenchendo lacunas)."""
        models = list_trained_models()
        used_ids = set()
        import re
        for m in models:
            match = re.search(r'training_(\d{3})', m['training_id'])
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
        self.w_comment = widgets.Textarea(placeholder='Comentários...', layout=L(width='98%', height='60px'))
        
        return widgets.VBox([
            widgets.HTML("<b style='font-size:14px; color:#2c3e50;'>Destino de los Resultados</b>"),
            widgets.HBox([self.w_training_id, self.w_shortname], layout=L(gap='15px')),
            self.w_comment,
        ], layout=L(padding='15px', border='1px solid #eee', border_radius='8px', margin='0 0 15px 0'))

    def _refresh_ui(self):
        self._refresh_models_list(show_loader=True)
        

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

    def _refresh_models_list(self, show_loader=False):
        if show_loader: self.show_loader("Actualizando Ranking...")
        models = list_trained_models()
        fs = _get_fs()
        
        self.model_chk_map = {} 
        ranking_data = []
        for m in models:
            try:
                with fs.open(f"{m['path']}/metadata.json", 'r') as f: hp = json.load(f)
                with fs.open(f"{m['path']}/metrics.json", 'r') as f: met = json.load(f)
                crep = met.get('classification_report', {})
                f_met = crep.get('1', {}) 
                ranking_data.append({
                    'id': m['training_id'], 'short': hp.get('shortname', 'N/A'),
                    'sensor': hp.get('sensor', 'N/A').replace('sentinel2','S2').replace('landsat8','L8').upper(),
                    'acc': crep.get('accuracy', 0), 'prec': f_met.get('precision', 0), 'rec': f_met.get('recall', 0), 'f1': f_met.get('f1-score', 0),
                    'auto_rating': met.get('auto_rating', 0), 'human_rating': hp.get('rating', 0),
                    'path': m['path'], 'info': m
                })
                # Sync all models to canvas history for repo-wide search
                self.canvas_history[m['training_id']] = m
            except: continue
            
        if self.search_query_models:
            q = self.search_query_models.lower()
            ranking_data = [r for r in ranking_data if q in r['id'].lower() or q in r['short'].lower()]
            
        ranking_data.sort(key=lambda x: x[self.sort_column], reverse=not self.sort_ascending)
        if show_loader: self.hide_loader()

        # --- TOOLBAR ---
        txt_search = widgets.Text(value=self.search_query_models, placeholder='🔍 Buscar...', layout=widgets.Layout(width='300px'))
        txt_search.observe(self._on_search_models_change, names='value')
        btn_refresh = widgets.Button(description="Actualizar base", icon='refresh', layout=widgets.Layout(width='180px'), button_style='success')
        btn_refresh.on_click(lambda _: self._refresh_models_list(show_loader=True))
        toolbar = widgets.HBox([txt_search, btn_refresh], layout=widgets.Layout(margin='0 0 15px 0', align_items='center', gap='15px'))

        # LARGURAS (Optimizado para evitar scrollbars)
        W = {'pos': '40px', 'id': '180px', 'met': '50px', 'sep': '10px', 'stars': '90px', 'del': '150px'}

        def make_sort_head(label, key, width):
            icon = 'sort-desc' if self.sort_column == key and not self.sort_ascending else \
                   'sort-asc' if self.sort_column == key and self.sort_ascending else 'sort'
            btn = widgets.Button(description=label, icon=icon, layout=widgets.Layout(width=width, height='30px', margin='0', padding='0'))
            btn.style.button_color = '#f8f9fa'
            btn.style.font_weight = 'bold'
            btn.style.text_color = '#2c3e50'
            def _on_click(_):
                if self.sort_column == key: self.sort_ascending = not self.sort_ascending
                else: self.sort_column = key; self.sort_ascending = False
                self._refresh_models_list()
            btn.on_click(_on_click)
            return btn

        header = widgets.HBox([
            widgets.HTML("<div style='width:35px;'></div>"), 
            widgets.HTML(f"<div style='width:{W['pos']}; color:#2c3e50; font-weight:bold; text-align:center;'>#</div>"),
            make_sort_head("ID", "id", W['id']),
            make_sort_head("ACC", "acc", W['met']),
            make_sort_head("PRE", "prec", W['met']),
            make_sort_head("REC", "rec", W['met']),
            make_sort_head("F1", "f1", W['met']),
            widgets.HTML(f"<div style='width:{W['sep']}; border-right:1px solid #dee2e6; height:20px;'></div>"),
            make_sort_head("IA", "auto_rating", W['stars']),
            make_sort_head("IH", "human_rating", W['stars']),
            widgets.HTML(f"<div style='width:{W['del']}; color:#2c3e50; font-weight:bold; text-align:center;'>ACCIONES</div>"),
        ], layout=widgets.Layout(background='#ffffff', padding='8px', border_bottom='2px solid #dee2e6', border_radius='8px 8px 0 0', align_items='center'))

        final_rows = []
        for i, r in enumerate(ranking_data):
            medal = "🥇" if i == 0 and not self.sort_ascending and self.sort_column in ['acc','f1'] else f"#{i+1}"
            
            def make_star_row(val, color, is_human=False):
                btns_container = widgets.HBox([], layout=widgets.Layout(width=W['stars'], justify_content='center'))
                
                def _show_stars_row():
                    btns = []
                    for s_idx in range(1, 6):
                        char = "★" if s_idx <= val else "☆"
                        b = widgets.Button(description=char, layout=widgets.Layout(width='18px', height='20px', margin='0', padding='0'))
                        b.style.button_color = color if s_idx <= val else '#fff'
                        if is_human:
                            def _on_click_star(btn, v=s_idx):
                                # Mostrar confirmação compacta
                                btn_b = widgets.Button(description="<", layout=widgets.Layout(width='20px', height='20px', padding='0'), button_style='info')
                                btn_o = widgets.Button(description="OK", layout=widgets.Layout(width='30px', height='20px', padding='0'), button_style='success')
                                def _ok(_):
                                    btns_container.children = [self.make_spinner("Votando...")]
                                    if ModelTrainer.update_model_metadata(r['id'], r['short'], {'rating': v}): 
                                        self._refresh_models_list()
                                    else:
                                        _show_stars_row()
                                def _back(_): _show_stars_row()
                                btn_b.on_click(_back); btn_o.on_click(_ok)
                                btns_container.children = [btn_b, btn_o]
                            b.on_click(_on_click_star)
                        btns.append(b)
                    btns_container.children = btns
                
                _show_stars_row()
                return btns_container

            # --- GRUPO DE ACCIONES ESTABLE ---
            btn_mirar = widgets.Button(description='Mirar', layout=widgets.Layout(width='60px', height='30px'), button_style='primary', tooltip="Mirar en Canvas")
            btn_trash = widgets.Button(description='Deletar', layout=widgets.Layout(width='70px', height='30px'), button_style='danger')
            
            action_box = widgets.HBox([btn_mirar, btn_trash], layout=widgets.Layout(width=W['del'], justify_content='center', gap='5px'))
            
            def _on_mirar(_, info=r['info'], rid=r['id']):
                self.selected_models = {rid: info}
                self.canvas_history[rid] = info
                self.tab.selected_index = 2
                self._update_canvas()
            btn_mirar.on_click(_on_mirar)

            def _on_del_confirm(_, rid=r['id'], rs=r['short'], abox=action_box, btrash=btn_trash, bmirar=btn_mirar):
                btn_back = widgets.Button(description="<-", layout=widgets.Layout(width='35px', height='30px'), button_style='info')
                btn_real_del = widgets.Button(description="Borrar", layout=widgets.Layout(width='65px', height='30px'), button_style='warning')
                conf_box = widgets.HBox([btn_back, btn_real_del], layout=widgets.Layout(align_items='center', gap='2px'))
                
                def _do_back(_): abox.children = [bmirar, btrash]
                def _do_del(_):
                    abox.children = [self.make_spinner("Borrando...")]
                    ModelTrainer.delete_model(rid, rs)
                    self.selected_models.pop(rid, None)
                    self.canvas_history.pop(rid, None)
                    self._refresh_models_list(show_loader=True); self._update_canvas()
                    
                btn_back.on_click(_do_back); btn_real_del.on_click(_do_del)
                abox.children = [conf_box]
                
            btn_trash.on_click(_on_del_confirm)

            row = widgets.HBox([
                widgets.HTML(f"<div style='width:{W['pos']}; text-align:center; font-weight:bold;'>{medal}</div>"),
                widgets.HTML(f"<div style='width:{W['id']}; overflow:hidden; font-size:11px;'><b>{r['id']}</b><br><span style='color:#666;'>{r['short']}</span></div>"),
                widgets.HTML(f"<div style='width:{W['met']}; text-align:center; font-weight:bold; color:#2c3e50;'>{r['acc']:.1%}</div>"),
                widgets.HTML(f"<div style='width:{W['met']}; text-align:center; color:#666;'>{r['prec']:.1%}</div>"),
                widgets.HTML(f"<div style='width:{W['met']}; text-align:center; color:#666;'>{r['rec']:.1%}</div>"),
                widgets.HTML(f"<div style='width:{W['met']}; text-align:center; font-weight:bold; color:#28a745;'>{r['f1']:.1%}</div>"),
                widgets.HTML(f"<div style='width:{W['sep']}; border-right:1px solid #ddd; height:20px;'></div>"),
                make_star_row(r['auto_rating'], '#bdc3c7'),
                make_star_row(r['human_rating'], '#f1c40f', True),
                action_box
            ], layout=widgets.Layout(padding='5px', border_bottom='1px solid #eee', align_items='center', overflow='hidden', background='#fff' if i%2==0 else '#f9f9f9'))
            final_rows.append(row)

        self.analytics_area.children = [toolbar, widgets.VBox([header, widgets.VBox(final_rows, layout=widgets.Layout(border='1px solid #dee2e6', border_radius='0 0 8px 8px', max_height='450px', overflow_y='auto'))])]
        self._refresh_canvas_hub()

    def _update_canvas_live(self, history, embeds, preds, y_true, samples, b_cfg):
        # Inicializa a estrutura estável se necessário
        if not hasattr(self, '_live_initialized') or not self._live_initialized:
            self.canvas_output.clear_output()
            with self.canvas_output:
                display(HTML("<h2 style='color:#2c3e50; border-bottom:3px solid #3498db; padding-bottom:5px; margin-bottom:15px;'>🚀 Entrenamiento en Vivo</h2>"))
                display(self._build_viz_toolbar())
                display(self._live_plots_out)
            self._live_initialized = True

        self._live_plots_out.clear_output(wait=True)
        with self._live_plots_out:
            # 1. HEADER DO TREINO ATUAL (Metadados Live)
            from sklearn.metrics import classification_report
            try:
                rep = classification_report(y_true, (preds > 0.5).astype(int), output_dict=True, zero_division=0)
            except: rep = {}
            
            hp_live = {
                'training_id': self.w_training_id.value, 'shortname': self.w_shortname.value,
                'sample_collections': samples, 'bands_input': sorted(b_cfg.keys()),
                'layers': self.w_layers.value, 'lr': self.w_lr.value,
                'sample_count': self.trainer_instance._sample_count, 'comment': self.w_comment.value,
                'training_date': '🚀 Entrenamiento en curso...'
            }
            
            if self.viz_config.get('title'): 
                display(HTML(render_model_card_html(hp_live, {'classification_report': rep})))
            
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

    def _refresh_canvas_hub(self):
        """Redesenha as listas de modelos disponíveis e selecionados no Canvas."""
        # 1. Disponíveis (Filtrados)
        available = []
        q = self.canvas_search_query.lower()
        for rid, info in self.canvas_history.items():
            if rid in self.selected_models: continue
            if q and q not in rid.lower() and q not in info.get('shortname','').lower(): continue
            
            sname = info.get('shortname','')
            lbl = f"➕ {rid} ({sname})" if sname else f"➕ {rid}"
            
            btn = widgets.Button(
                description=lbl,
                layout=widgets.Layout(width='100%', min_height='28px', margin='1px 0'),
                style={'button_color': '#f8f9fa'}
            )
            def _add(b, r=rid, i=info):
                self.selected_models[r] = i
                self._refresh_canvas_hub(); self._update_canvas()
            btn.on_click(_add)
            available.append(btn)
        self.canvas_available_box.children = available
        
        # 2. Selecionados
        selected = []
        for rid, info in self.selected_models.items():
            sname = info.get('shortname','')
            lbl = f"❌ {rid} ({sname})" if sname else f"❌ {rid}"
            
            btn = widgets.Button(
                description=lbl,
                layout=widgets.Layout(width='100%', min_height='28px', margin='1px 0'),
                style={'button_color': '#e3f2fd'}
            )
            def _rem(b, r=rid):
                self.selected_models.pop(r, None)
                self._refresh_canvas_hub(); self._update_canvas()
            btn.on_click(_rem)
            selected.append(btn)
        self.canvas_selected_box.children = selected

    def _build_viz_toolbar(self):
        L = widgets.Layout
        labels = {
            'title': 'Metadatos', 'scores': 'KPIs', 'cm': 'Confusion', 
            'history': 'Historial', 'prob': 'Prob', 'pr': 'PR-Curve', 
            'pca2d': 'PCA 2D', 'pca3d': 'PCA 3D', 'tsne3d': 't-SNE 3D'
        }
        chks = []
        for key, label in labels.items():
            cb = widgets.Checkbox(value=self.viz_config[key], description=label, layout=L(width='auto', margin='0 8px 0 0'))
            def _on_change(change, k=key):
                self.viz_config[k] = change['new']
                self._update_canvas()
            cb.observe(_on_change, names='value')
            chks.append(cb)
        
        return widgets.HBox([widgets.HTML("<b style='margin-right:10px;'>Ver:</b>")] + chks, 
                           layout=L(margin='10px 0', padding='10px', background_color='#f8f9fa', border_radius='5px', align_items='center'))

    def _update_canvas(self):
        # Sincroniza o hub antes de renderizar
        self._refresh_canvas_hub()
        self.canvas_output.clear_output(wait=True)
        with self.canvas_output:
            if not self.selected_models and not self.trainer_instance:
                display(HTML("<div style='padding:100px; text-align:center; background:white;'> <span style='font-size:50px;'>🎨</span><br><h3 style='color:#999;'>El Canvas está vacío</h3><p style='color:#ccc;'>Seleccione modelos en <b>Trenamientos</b> para visualizarlos aquí.</p></div>"))
                return
            
            # Toolbar de Visibilidade
            display(self._build_viz_toolbar())
            
            # Modelos Selecionados do Ranking
            for mid, info in self.selected_models.items():
                view_analytics(info, out_widget=None, clear_before=False, viz_config=self.viz_config)
                display(HTML("<div style='margin:40px 0; border-top:1px dashed #ccc;'></div>"))

    def _on_view_batch_logic(self, ranking_data):
        """Visualiza una comparación de los modelos seleccionados."""
        selected = [r['info'] for r in ranking_data if self.model_chk_map[r['id']].value]
        if not selected:
            return
        self.canvas_output.clear_output()
        with self.canvas_output:
            display(HTML(f"<h3 style='color:#007bff;'>📂 Comparativa ({len(selected)} modelos)</h3>"))
            for info in selected:
                view_analytics(info, out_widget=None, clear_before=False, viz_config=self.viz_config)
def start_training(ui):
    # -----------------------------------------------------------------
    # 1️⃣ Retraining intent (checked via the UI state)
    # -----------------------------------------------------------------
    intent = ui.retrain_intent
    if intent.get('mode'):
        hp = intent.get('hp')
        
        # Determine training ID and shortname for the target model
        # If hp is provided (from Canvas/Ranking), use it. Otherwise use widgets.
        target_id = hp['training_id'] if hp else ui.w_training_id.value
        target_short = hp['shortname'] if hp else ui.w_shortname.value
        
        # If 'borrar' mode is selected, delete the target model first.
        if intent['mode'] == 'borrar':
            print(f"🗑️ Borrando modelo previo: {target_id} ({target_short})")
            ModelTrainer.delete_model(target_id, target_short)
            
        # If hp is provided, load its full configuration into the widgets.
        if hp:
            ui._load_config_into_widgets(hp)
            selected_samples = hp.get('sample_collections', [])
            # Also extract other HPs if needed (though start_training reads widgets below)
            
        print(f"🔄 Modo '{intent['mode']}' activado para {target_id}")
        
        # Reset the intent so it does not fire again accidentally.
        ui.retrain_intent = {'mode': None, 'hp': None}
        # Reset the checkboxes visually too
        for cb in [ui.cb_retrain, ui.cb_reextract, ui.cb_borrar_retrain]:
            cb.unobserve(ui._on_intent_cb_change, names='value')
            cb.value = False
            cb.observe(ui._on_intent_cb_change, names='value')
            
        # Continue to training...
    
    # 2️⃣ Get parameters from UI (always up-to-date after intent load or manual edit)
    if not intent.get('mode') or not hp:
        selected_samples = [name for name, chk in ui.chk_dict.items() if chk.value]

    if not selected_samples:
        print("Error: Ninguna muestra seleccionada.")
        return
        
    ui.tab.selected_index = 3 # Muda para a aba "Canvas"
    ui._live_initialized = False # Reseta para reconstruir a estrutura estável
    ui.canvas_output.clear_output()
    
    # Constrói o dicionário de configuração de bandas a partir da nova Matriz Premium
    bands_config = {}
    for (s, m, b), chk in ui.band_chk_map.items():
        if chk.value:
            bands_config[b] = {'sensor': s, 'mosaic': m}
            
    if not bands_config:
        print("Error: Ninguna banda seleccionada en la Matriz de Extracción.")
        return

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
    
    # Mudar para aba Canvas (Índice 2)
    ui.tab.selected_index = 2
    
    # Snapshot Directory
    m_id = ui.w_training_id.value
    m_short = ui.w_shortname.value
    snap_dir = f"library_images/models/{m_id}_{m_short}"
    os.makedirs(snap_dir, exist_ok=True)

    def update_chart(history, embeds=None, preds=None, y_true=None):
        with ui.canvas_output:
            ui._update_canvas_live(history, embeds, preds, y_true, selected_samples, bands_config)

    # Iniciar Treino
    ui.trainer_instance.train(X_train, y_train, X_val=X_val, y_val=y_val, 
                              batch_size=batch, n_iters=iters, logger=_logger, 
                              update_chart_fn=update_chart, snapshot_dir=snap_dir)
    
    # --- AUDITORIA FINAL COM t-SNE (INTERATIVO) ---
    print("\n🏁 Entrenamiento completado. Generando auditoría t-SNE final de alta resolución...")
    with ui.canvas_output:
        import plotly.graph_objects as go
        from sklearn.manifold import TSNE
        try:
            display(HTML("<h4 style='color:#2c3e50; margin-top:20px; font-weight:bold;'>🚀 Auditoría t-SNE (Espacio Latente Final)</h4>"))
            display(HTML("<p style='font-size:11px; color:#666;'>Calculando proyección no-lineal para mejor visualización de clústeres...</p>"))
            
            idx_v = np.random.choice(len(X_val), min(600, len(X_val)), replace=False)
            X_v_sub = X_val[idx_v]
            y_v_sub = y_val[idx_v]
            
            emb_v = ui.trainer_instance.get_embeddings(X_v_sub)
            prd_v = ui.trainer_instance.predict(X_v_sub)
            
            print("  - Calculando manifold t-SNE (esto puede tardar)...")
            tsne = TSNE(n_components=3, perplexity=30, random_state=42, max_iter=1000)
            coords_tsne = tsne.fit_transform(emb_v)
            
            # SALVAR SNAPSHOT NO TRAINER PARA O SAVE()
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
            # Injeção pesada (include_plotlyjs=True) para máxima compatibilidade
            display(HTML(fig_tsne.to_html(include_plotlyjs=True, full_html=False)))
            print("✅ Auditoría t-SNE lista.")
        except Exception as e:
            print(f"⚠️ No se pudo gerar t-SNE final: {e}")

    print("Guardando estructura (muestras, píxeles, metadatos, métricas) en GCS...")
    try:
        ui.trainer_instance.save(ui.w_training_id.value, ui.w_shortname.value, comment=ui.w_comment.value, logger=_logger)
        print("¡Modelo y Model Card guardados exitosamente!")
        
        # Carregar o Model Card automaticamente no dashboard inferior
        model_info = {
            'training_id': f"training_{ui.w_training_id.value}_{ui.w_shortname.value}_{GLOBAL_OPTS['SENSOR'].lower()}", 
            'path': model_path(ui.w_training_id.value, ui.w_shortname.value)
        }
        view_analytics(model_info, out_widget=ui.analytics_dashboard_output)
        
    except Exception as e:
        print(f"Error al guardar: {e}")
        
    ui._refresh_models_list()

def run_ui():
    ui = ModelTrainerUI()
    ui.display()
    return ui
