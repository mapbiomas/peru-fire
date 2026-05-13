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

    def train(self, X, y, batch_size=None, n_iters=None, split=None, keep_prob=0.8, logger=None, update_chart_fn=None):
        self._X_raw = X
        self._y_raw = y
        
        batch_size = batch_size or CONFIG.get('model_batch', 1000)
        n_iters    = n_iters    or CONFIG.get('model_iters', 5000)
        split      = split      or CONFIG.get('model_split', 0.8)

        self.norm_stats = compute_normalizer(X)
        X_norm = normalize(X, self.norm_stats)

        n = len(X_norm)
        idx = np.random.permutation(n)
        n_train = int(n * split)
        
        X_tr, y_tr = X_norm[idx[:n_train]], y[idx[:n_train]].reshape(-1, 1)
        X_te, y_te = X_norm[idx[n_train:]], y[idx[n_train:]].reshape(-1, 1)

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

            self._saved_vars = {v.name: sess.run(v) for v in tf.global_variables()}
            self._history = history

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
        preds = (1 / (1 + np.exp(-logits))).flatten() > 0.5
        
        cm = confusion_matrix(self._y_raw, preds)
        rep = classification_report(self._y_raw, preds, output_dict=True)
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
            
    def predict_array(self, X_raw):
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
        preds = (1 / (1 + np.exp(-logits))).flatten() > 0.5
        return preds.astype(np.uint8)

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
            for fname in ['vectors.tsv', 'metadata.tsv']:
                src = os.path.join(tmpdir, fname)
                dest = gcs_path(f"{dest_dir}/{fname}")
                if logger: logger(f"  📤 Subiendo {fname} a GCS...", "info")
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
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
                'num_input':    self.num_input,
                'layers':       self.layers,
                'lr':           self.lr,
                'training_date': datetime.now().isoformat(),
                'norm_stats':   {str(k): list(v) for k, v in self.norm_stats.items()},
                'history':      self._history,
                'sample_collections': getattr(self, '_sample_collections', []),
                'sample_count': getattr(self, '_sample_count', {}),
                'comment':      comment,
            }
            with open(os.path.join(tmpdir, 'metadata.json'), 'w') as f:
                json.dump(hp, f, indent=2)

            for fname in ['weights.npz', 'metadata.json']:
                src  = os.path.join(tmpdir, fname)
                dest = gcs_path(f"{base_path}/{fname}")
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2.5 Metrics
            if logger: logger("Generación y guardado de métricas de evaluación...", "info")
            cm, rep = self.evaluate()
            metrics = {
                'confusion_matrix': cm.tolist(),
                'classification_report': rep,
                'generated_at': datetime.now().isoformat()
            }
            with open(os.path.join(tmpdir, 'metrics.json'), 'w') as f:
                json.dump(metrics, f, indent=2)
            subprocess.run(['gsutil', 'cp', os.path.join(tmpdir, 'metrics.json'), gcs_path(f"{base_path}/metrics.json")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Extracted Pixels
            if logger: logger("Guardar una matriz de píxeles en GCS...", "info")
            np.save(os.path.join(tmpdir, 'X_data.npy'), self._X_raw)
            np.save(os.path.join(tmpdir, 'y_data.npy'), self._y_raw)
            
            for fname in ['X_data.npy', 'y_data.npy']:
                src  = os.path.join(tmpdir, fname)
                dest = gcs_path(f"{base_path}/extracted_pixels/{fname}")
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        # 4. Copy samples
        if logger: logger("Copiar archivos CSV de las muestras para su almacenamiento...", "info")
        collections = getattr(self, '_sample_collections', [])
        for coll in collections:
            src = gcs_path(f"{CONFIG['gcs_library_samples']}/{coll}.csv")
            dest = gcs_path(f"{base_path}/samples/{coll}.csv")
            subprocess.run(['gsutil', 'cp', src, dest], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return hp


# ─── INTERFAZ PREMIUM ─────────────────────────────────────────────────────────

def view_analytics(model_info, out_widget=None):
    import gcsfs, tempfile, subprocess
    import matplotlib.pyplot as plt
    from IPython.display import display, HTML
    
    fs = _get_fs()
    base_gs = f"gs://{model_info['path']}"
    
    if out_widget:
        out_widget.clear_output(wait=True)
        with out_widget:
            print(f"Carregando Dashboard para: {model_info['training_id']}...")
            
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ['metadata.json', 'metrics.json']:
            src = f"{base_gs}/{fname}"
            dest = os.path.join(tmpdir, fname)
            try:
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                if out_widget:
                    with out_widget: print(f"Error: No se encontró el archivo {fname}. Vuelve a entrenar el modelo.")
                return
                
        with open(os.path.join(tmpdir, 'metadata.json')) as f:
            hp = json.load(f)
        with open(os.path.join(tmpdir, 'metrics.json')) as f:
            metrics = json.load(f)
            
        cm = np.array(metrics['confusion_matrix'])
        rep = metrics['classification_report']
        
def render_model_card_html(hp, metrics):
    """Gera o HTML do header e KPIs do Model Card."""
    # Cores e estilos
    style = """
    <style>
    .dash-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .dash-title { font-size: 18px; font-weight: bold; color: #343a40; margin-bottom: 10px; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
    .dash-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
    .kpi-box { background: #fff; padding: 10px; border-left: 4px solid #007bff; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .kpi-title { font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 20px; font-weight: bold; color: #212529; }
    .meta-text { font-size: 13px; color: #495057; margin: 2px 0; }
    </style>
    """
    
    # Preparando métricas
    rep = metrics.get('classification_report', {})
    acc = rep.get('accuracy', 0)
    f1_fire = rep.get('1', {}).get('f1-score', 0)
    prec_fire = rep.get('1', {}).get('precision', 0)
    rec_fire = rep.get('1', {}).get('recall', 0)
    
    # Formatando data
    date_str = hp.get('training_date', 'Entrenando...')
    if date_str and 'T' in date_str: date_str = date_str[:16].replace('T', ' ')
    
    html_content = f"""
    {style}
    <div class="dash-card">
        <div class="dash-title">📄 Ficha del modelo: {hp.get('training_id')} / {hp.get('shortname')}</div>
        <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 15px;">
            <div style="flex: 2; min-width: 300px;">
                <p class="meta-text"><b>Estado/Fecha:</b> {date_str}</p>
                <p class="meta-text"><b>Muestras:</b> {', '.join(hp.get('sample_collections', []))}</p>
                <p class="meta-text"><b>Bandas:</b> {', '.join(hp.get('bands_input', []))}</p>
                <p class="meta-text"><b>Capas:</b> {hp.get('layers')} | <b>LR:</b> {hp.get('lr')}</p>
                <p class="meta-text"><b>Píxeles:</b> {hp.get('sample_count', {}).get('burned', 0)} (F) | {hp.get('sample_count', {}).get('not_burned', 0)} (NF)</p>
            </div>
            <div style="flex: 1; min-width: 250px; background:#fff3cd; padding:10px; border-radius:4px; border:1px solid #ffeeba;">
                <p class="meta-text" style="color:#856404; font-weight:bold; margin-bottom:5px;">📝 Comentario:</p>
                <p class="meta-text" style="color:#856404; font-style:italic;">{hp.get('comment', 'Sin comentarios.')}</p>
            </div>
        </div>
        
        <div class="dash-grid">
            <div class="kpi-box" style="border-left-color: #28a745;">
                <div class="kpi-title">Acurácia Global</div>
                <div class="kpi-value">{acc:.1%}</div>
            </div>
            <div class="kpi-box" style="border-left-color: #dc3545;">
                <div class="kpi-title">Precisión (Fuego)</div>
                <div class="kpi-value">{prec_fire:.1%}</div>
            </div>
            <div class="kpi-box" style="border-left-color: #ffc107;">
                <div class="kpi-title">Recall (Fuego)</div>
                <div class="kpi-value">{rec_fire:.1%}</div>
            </div>
            <div class="kpi-box" style="border-left-color: #17a2b8;">
                <div class="kpi-title">F1-Score (Fuego)</div>
                <div class="kpi-value">{f1_fire:.1%}</div>
            </div>
        </div>
    </div>
    """
    return html_content

def view_analytics(model_info, out_widget=None):
    """Visualiza as métricas e o card de um modelo salvo no GCS."""
    fs = _get_fs()
    try:
        # 1. Carregar dados do GCS
        with fs.open(f"{model_info['path']}/hyperparameters.json", 'r') as f:
            hp = json.load(f)
        with fs.open(f"{model_info['path']}/metrics.json", 'r') as f:
            metrics = json.load(f)
        
        cm = np.array(metrics.get('confusion_matrix', [[0,0],[0,0]]))
        rep = metrics.get('classification_report', {})
        history = hp.get('history', {})

        if out_widget:
            out_widget.clear_output(wait=True)
            with out_widget:
                # Renderizar Header HTML
                display(HTML(render_model_card_html(hp, metrics)))
                
                # --- DASHBOARD DE DIAGNÓSTICO (2x3 Grid) ---
                fig = plt.figure(figsize=(18, 9))
                
                # 1. Matriz de Confusión (Normalizada %)
                ax1 = fig.add_subplot(2, 3, 1)
                cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
                ax1.matshow(cm_norm, cmap='Blues', alpha=0.8, vmin=0, vmax=1)
                for (i, j), z in np.ndenumerate(cm):
                    ax1.text(j, i, f"{z:,}\n({cm_norm[i,j]:.1%})", ha='center', va='center', 
                             weight='bold', color='black' if cm_norm[i,j] < 0.5 else 'white')
                ax1.set_title('Matriz de Confusión (%)', pad=15, weight='bold')
                ax1.set_xticks([0, 1]); ax1.set_yticks([0, 1])
                ax1.set_xticklabels(['No-fuego', 'Fuego']); ax1.set_yticklabels(['No-fuego', 'Fuego'])

                # 2. Historial de Entrenamiento (Loss & Acc)
                if history and 'steps' in history:
                    ax2 = fig.add_subplot(2, 3, 2)
                    ax2.plot(history['steps'], history['acc'], color='#28a745', label='Acc Treino', linewidth=2)
                    ax2.plot(history['steps'], history['val_acc'], color='#28a745', label='Acc Validação', linestyle='--', alpha=0.6)
                    ax2.set_ylabel('Acurácia', color='#28a745', weight='bold')
                    ax2b = ax2.twinx()
                    ax2b.plot(history['steps'], history['loss'], color='#dc3545', label='Loss', linewidth=1.5, alpha=0.7)
                    ax2b.set_ylabel('Custo (Loss)', color='#dc3545', weight='bold')
                    ax2.set_title('Evolución Histórica', weight='bold')
                    ax2.grid(True, linestyle='--', alpha=0.3)

                # 3. Placeholder PCA 2D
                ax3 = fig.add_subplot(2, 3, 3)
                ax3.text(0.5, 0.5, "PCA 2D disponible en Live", ha='center', va='center', color='#999')
                ax3.set_title('Proyección Latente 2D', weight='bold')

                # 4. Placeholder Distribución
                ax4 = fig.add_subplot(2, 3, 4)
                ax4.text(0.5, 0.5, "Histograma disponible en Live", ha='center', va='center', color='#999')
                ax4.set_title('Distribución de Probabilidades', weight='bold')

                # 5. Placeholder Precision-Recall
                ax5 = fig.add_subplot(2, 3, 5)
                ax5.text(0.5, 0.5, "Curva PR disponible en Live", ha='center', va='center', color='#999')
                ax5.set_title('Curva Precision-Recall', weight='bold')

                # 6. Placeholder PCA 3D
                ax6 = fig.add_subplot(2, 3, 6, projection='3d')
                ax6.text(0.5, 0.5, 0.5, "PCA 3D en Projector", ha='center', va='center', color='#999')
                ax6.set_title('Espacio Latente 3D', weight='bold')

                plt.tight_layout()
                plt.show()

                # --- AUDITORIA INTERATIVA (PLOTLY 3D) ---
                display(HTML("<h4 style='margin-top:20px; color:#2c3e50; font-weight:bold;'>🔍 Auditoría del Espacio Latente (Interactivo)</h4>"))
                
                import plotly.graph_objects as go
                from sklearn.decomposition import PCA
                
                # Para o histórico, tentamos carregar os pesos e gerar o espaço latente de uma amostra
                try:
                    # Buscamos se existem pesos salvos para gerar o plot
                    weights_path = f"{model_info['path']}/weights.npz"
                    if fs.exists(weights_path):
                        with fs.open(weights_path, 'rb') as f:
                            weights = dict(np.load(f))
                        
                        # Criamos um trainer temporário para o forward pass
                        trainer_tmp = ModelTrainer(num_input=len(hp['bands_input']), layers=hp['layers'])
                        trainer_tmp._saved_vars = weights
                        trainer_tmp.norm_stats = {int(k): tuple(v) for k, v in hp['norm_stats'].items()}
                        
                        # Pegamos uma amostra sintética ou real para o plot (simplificado aqui com dados aleatórios se não houver X_data)
                        # No fluxo real, o ideal é ter o X_data salvo
                        X_sub = np.random.randn(500, len(hp['bands_input'])) 
                        embeds = trainer_tmp.get_embeddings(X_sub)
                        preds = trainer_tmp.predict(X_sub)
                        
                        pca = PCA(n_components=3)
                        coords = pca.fit_transform(embeds)
                        
                        fig_plotly = go.Figure(data=[go.Scatter3d(
                            x=coords[:,0], y=coords[:,1], z=coords[:,2],
                            mode='markers',
                            marker=dict(size=4, color=preds.flatten(), colorscale='RdBu_r', opacity=0.8, showscale=True),
                            text=[f"Confianza: {p:.2%}" for p in preds.flatten()]
                        )])
                        fig_plotly.update_layout(
                            title="Exploración 3D Navegable (PCA)",
                            margin=dict(l=0, r=0, b=0, t=30),
                            scene=dict(xaxis_title='PC1', yaxis_title='PC2', zaxis_title='PC3')
                        )
                        fig_plotly.show()
                except:
                    display(HTML("<p style='color:#666;'><i>Gráfico interactivo disponible al cargar pesos del modelo.</i></p>"))

                # Rodapé com instruções para Projector (t-SNE/UMAP)
                display(HTML(f"""
                <div style="background:#f8f9fa; border:1px solid #dee2e6; padding:15px; border-radius:8px; margin-top:15px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <b style="color:#2c3e50; font-size:14px;">🚀 Análisis Avanzado (t-SNE / UMAP)</b><br>
                            <span style="color:#7f8c8d; font-size:12px;">Para exploraciones pesadas de clusters, use el TensorBoard Projector.</span>
                        </div>
                        <a href="https://projector.tensorflow.org/" target="_blank" 
                           style="background:#007bff; color:white; padding:8px 16px; border-radius:4px; text-decoration:none; font-weight:bold;">
                           Abrir Projector
                        </a>
                    </div>
                </div>
                """))
    except Exception as e:
        if out_widget:
            with out_widget: print(f"❌ Erro ao carregar analíticos: {e}")




class ModelTrainerUI(PipelineStepUI):
    def __init__(self):
        super().__init__(
            title="M4 - Entrenador del Modelo (DNN)", 
            description="Interfaz Matricial de Muestras, entrenamiento de red neuronal y análisis postergados."
        )
        self.trainer_instance = None
        self.chk_dict = {}
        self.search_query_samples = ""
        self.main_area.children = [widgets.HTML("<i>Cargando interfaz...</i>")]

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
        self._refresh_matrix_only()

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
        
        # BARRA DE BUSCA
        self.txt_search_samples = widgets.Text(
            value=self.search_query_samples,
            placeholder='Buscar muestras (ex: r10)...',
            layout=L(width='300px')
        )
        self.txt_search_samples.observe(self._on_search_samples_change, names='value')

        btn_all = widgets.Button(description="Seleccionar filtradas", button_style='info', icon='check-square', layout=L(width='180px'))
        btn_none = widgets.Button(description="Borrar filtrados", button_style='warning', icon='square-o', layout=L(width='180px'))
        btn_refresh = widgets.Button(description="", button_style='success', icon='refresh', layout=L(width='40px'))
        
        btn_all.on_click(self._on_select_all_samples)
        btn_none.on_click(self._on_select_none_samples)
        btn_refresh.on_click(lambda _: self._refresh_ui())
        
        toolbar = widgets.HBox([self.txt_search_samples, btn_all, btn_none, btn_refresh], layout=L(margin='0 0 10px 0', gap='10px', align_items='center'))
        
        # Container persistente para a matriz
        self.matrix_container = widgets.VBox([self._build_matrix_content()], layout=L(
            border='1px solid #dee2e6', padding='10px', max_height='300px', overflow_y='auto'
        ))
        
        return widgets.VBox([css, toolbar, self.matrix_container])

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

    def _refresh_ui(self):
        self.show_loader("Actualizando lista de muestras...")
        self._build_ui()
        self.hide_loader()

    def _build_ui(self):
        L = widgets.Layout
        css_tags = widgets.HTML("<style>.widget-toggle-button { border-radius:12px !important; }</style>")
        
        # --- TAB 1: Configuración & Entrenamiento ---
        matrix_ui = self._build_matrix()
        extraction_matrix = self._build_extraction_matrix()
        
        self.w_iters = widgets.Text(value="7000", description='Iteraciones:', style={'description_width': '150px'}, layout=L(width='350px'))
        lbl_iters = widgets.HTML("<span style='color:#666; font-size:12px; margin-left:10px;'>Total de iteraciones de entrenamiento (Ej: 5000, 10000). Mayor = más entrenamiento.</span>")
        box_iters = widgets.HBox([self.w_iters, lbl_iters], layout=L(align_items='center', margin='5px 0'))
        
        self.w_batch = widgets.Text(value="1000", description='Tamaño de Lote:', style={'description_width': '150px'}, layout=L(width='350px'))
        lbl_batch = widgets.HTML("<span style='color:#666; font-size:12px; margin-left:10px;'>Píxeles por iteración (Ej: 500, 1000). Controla el uso de memoria.</span>")
        box_batch = widgets.HBox([self.w_batch, lbl_batch], layout=L(align_items='center', margin='5px 0'))
        
        self.w_lr = widgets.Text(value="0.001", description='Tasa de Aprendizaje:', style={'description_width': '150px'}, layout=L(width='350px'))
        lbl_lr = widgets.HTML("<span style='color:#666; font-size:12px; margin-left:10px;'>Learning rate (Ej: 0.001, 0.01). Controla la velocidad de ajuste.</span>")
        box_lr = widgets.HBox([self.w_lr, lbl_lr], layout=L(align_items='center', margin='5px 0'))
        
        self.w_layers = widgets.Text(value="7, 14, 7", description='Capas Ocultas:', style={'description_width': '150px'}, layout=L(width='350px'))
        lbl_layers = widgets.HTML("<span style='color:#666; font-size:12px; margin-left:10px;'>Neuronas por capa, separadas por coma (Ej: 14, 28, 14).</span>")
        box_layers = widgets.HBox([self.w_layers, lbl_layers], layout=L(align_items='center', margin='5px 0'))
        
        hp_box = widgets.VBox([box_iters, box_batch, box_lr, box_layers], layout=L(margin='10px 0'))
        
        self.w_training_id = widgets.Text(value='42', description='Training ID:', style={'description_width': '80px'})
        self.w_shortname = widgets.Text(value='peru_r1', description='Nombre Corto:', style={'description_width': '100px'})
        self.w_comment = widgets.Textarea(
            placeholder='Descreva aqui os detalhes de este treinamento...',
            description='Comentário:',
            style={'description_width': '100px'},
            layout=L(width='98%', height='80px')
        )
        
        tab_config = widgets.VBox([
            widgets.HTML("<b>1. Selección de muestras (matriz GCS)</b>"), matrix_ui,
            widgets.HTML("<br><b>2. Matriz de extracción (bandas por sensor + mosaico)</b>"), extraction_matrix,
            widgets.HTML("<b>3. Hiperparámetros (DNN)</b>"), hp_box,
            widgets.HTML("<hr style='margin:10px 0'>"),
            widgets.HTML("<b>4. Destino Final no GCS</b>"),
            widgets.HBox([self.w_training_id, self.w_shortname], layout=L(margin='10px 0')),
            self.w_comment
        ], layout=L(padding='15px'))
        
        # --- TAB 2: Monitorización en Vivo (Live) ---
        self.training_header_output = widgets.Output(layout=L(margin='0 0 10px 0'))
        self.training_chart_output = widgets.Output(layout=L(border='1px solid #dee2e6', border_radius='4px', padding='10px', min_height='250px'))
        
        tab_live = widgets.VBox([
            widgets.HTML("<b>📈 Entrenamiento Actual (En vivo)</b>"),
            widgets.HTML("<p style='font-size:11px;color:#666;margin-bottom:10px;'>Acompanhe o progresso do seu modelo e a separação dos clusters em tempo real.</p>"),
            self.training_header_output,
            self.training_chart_output,
        ], layout=L(padding='15px'))

        # --- TAB 3: Historial & Analytics ---
        self.analytics_dashboard_output = widgets.Output(layout=L(border='1px solid #dee2e6', border_radius='4px', padding='10px', min_height='300px', margin='10px 0', background_color='#fafafa'))
        self.analytics_area = widgets.VBox()
        self._refresh_models_list()
        
        tab_history = widgets.VBox([
            widgets.HTML("<b>📊 Ficha del modelo y panel de análisis</b>"),
            self.analytics_dashboard_output,
            widgets.HTML("<hr style='margin:15px 0'>"),
            widgets.HTML("<b>📂 Historial de Modelos</b>"),
            widgets.HTML("<p style='font-size:11px;color:#666;'>Consulte os Model Cards de treinamentos anteriores ou exporte para o TensorBoard Projector.</p>"),
            self.analytics_area
        ], layout=L(padding='15px'))
        
        self.tabs = widgets.Tab(children=[tab_config, tab_live, tab_history])
        self.tabs.set_title(0, '⚙️ Configuración')
        self.tabs.set_title(1, '📈 Monitorización Live')
        self.tabs.set_title(2, '📂 Historial & Analytics')
        
        self.clear_main()
        self.main_area.children = [css_tags, self.tabs]
        

    def _refresh_models_list(self, show_loader=False):
        if show_loader: self.show_loader("Actualizando lista de modelos...")
        models = list_trained_models()
        if show_loader: self.hide_loader()
        fs = _get_fs()
        
        items = []
        for m in models:
            has_metrics = fs.exists(f"{m['path']}/metrics.json")
            status = "✅ Completo" if has_metrics else "⚠️ Sin Métricas"
            btn = widgets.Button(
                description="Ver Model Card", 
                button_style='success' if has_metrics else 'warning', 
                icon='bar-chart',
                layout=widgets.Layout(width='150px')
            )
            
            btn_del = widgets.Button(
                description="", 
                button_style='danger', 
                icon='trash',
                layout=widgets.Layout(width='40px'),
                tooltip="Eliminar el Modelo permanentemente do GCS"
            )
            
            btn_proj = widgets.Button(
                description="Exportar Projector", 
                button_style='info', 
                icon='external-link',
                layout=widgets.Layout(width='160px'),
                tooltip="Gerar arquivos .tsv para o TensorBoard Projector"
            )
            
            def _make_callback(model_info):
                def callback(b):
                    view_analytics(model_info, out_widget=self.analytics_dashboard_output)
                return callback

            def _make_proj_callback(model_info):
                def callback(b):
                    self.show_loader("Generando archivos para Projector...")
                    try:
                        # Carregar o modelo e os dados
                        import tempfile, subprocess
                        fs = _get_fs()
                        with tempfile.TemporaryDirectory() as tmpdir:
                            # Precisamos de uma amostra de dados para gerar os embeddings
                            # Vamos baixar os píxeis que foram salvos com o modelo
                            X_file = os.path.join(tmpdir, 'X_data.npy')
                            y_file = os.path.join(tmpdir, 'y_data.npy')
                            src_x = f"gs://{model_info['path']}/extracted_pixels/X_data.npy"
                            src_y = f"gs://{model_info['path']}/extracted_pixels/y_data.npy"
                            
                            subprocess.run(['gsutil', 'cp', src_x, X_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            subprocess.run(['gsutil', 'cp', src_y, y_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                            X_data = np.load(X_file)
                            y_data = np.load(y_file)
                            
                            # Carregar o modelo
                            trainer = ModelTrainer(num_input=X_data.shape[1])
                            trainer.load(model_info['training_id'].split('_')[1], model_info['training_id'].split('_')[2])
                            
                            # Gerar e salvar os arquivos
                            trainer.save_projector_files(
                                model_info['training_id'].split('_')[1], 
                                model_info['training_id'].split('_')[2], 
                                X_data, y_data, 
                                logger=print
                            )
                    except Exception as e:
                        print(f"❌ Erro ao exportar: {e}")
                    self.hide_loader()
                return callback

            def _make_del_callback(model_info):
                def callback(b):
                    print(f"⚠️ Excluindo modelo: {model_info['training_id']}...")
                    try:
                        fs.rm(model_info['path'], recursive=True)
                        self._refresh_models_list(show_loader=True)
                    except Exception as e:
                        print(f"❌ Erro ao excluir: {e}")
                return callback
                
            btn.on_click(_make_callback(m))
            btn_proj.on_click(_make_proj_callback(m))
            btn_del.on_click(_make_del_callback(m))

            row = widgets.HBox([
                widgets.HTML(f"<div style='width:250px;font-family:monospace;'>{m['training_id']}</div>"), 
                widgets.HTML(f"<div style='width:100px;'>{status}</div>"),
                btn,
                widgets.HTML('<div style="width:5px;"></div>'),
                btn_proj,
                widgets.HTML('<div style="width:5px;"></div>'),
                btn_del
            ], layout=widgets.Layout(align_items='center', margin='2px 0', border_bottom='1px solid #eee'))
            items.append(row)
            
        if not items:
            items = [widgets.HTML("<i>Ningún modelo disponible en GCS.</i>")]
            
        self.analytics_area.children = items

def run_ui():
    ui = ModelTrainerUI()
    ui.display()
    
    # Executa inicialização com loader visível
    ui.show_loader("Cargando interfaz...")
    ui._build_ui()
    ui.hide_loader()
    
    return ui

def start_training(ui):
    selected_samples = [name for name, chk in ui.chk_dict.items() if chk.value]
    if not selected_samples:
        print("Error: Ninguna muestra seleccionada.")
        return
        
    ui.tabs.selected_index = 1 # Muda para a aba "Monitorización Live"
    ui.training_chart_output.clear_output()
    ui.analytics_dashboard_output.clear_output()
    
    # Constrói o dicionário de configuração de bandas a partir da nova Matriz Premium
    bands_config = {}
    for (s, m, b), chk in ui.band_chk_map.items():
        if chk.value:
            # Se a mesma banda for selecionada em múltiplos sensores, a última prevalece
            # Mas na prática o usuário escolherá uma fonte por banda
            bands_config[b] = {
                'sensor': s,
                'mosaic': m
            }
            
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
    
    ui.trainer_instance = ModelTrainer(num_input=len(bands_config), layers=layers, lr=lr)
    ui.trainer_instance._bands_input = sorted(bands_config.keys()) # Salva a ordem das bandas
    ui.trainer_instance._bands_config = bands_config # Salva a configuração completa
    ui.trainer_instance._sample_collections = selected_samples
    ui.trainer_instance._sample_count = {'burned': int(y.sum()), 'not_burned': int((y==0).sum())}
    
    print("Entrenando DNN...")
    
    def update_chart(history, embeds=None, preds=None, y_true=None):
        # 1. Atualizar Header HTML (KPIs)
        with ui.training_header_output:
            from sklearn.metrics import classification_report
            try:
                # Filtrar preds/y_true para evitar erros de tamanho se houver atraso
                rep = classification_report(y_true, (preds > 0.5).astype(int), output_dict=True, zero_division=0)
            except:
                rep = {}

            hp_live = {
                'training_id': ui.w_training_id.value,
                'shortname': ui.w_shortname.value,
                'sample_collections': selected_samples,
                'bands_input': sorted(bands_config.keys()),
                'layers': ui.w_layers.value,
                'lr': ui.w_lr.value,
                'sample_count': ui.trainer_instance._sample_count,
                'comment': ui.w_comment.value,
                'training_date': 'En progreso...'
            }
            clear_output(wait=True)
            display(HTML(render_model_card_html(hp_live, {'classification_report': rep})))

        # 2. Atualizar Dashboard de Gráficos (2x3 Grid - Matplotlib Rápido)
        with ui.training_chart_output:
            from sklearn.metrics import confusion_matrix, precision_recall_curve, average_precision_score
            from sklearn.decomposition import PCA
            
            try:
                # Forçar arrays unidimensionais para evitar IndexError
                y_true_f = y_true.flatten()
                preds_f = preds.flatten()
                
                cm = confusion_matrix(y_true_f, (preds_f > 0.5).astype(int))
                cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            except:
                cm = np.zeros((2,2)); cm_norm = np.zeros((2,2))

            clear_output(wait=True)
            fig = plt.figure(figsize=(18, 9))
            
            # (1,1) Matriz de Confusión (%)
            ax1 = fig.add_subplot(2, 3, 1)
            ax1.matshow(cm_norm, cmap='Blues', alpha=0.8, vmin=0, vmax=1)
            for (i, j), z in np.ndenumerate(cm):
                ax1.text(j, i, f"{z:,}\n({cm_norm[i,j]:.1%})", ha='center', va='center', 
                         weight='bold', color='black' if cm_norm[i,j] < 0.5 else 'white')
            ax1.set_title('Matriz de Confusión (%)', pad=15, weight='bold')
            ax1.set_xticks([0, 1]); ax1.set_yticks([0, 1])
            ax1.set_xticklabels(['No-fuego', 'Fuego']); ax1.set_yticklabels(['No-fuego', 'Fuego'])
            
            # (1,2) Evolución (Loss & Acc)
            ax2 = fig.add_subplot(2, 3, 2)
            ax2.plot(history['steps'], history['acc'], color='#28a745', label='Acc Treino', linewidth=2)
            ax2.plot(history['steps'], history['val_acc'], color='#28a745', label='Acc Validação', linestyle='--', alpha=0.6)
            ax2.set_ylabel('Acurácia', color='#28a745', weight='bold')
            ax2b = ax2.twinx()
            ax2b.plot(history['steps'], history['loss'], color='#dc3545', label='Loss', linewidth=1.5, alpha=0.7)
            ax2b.set_ylabel('Custo (Loss)', color='#dc3545', weight='bold')
            ax2.set_title('Evolución (Loss vs Acc)', weight='bold')
            ax2.grid(True, linestyle='--', alpha=0.3)

            # (1,3) PCA 2D (Playground Style)
            if embeds is not None:
                try:
                    pca2 = PCA(n_components=2)
                    coords2 = pca2.fit_transform(embeds)
                    ax3 = fig.add_subplot(2, 3, 3)
                    ax3.scatter(coords2[:, 0], coords2[:, 1], c=preds, cmap='RdBu_r', s=25, alpha=0.7, edgecolors='white', linewidth=0.3, vmin=0, vmax=1)
                    ax3.set_title('Proyección Latente 2D', weight='bold')
                    ax3.set_xticks([]); ax3.set_yticks([])
                except: pass

            # (2,1) Histograma de Confianza (Probabilidades)
            ax4 = fig.add_subplot(2, 3, 4)
            # Usar os arrays achatados aqui
            ax4.hist(preds_f[y_true_f==0], bins=30, alpha=0.5, color='#007bff', label='No-Fuego', density=True)
            ax4.hist(preds_f[y_true_f==1], bins=30, alpha=0.5, color='#ff4d4d', label='Fuego', density=True)
            ax4.set_title('Distribución de Probabilidades', weight='bold')
            ax4.set_xlabel('Confianza (Predicción)'); ax4.legend(fontsize=8); ax4.grid(True, alpha=0.2)

            # (2,2) Curva Precision-Recall
            try:
                precision, recall, _ = precision_recall_curve(y_true_f, preds_f)
                ap_score = average_precision_score(y_true_f, preds_f)
                ax5 = fig.add_subplot(2, 3, 5)
                ax5.plot(recall, precision, color='#17a2b8', linewidth=2, label=f'AP={ap_score:.3f}')
                ax5.fill_between(recall, precision, alpha=0.2, color='#17a2b8')
                ax5.set_title('Curva Precision-Recall', weight='bold')
                ax5.set_xlabel('Recall'); ax5.set_ylabel('Precision'); ax5.legend(loc='lower left', fontsize=8); ax5.grid(True, alpha=0.3)
            except: pass

            # (2,3) PCA 3D Projection
            if embeds is not None:
                try:
                    pca3 = PCA(n_components=3)
                    coords3 = pca3.fit_transform(embeds)
                    ax6 = fig.add_subplot(2, 3, 6, projection='3d')
                    ax6.scatter(coords3[:, 0], coords3[:, 1], coords3[:, 2], c=preds, cmap='RdBu_r', s=15, alpha=0.6, edgecolors='white', linewidth=0.2, vmin=0, vmax=1)
                    ax6.set_title('Espacio Latente 3D', weight='bold')
                    ax6.set_xticks([]); ax6.set_yticks([]); ax6.set_zticks([])
                except: pass
            
            plt.tight_layout()
            plt.show()
            
    ui.trainer_instance.train(X, y, batch_size=batch, n_iters=iters, logger=_logger, update_chart_fn=update_chart)
    
    # --- AUDITORIA FINAL COM t-SNE (INTERATIVO) ---
    print("\n🏁 Entrenamiento completado. Generando auditoría t-SNE final de alta resolución...")
    with ui.training_chart_output:
        import plotly.graph_objects as go
        from sklearn.manifold import TSNE
        try:
            display(HTML("<h4 style='color:#2c3e50; margin-top:20px; font-weight:bold;'>🚀 Auditoría t-SNE (Espacio Latente Final)</h4>"))
            display(HTML("<p style='font-size:11px; color:#666;'>Calculando proyección no-lineal para mejor visualización de clústeres...</p>"))
            
            # Pegamos uma amostra da validação para o t-SNE (ex: 600 pontos para ser rápido)
            idx_v = np.random.choice(len(X_val), min(600, len(X_val)), replace=False)
            X_v_sub = X_val[idx_v]
            y_v_sub = y_val[idx_v]
            
            emb_v = ui.trainer_instance.get_embeddings(X_v_sub)
            prd_v = ui.trainer_instance.predict(X_v_sub)
            
            # t-SNE 3D
            tsne = TSNE(n_components=3, perplexity=30, random_state=42, n_iter=1000)
            coords_tsne = tsne.fit_transform(emb_v)
            
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
            fig_tsne.show()
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
