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
from IPython.display import display, clear_output
import matplotlib.pyplot as plt
from datetime import datetime

from M0_auth_config import CONFIG, gcs_path, model_path
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
    from M0_auth_config import _gcs_library_base
    try:
        fs = _get_fs()
        path = f"{CONFIG['bucket']}/{_gcs_library_base()}/models"
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
        if logger: logger(f"Lendo amostras: {group}.csv", "info")
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
                        if logger: logger(f"  ⚠️ Detectada data futura {p_found} no CSV. Corrigindo para {file_date}...", "warning")
                        temp_df['period'] = file_date
                        p_found = [file_date]
                    
                    if logger: logger(f"  🔍 Conteúdo: {len(temp_df)} pontos | Períodos: {p_found}", "info")
                dfs.append(temp_df)
        except Exception as e:
            if logger: logger(f"Erro ao ler {group}: {e}", "error")
            
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
            if logger: logger(f"⚠️ Pulo período {p}: Faltam {len(missing_bands)} bandas ({', '.join(missing_bands)})", "warning")
            continue

        if logger: logger(f"✅ Mosaicos OK para {p}: {len(band_paths)} bandas prontas para extração.", "info")
        if logger: logger(f"📡 Extraindo {len(geometries)} amostras de {p}...", "info")
        
        # --- LEITURA REAL DAS BANDAS ---
        band_data_list = []
        valid_period = True
        period_y = np.array([])
        
        for b in bands_sorted:
            cog_path = band_paths[b]
            try:
                # Tenta leitura via /vsigs/ (Linux/Colab) ou local (Windows)
                is_colab = 'COLAB_RELEASE_TAG' in os.environ
                src_path = f"/vsigs/{cog_path.replace('gs://', '')}" if is_colab else None
                
                # Para Windows, fazemos download temporário
                local_file = None
                if not is_colab:
                    from M0_auth_config import get_temp_dir
                    local_file = os.path.join(get_temp_dir(), os.path.basename(cog_path))
                    
                    if logger: logger(f"  📥 Baixando banda {b}...", "info")
                    try:
                        fs.get(cog_path, local_file)
                        if not os.path.exists(local_file) or os.path.getsize(local_file) < 1000:
                            raise Exception("Download falhou ou arquivo vazio.")
                        src_path = local_file
                    except Exception as e:
                        if logger: logger(f"  ❌ Erro no download {cog_path}: {e}", "error")
                        valid_period = False; break
                
                with rasterio.open(src_path) as src:
                    band_pixels, valid_labels = [], []
                    for geom, label in zip(geometries, labels):
                        try:
                            out_image, _ = mask(src, [geom], crop=True, filled=False)
                            if not out_image.mask.all():
                                v_px = out_image.data[~out_image.mask]
                                band_pixels.extend(v_px)
                                if len(period_y) == 0: valid_labels.extend([label] * len(v_px))
                        except: pass
                    
                    if not band_pixels:
                        valid_period = False; break
                    band_data_list.append(np.array(band_pixels))
                    if len(period_y) == 0: period_y = np.array(valid_labels)
                    
                if local_file and os.path.exists(local_file): os.remove(local_file)
                
            except Exception as e:
                if logger: logger(f"Erro crítico ao ler {b} em {p}: {e}", "error")
                valid_period = False; break
                
        if valid_period and len(band_data_list) == len(bands_sorted):
            X_period = np.column_stack(band_data_list)
            X_all.append(X_period)
            y_all.append(period_y)
            
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

                    if logger:
                        logger(f"Iter {i:5d}/{n_iters} | Loss: {loss_val:.4f} | Acc Treino: {acc_tr:.3f} | Validação: {acc_te:.3f}", "info")
                    
                    if update_chart_fn:
                        update_chart_fn(history)

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
            if logger: logger("Gerando e salvando métricas de avaliação...", "info")
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
            if logger: logger("Salvando matriz de píxeis no GCS...", "info")
            np.save(os.path.join(tmpdir, 'X_data.npy'), self._X_raw)
            np.save(os.path.join(tmpdir, 'y_data.npy'), self._y_raw)
            
            for fname in ['X_data.npy', 'y_data.npy']:
                src  = os.path.join(tmpdir, fname)
                dest = gcs_path(f"{base_path}/extracted_pixels/{fname}")
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        # 4. Copy samples
        if logger: logger("Copiando arquivos CSV das amostras para persistência...", "info")
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
                    with out_widget: print(f"Error: Arquivo {fname} não encontrado. Treine o modelo novamente.")
                return
                
        with open(os.path.join(tmpdir, 'metadata.json')) as f:
            hp = json.load(f)
        with open(os.path.join(tmpdir, 'metrics.json')) as f:
            metrics = json.load(f)
            
        cm = np.array(metrics['confusion_matrix'])
        rep = metrics['classification_report']
        
        # Cores para o header
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
        acc = rep.get('accuracy', 0)
        f1_fire = rep.get('1', {}).get('f1-score', 0)
        prec_fire = rep.get('1', {}).get('precision', 0)
        rec_fire = rep.get('1', {}).get('recall', 0)
        
        # Formatando data
        date_str = hp.get('training_date', '')
        if date_str: date_str = date_str[:16].replace('T', ' ')
        
        html_content = f"""
        {style}
        <div class="dash-card">
            <div class="dash-title">📄 Model Card: {hp.get('training_id')} / {hp.get('shortname')}</div>
            <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 15px;">
                <div style="flex: 2; min-width: 300px;">
                    <p class="meta-text"><b>Data de Criação:</b> {date_str}</p>
                    <p class="meta-text"><b>Amostras Usadas:</b> {', '.join(hp.get('sample_collections', []))}</p>
                    <p class="meta-text"><b>Bandas Espectrais:</b> {', '.join(hp.get('bands_input', []))}</p>
                    <p class="meta-text"><b>Arquitetura (Camadas):</b> {hp.get('layers')} | <b>LR:</b> {hp.get('lr')}</p>
                    <p class="meta-text"><b>Total Píxeis (Fogo):</b> {hp.get('sample_count', {}).get('burned', 0)} | <b>Não-Fogo:</b> {hp.get('sample_count', {}).get('not_burned', 0)}</p>
                </div>
                <div style="flex: 1; min-width: 250px; background:#fff3cd; padding:10px; border-radius:4px; border:1px solid #ffeeba;">
                    <p class="meta-text" style="color:#856404; font-weight:bold; margin-bottom:5px;">📝 Comentário do Treinamento:</p>
                    <p class="meta-text" style="color:#856404; font-style:italic;">{hp.get('comment', 'Sem comentário.')}</p>
                </div>
            </div>
            
            <div class="dash-grid">
                <div class="kpi-box" style="border-left-color: #28a745;">
                    <div class="kpi-title">Acurácia Global</div>
                    <div class="kpi-value">{acc:.1%}</div>
                </div>
                <div class="kpi-box" style="border-left-color: #dc3545;">
                    <div class="kpi-title">Precisão (Fogo)</div>
                    <div class="kpi-value">{prec_fire:.1%}</div>
                </div>
                <div class="kpi-box" style="border-left-color: #ffc107;">
                    <div class="kpi-title">Recall (Fogo)</div>
                    <div class="kpi-value">{rec_fire:.1%}</div>
                </div>
                <div class="kpi-box" style="border-left-color: #17a2b8;">
                    <div class="kpi-title">F1-Score (Fogo)</div>
                    <div class="kpi-value">{f1_fire:.1%}</div>
                </div>
            </div>
        </div>
        """
        
        if out_widget:
            out_widget.clear_output(wait=True)
            with out_widget:
                display(HTML(html_content))
                
                # Plot Confusion Matrix and Training History if available
                fig = plt.figure(figsize=(12, 4))
                
                # Confusion Matrix
                ax1 = plt.subplot(1, 2, 1)
                cax = ax1.matshow(cm, cmap='Blues', alpha=0.8)
                fig.colorbar(cax, ax=ax1)
                for (i, j), z in np.ndenumerate(cm):
                    ax1.text(j, i, f"{z:,}", ha='center', va='center', weight='bold', color='black' if z < cm.max()/2 else 'white')
                ax1.set_title('Matriz de Confusão', pad=15, weight='bold')
                ax1.set_ylabel('Real')
                ax1.set_xlabel('Predito')
                ax1.set_xticks([0, 1])
                ax1.set_yticks([0, 1])
                ax1.set_xticklabels(['No-fuego', 'Fuego'])
                ax1.set_yticklabels(['No-fuego', 'Fuego'])
                
                # Training History
                history = hp.get('history', {})
                if history and 'steps' in history:
                    ax2 = plt.subplot(1, 2, 2)
                    ax2.plot(history['steps'], history['acc'], color='#0275d8', label='Treino', linewidth=2)
                    ax2.plot(history['steps'], history['val_acc'], color='#5cb85c', label='Validação', linestyle='--', linewidth=2)
                    ax2.set_title('Evolução da Acurácia', weight='bold')
                    ax2.set_xlabel('Iteração')
                    ax2.legend()
                    ax2.grid(True, linestyle='--', alpha=0.5)
                
                plt.tight_layout()
                plt.show()

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
            return widgets.HTML('<div style="padding:10px; color:#999;"><i>Nenhuma amostra encontrada com este filtro.</i></div>')
            
        return widgets.VBox(matrix_rows)

    def _build_matrix(self):
        L = widgets.Layout
        css = PipelineStepUI.get_status_css()
        
        # BARRA DE BUSCA
        self.txt_search_samples = widgets.Text(
            value=self.search_query_samples,
            placeholder='Buscar amostras (ex: r10)...',
            layout=L(width='300px')
        )
        self.txt_search_samples.observe(self._on_search_samples_change, names='value')

        btn_all = widgets.Button(description="Selecionar Filtradas", button_style='info', icon='check-square', layout=L(width='180px'))
        btn_none = widgets.Button(description="Limpar Filtradas", button_style='warning', icon='square-o', layout=L(width='180px'))
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
            placeholder='Describa aqui os detalhes de este treinamento...',
            description='Comentário:',
            style={'description_width': '100px'},
            layout=L(width='98%', height='80px')
        )
        
        tab_config = widgets.VBox([
            widgets.HTML("<b>1. Seleção de Amostras (Matriz GCS)</b>"), matrix_ui,
            widgets.HTML("<br><b>2. Matriz de Extração (Bandas por Sensor+Mosaico)</b>"), extraction_matrix,
            widgets.HTML("<b>3. Hiperparâmetros (DNN)</b>"), hp_box,
            widgets.HTML("<hr style='margin:10px 0'>"),
            widgets.HTML("<b>4. Destino Final no GCS</b>"),
            widgets.HBox([self.w_training_id, self.w_shortname], layout=L(margin='10px 0')),
            self.w_comment
        ], layout=L(padding='15px'))
        
        # --- TAB 2: Analytics & Monitoramento ---
        self.training_chart_output = widgets.Output(layout=L(border='1px solid #dee2e6', border_radius='4px', padding='10px', min_height='250px', margin='10px 0'))
        self.analytics_dashboard_output = widgets.Output(layout=L(border='1px solid #dee2e6', border_radius='4px', padding='10px', min_height='300px', margin='10px 0', background_color='#fafafa'))
        
        self.analytics_area = widgets.VBox()
        self._refresh_models_list()
        
        tab_monitor = widgets.VBox([
            widgets.HTML("<b>📈 Entrenamiento Actual (En vivo)</b>"),
            self.training_chart_output,
            widgets.HTML("<hr style='margin:15px 0'>"),
            widgets.HTML("<b>📊 Model Card & Analytics Dashboard</b>"),
            self.analytics_dashboard_output,
            widgets.HTML("<hr style='margin:15px 0'>"),
            widgets.HTML("<b>📂 Historial de Modelos</b>"),
            widgets.HTML("<p style='font-size:11px;color:#666;'>Consulte los Model Cards de entrenamientos anteriores.</p>"),
            self.analytics_area
        ], layout=L(padding='15px'))
        
        self.tabs = widgets.Tab(children=[tab_config, tab_monitor])
        self.tabs.set_title(0, '⚙️ Configuración & Entrenamiento')
        self.tabs.set_title(1, '📊 Monitorización & Análisis')
        
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
                tooltip="Excluir Modelo permanentemente do GCS"
            )
            
            def _make_callback(model_info):
                def callback(b):
                    view_analytics(model_info, out_widget=self.analytics_dashboard_output)
                return callback

            def _make_del_callback(model_info):
                def callback(b):
                    if logger: logger(f"Excluindo modelo: {model_info['training_id']}...", "warning")
                    try:
                        fs.rm(model_info['path'], recursive=True)
                        self._refresh_models_list(show_loader=True)
                    except Exception as e:
                        if logger: logger(f"Erro ao excluir: {e}", "error")
                return callback
                
            btn.on_click(_make_callback(m))
            btn_del.on_click(_make_del_callback(m))

            row = widgets.HBox([
                widgets.HTML(f"<div style='width:300px;font-family:monospace;'>{m['training_id']}</div>"), 
                widgets.HTML(f"<div style='width:100px;'>{status}</div>"),
                btn,
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
        
    ui.tabs.selected_index = 1 
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
    
    def update_chart(history):
        with ui.training_chart_output:
            clear_output(wait=True)
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))
            
            ax1.plot(history['steps'], history['loss'], color='#d9534f', linewidth=2)
            ax1.set_title('Función de Costo (Loss)', fontsize=10, weight='bold')
            ax1.set_xlabel('Iteración', fontsize=9)
            ax1.grid(True, linestyle='--', alpha=0.5)
            
            ax2.plot(history['steps'], history['acc'], color='#0275d8', label='Entrenamiento', linewidth=2)
            ax2.plot(history['steps'], history['val_acc'], color='#5cb85c', label='Validación', linestyle='--', linewidth=2)
            ax2.set_title('Precisión', fontsize=10, weight='bold')
            ax2.set_xlabel('Iteración', fontsize=9)
            ax2.legend(fontsize=9)
            ax2.grid(True, linestyle='--', alpha=0.5)
            
            plt.tight_layout()
            plt.show()
            
    ui.trainer_instance.train(X, y, batch_size=batch, n_iters=iters, logger=_logger, update_chart_fn=update_chart)
    
    print("Guardando estructura (muestras, píxeles, metadatos, métricas) en GCS...")
    try:
        ui.trainer_instance.save(ui.w_training_id.value, ui.w_shortname.value, comment=ui.w_comment.value, logger=_logger)
        print("¡Modelo y Model Card guardados exitosamente!")
        
        # Carregar o Model Card automaticamente no dashboard inferior
        from M0_auth_config import model_path
        model_info = {
            'training_id': f"training_{ui.w_training_id.value}_{ui.w_shortname.value}_{GLOBAL_OPTS['SENSOR'].lower()}", 
            'path': model_path(ui.w_training_id.value, ui.w_shortname.value)
        }
        view_analytics(model_info, out_widget=ui.analytics_dashboard_output)
        
    except Exception as e:
        print(f"Error al guardar: {e}")
        
    ui._refresh_models_list()
