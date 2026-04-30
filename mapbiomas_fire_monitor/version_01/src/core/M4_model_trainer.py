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
from M_ui_components import PipelineStepUI

# ─── EXTRAÇÃO DE DADOS (GCS) ──────────────────────────────────────────────────

ALL_BANDS = {
    'blue':      {'desc': 'Blue',      'default': False},
    'green':     {'desc': 'Green',     'default': False},
    'red':       {'desc': 'Red',       'default': True},
    'nir':       {'desc': 'NIR',       'default': True},
    'swir1':     {'desc': 'SWIR1',     'default': True},
    'swir2':     {'desc': 'SWIR2',     'default': True},
    'dayOfYear': {'desc': 'DayOfYear', 'default': False}
}

def list_sample_collections_gcs():
    """Lista arquivos CSV de amostras curadas no GCS."""
    try:
        project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
        fs = gcsfs.GCSFileSystem(project=project)
        path = f"{CONFIG['bucket']}/{CONFIG['gcs_samples']}"
        files = fs.ls(path)
        return sorted([f.split('/')[-1].replace('.csv', '') for f in files if f.endswith('.csv')], reverse=True)
    except Exception:
        return []

def list_trained_models():
    """Lista modelos já treinados no GCS."""
    try:
        project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
        fs = gcsfs.GCSFileSystem(project=project)
        path = f"{CONFIG['bucket']}/{CONFIG['gcs_models']}"
        models = []
        if fs.exists(path):
            versions = fs.ls(path)
            for v_dir in versions:
                v_name = v_dir.split('/')[-1]
                regions = fs.ls(v_dir)
                for r_dir in regions:
                    r_name = r_dir.split('/')[-1]
                    models.append({'version': v_name, 'region': r_name, 'path': r_dir})
        return models
    except Exception:
        return []

def extract_pixels_from_gcs(sample_groups, bands, logger=None):
    from M0_auth_config import mosaic_name, monthly_mosaic_path, yearly_mosaic_path
    project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
    fs = gcsfs.GCSFileSystem(project=project)
    
    dfs = []
    for group in sample_groups:
        sample_path = f"{CONFIG['bucket']}/{CONFIG['gcs_samples']}/{group}.csv"
        if logger: logger(f"Lendo amostras: {group}.csv", "info")
        try:
            with fs.open(sample_path, 'r') as f:
                dfs.append(pd.read_csv(f))
        except Exception as e:
            if logger: logger(f"Erro ao ler {group}: {e}", "error")
            
    if not dfs:
        return np.array([]), np.array([])
        
    df = pd.concat(dfs, ignore_index=True)
    df['geometry'] = df['.geo'].apply(lambda x: shape(json.loads(x)))
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
    
    X_all, y_all = [], []
    periods = gdf['period'].unique()
    
    for p in periods:
        if logger: logger(f"Extraindo píxeis para o período: {p}", "info")
        subset = gdf[gdf['period'] == p]
        
        parts = str(p).split('_')
        y = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else None
        per = 'monthly' if m else 'yearly'
        
        folder = monthly_mosaic_path(y, m) if m else yearly_mosaic_path(y)
        m_name = mosaic_name(y, m, per)
        
        geometries = subset.geometry.values
        labels = subset['fire'].values
        
        period_y = []
        band_data_list = []
        
        for band in bands:
            cog_path = f"{CONFIG['bucket']}/{folder}/{m_name}_{band}_cog.tif"
            if not fs.exists(cog_path):
                if logger: logger(f"COG ausente ({band}). Ignorando período {p}.", "warning")
                band_data_list = []
                break
                
            try:
                with fs.open(cog_path, 'rb') as f:
                    with MemoryFile(f.read()) as memfile:
                        with memfile.open() as src:
                            band_pixels, valid_labels = [], []
                            for geom, label in zip(geometries, labels):
                                try:
                                    out_image, _ = mask(src, [geom], crop=True, filled=False)
                                    valid_pixels = out_image.data[~out_image.mask]
                                    band_pixels.extend(valid_pixels)
                                    if len(period_y) == 0: 
                                        valid_labels.extend([label] * len(valid_pixels))
                                except ValueError:
                                    pass
                                    
                            band_data_list.append(np.array(band_pixels))
                            if len(period_y) == 0:
                                period_y = np.array(valid_labels)
            except Exception as e:
                if logger: logger(f"Erro ao ler COG {band}: {e}", "error")
                band_data_list = []
                break
                
        if len(band_data_list) == len(bands) and len(period_y) > 0:
            period_X = np.column_stack(band_data_list)
            X_all.append(period_X)
            y_all.append(period_y)
            
    if not X_all:
        return np.array([]), np.array([])
        
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
        
        batch_size = batch_size or CONFIG['model_batch']
        n_iters    = n_iters    or CONFIG['model_iters']
        split      = split      or CONFIG['model_split']

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

    def save(self, version, region, logger=None):
        import subprocess, tempfile
        base_path = model_path(version, region)
        project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
        fs = gcsfs.GCSFileSystem(project=project)

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Weights
            np.savez(os.path.join(tmpdir, 'weights.npz'), **self._saved_vars)

            # 2. Metadata
            hp = {
                'version':      version,
                'country':      CONFIG['country'],
                'region':       region,
                'sensor':       'sentinel2',
                'bands_input':  getattr(self, '_bands_input', CONFIG['bands_model_default']),
                'num_input':    self.num_input,
                'layers':       self.layers,
                'lr':           self.lr,
                'training_date': datetime.now().isoformat(),
                'norm_stats':   {str(k): list(v) for k, v in self.norm_stats.items()},
                'history':      self._history,
                'sample_collections': getattr(self, '_sample_collections', []),
                'sample_count': getattr(self, '_sample_count', {}),
            }
            with open(os.path.join(tmpdir, 'metadata.json'), 'w') as f:
                json.dump(hp, f, indent=2)

            for fname in ['weights.npz', 'metadata.json']:
                src  = os.path.join(tmpdir, fname)
                dest = gcs_path(f"{base_path}/{fname}")
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
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
            src = gcs_path(f"sudamerica/{CONFIG['country']}/monitor/library_samples/{coll}.csv")
            dest = gcs_path(f"{base_path}/samples/{coll}.csv")
            subprocess.run(['gsutil', 'cp', src, dest], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return hp


# ─── INTERFAZ PREMIUM ─────────────────────────────────────────────────────────

def generate_analytics(model_info, out_widget=None):
    import gcsfs, tempfile, subprocess
    from sklearn.metrics import confusion_matrix, classification_report
    
    project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
    fs = gcsfs.GCSFileSystem(project=project)
    base_gs = f"gs://{model_info['path']}"
    
    if out_widget:
        with out_widget:
            clear_output()
            print(f"Iniciando análise profunda para: {model_info['version']} / {model_info['region']}")
            print("Baixando dados (X_data, y_data, weights)...")
            
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ['extracted_pixels/X_data.npy', 'extracted_pixels/y_data.npy', 'metadata.json', 'weights.npz']:
            src = f"{base_gs}/{fname}"
            dest = os.path.join(tmpdir, fname.replace('/', '_'))
            try:
                subprocess.run(['gsutil', 'cp', src, dest], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                if out_widget:
                    with out_widget: print(f"Erro: Não foi possível baixar {fname}")
                return
                
        X = np.load(os.path.join(tmpdir, 'extracted_pixels_X_data.npy'))
        y = np.load(os.path.join(tmpdir, 'extracted_pixels_y_data.npy'))
        with open(os.path.join(tmpdir, 'metadata.json')) as f:
            hp = json.load(f)
            
        if out_widget:
            with out_widget: print("Calculando matriz de confusão e relatório...")
            
        stats = {int(k): tuple(v) for k, v in hp['norm_stats'].items()}
        X_norm = normalize(X, stats)
        
        weights = dict(np.load(os.path.join(tmpdir, 'weights.npz'), allow_pickle=True))
        layer = X_norm
        for i in range(len(hp['layers'])):
            W = weights[f'fc_{i}/kernel:0']
            b = weights[f'fc_{i}/bias:0']
            layer = np.maximum(0, np.dot(layer, W) + b)
            
        W_out = weights['output/kernel:0']
        b_out = weights['output/bias:0']
        logits = np.dot(layer, W_out) + b_out
        preds = (1 / (1 + np.exp(-logits))).flatten() > 0.5
        
        cm = confusion_matrix(y, preds)
        rep = classification_report(y, preds, output_dict=True)
        
        metrics = {
            'confusion_matrix': cm.tolist(),
            'classification_report': rep,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(os.path.join(tmpdir, 'metrics.json'), 'w') as f:
            json.dump(metrics, f, indent=2)
            
        subprocess.run(['gsutil', 'cp', os.path.join(tmpdir, 'metrics.json'), f"{base_gs}/metrics.json"], stdout=subprocess.DEVNULL)
        
        if out_widget:
            with out_widget:
                print("✅ Análises salvas em metrics.json no GCS!")
                fig, ax = plt.subplots(figsize=(5, 4))
                cax = ax.matshow(cm, cmap='Blues', alpha=0.8)
                fig.colorbar(cax)
                for (i, j), z in np.ndenumerate(cm):
                    ax.text(j, i, f'{z:d}', ha='center', va='center', weight='bold', color='black')
                ax.set_title('Matriz de Confusão (Todos os Dados)', pad=15)
                ax.set_xlabel('Predição (0=Não-fogo, 1=Fogo)')
                ax.set_ylabel('Realidade')
                plt.show()

class ModelTrainerUI(PipelineStepUI):
    def __init__(self):
        super().__init__(
            title="M4 - Entrenador del Modelo (DNN)", 
            description="Interface Matricial de Amostras, treinamento de rede neural e análises postergadas."
        )
        self.trainer_instance = None
        self.chk_dict = {}
        self._build_ui()

    def _on_select_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = True

    def _on_select_none(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = False

    def _build_matrix(self):
        L = widgets.Layout
        samples_available = list_sample_collections_gcs()
        self.chk_dict = {}
        
        self.btn_all = widgets.Button(description="Selecionar Todos", button_style='info', layout=L(width='155px'))
        self.btn_none = widgets.Button(description="Limpar Seleção", button_style='info', layout=L(width='145px'))
        self.btn_refresh = widgets.Button(description="Atualizar GCS", button_style='success', layout=L(width='150px'))
        
        self.btn_all.on_click(self._on_select_all)
        self.btn_none.on_click(self._on_select_none)
        self.btn_refresh.on_click(lambda _: self._build_ui())
        
        toolbar = widgets.HBox([self.btn_all, self.btn_none, self.btn_refresh], layout=L(margin='0 0 10px 0'))
        
        css = PipelineStepUI.get_status_css()
        hdr = [
            widgets.HTML('<span class="mfm-hdr">Nome da Amostra (GCS)</span>', layout=L(width='350px')),
            widgets.HTML('<span class="mfm-hdr">Status / [S]</span>', layout=L(width='120px', text_align='center'))
        ]
        matrix_rows = [widgets.HBox(hdr, layout=L(border_bottom='2px solid #343a40', padding='8px 0'))]
        
        if not samples_available:
            matrix_rows.append(widgets.HTML("<i>Nenhuma amostra encontrada no GCS.</i>", layout=L(padding='10px')))
        else:
            for s in samples_available:
                chk = widgets.Checkbox(value=False, indent=False, layout=L(width='18px', height='18px', margin='0'))
                chk._meta = s
                self.chk_dict[s] = chk
                
                status_cell = PipelineStepUI.make_status_cell(chk, 'OK', 'mfm-ok', width='120px')
                
                row = widgets.HBox([
                    widgets.HTML(f'<div style="width:350px;font-family:monospace;">{s}</div>'),
                    status_cell
                ], layout=L(align_items='center', margin='2px 0', border_bottom='1px solid #dee2e6'))
                matrix_rows.append(row)
                
        matrix = widgets.VBox(matrix_rows, layout=L(border='1px solid #dee2e6', padding='10px', max_height='300px', overflow_y='auto'))
        return widgets.VBox([css, toolbar, matrix])

    def _build_ui(self):
        L = widgets.Layout
        
        # --- TAB 1: Configuração & Treinamento ---
        matrix_ui = self._build_matrix()
        
        band_items = []
        for band, info in ALL_BANDS.items():
            chk = widgets.Checkbox(value=info['default'], description=info['desc'], layout=L(width='auto', margin='0 15px 0 0'))
            band_items.append((band, chk))
        self.band_checkboxes = dict(band_items)
        band_box = widgets.HBox([chk for _, chk in band_items], layout=L(flex_flow='row wrap', border='1px solid #dee2e6', padding='10px', border_radius='4px', margin='10px 0'))
        
        self.w_iters = widgets.IntSlider(value=7000, min=1000, max=20000, step=500, description='Iterações:', style={'description_width': '150px'}, layout=L(width='400px'))
        self.w_batch = widgets.IntSlider(value=1000, min=100, max=5000, step=100, description='Tamanho do Lote:', style={'description_width': '150px'}, layout=L(width='400px'))
        self.w_lr = widgets.FloatText(value=0.001, description='Taxa de Aprendizado:', style={'description_width': '150px'}, layout=L(width='250px'))
        self.w_layers = widgets.Text(value="7, 14, 7", description='Camadas Ocultas:', style={'description_width': '150px'}, tooltip="Ex: 128, 64, 32", layout=L(width='250px'))
        
        hp_box = widgets.VBox([
            widgets.HBox([self.w_iters, self.w_batch]), 
            widgets.HBox([self.w_lr, self.w_layers])
        ], layout=L(margin='10px 0'))
        
        self.w_version = widgets.Text(value='v1', description='Versão:', style={'description_width': '80px'})
        self.w_region = widgets.Text(value='peru_r1', description='Região:', style={'description_width': '80px'})
        
        self.btn_extract_train = widgets.Button(description="Iniciar Treino Rápido & Salvar", button_style='primary', icon='rocket', layout=L(width='250px'))
        self.btn_extract_train.on_click(self._on_train_clicked)
        
        tab_config = widgets.VBox([
            widgets.HTML("<b>1. Seleção Múltipla de Dados (GCS)</b>"), matrix_ui,
            widgets.HTML("<br><b>2. Variáveis Espectrais</b>"), band_box,
            widgets.HTML("<b>3. Hiperparâmetros (DNN)</b>"), hp_box,
            widgets.HTML("<hr style='margin:10px 0'>"),
            widgets.HTML("<b>4. Destino Final no GCS</b>"),
            widgets.HBox([self.w_version, self.w_region], layout=L(margin='10px 0')),
            self.btn_extract_train
        ], layout=L(padding='15px'))
        
        # --- TAB 2: Analytics & Monitoramento ---
        self.chart_output = widgets.Output(layout=L(border='1px solid #dee2e6', border_radius='4px', padding='10px', min_height='250px', margin='10px 0'))
        self.analytics_area = widgets.VBox()
        self._refresh_models_list()
        
        tab_monitor = widgets.VBox([
            widgets.HTML("<b>Treinamento Atual (Live)</b>"),
            self.chart_output,
            widgets.HTML("<hr style='margin:15px 0'>"),
            widgets.HTML("<b>Análises Complementares (Postergadas)</b>"),
            widgets.HTML("<p style='font-size:11px;color:#666;'>Modelos prontos para análise profunda de matriz de confusão e importâncias.</p>"),
            self.analytics_area
        ], layout=L(padding='15px'))
        
        self.tabs = widgets.Tab(children=[tab_config, tab_monitor])
        self.tabs.set_title(0, '⚙️ Configuração & Treinamento')
        self.tabs.set_title(1, '📊 Monitoramento & Analytics')
        
        self.clear_main()
        self.main_area.children = [self.tabs]

    def _refresh_models_list(self):
        models = list_trained_models()
        import gcsfs
        project = CONFIG.get('gcs_project', CONFIG.get('ee_project'))
        fs = gcsfs.GCSFileSystem(project=project)
        
        items = []
        for m in models:
            has_metrics = fs.exists(f"{m['path']}/metrics.json")
            status = "✅ Pronta" if has_metrics else "⏳ Pendente"
            btn = widgets.Button(
                description="Gerar Análises" if not has_metrics else "Ver Análise", 
                button_style='info' if not has_metrics else 'success', 
                icon='cogs' if not has_metrics else 'eye',
                layout=widgets.Layout(width='150px')
            )
            
            def _make_callback(model_info):
                def callback(b):
                    generate_analytics(model_info, out_widget=self.chart_output)
                    self._refresh_models_list()
                return callback
                
            btn.on_click(_make_callback(m))
            row = widgets.HBox([
                widgets.HTML(f"<div style='width:300px;font-family:monospace;'>{m['version']} / {m['region']}</div>"), 
                widgets.HTML(f"<div style='width:100px;'>{status}</div>"),
                btn
            ], layout=widgets.Layout(align_items='center', margin='2px 0', border_bottom='1px solid #eee'))
            items.append(row)
            
        if not items:
            items = [widgets.HTML("<i>Nenhum modelo disponível no GCS.</i>")]
            
        self.analytics_area.children = items

    def _on_train_clicked(self, _):
        selected_samples = [chk._meta for chk in self.chk_dict.values() if chk.value]
        if not selected_samples:
            self.log("Nenhuma amostra selecionada.", "error")
            return
            
        self.tabs.selected_index = 1 
        self.clear_logs()
        self.chart_output.clear_output()
        self.btn_extract_train.disabled = True
        
        bands = [b for b, chk in self.band_checkboxes.items() if chk.value]
        layers = [int(x.strip()) for x in self.w_layers.value.split(',')]
        
        self.log(f"Extraindo píxeis de {len(selected_samples)} coleções. Aguarde...", "info")
        
        X, y = extract_pixels_from_gcs(selected_samples, bands, logger=self.log)
        
        if len(X) == 0:
            self.log("Falha ao extrair píxeis.", "error")
            self.btn_extract_train.disabled = False
            return
            
        self.log(f"Sucesso: {len(X)} píxeis extraídos (Fogo: {y.sum()} | Não-fogo: {(y==0).sum()}).", "success")
        
        self.trainer_instance = ModelTrainer(num_input=len(bands), layers=layers, lr=self.w_lr.value)
        self.trainer_instance._bands_input = bands
        self.trainer_instance._sample_collections = selected_samples
        self.trainer_instance._sample_count = {'burned': int(y.sum()), 'not_burned': int((y==0).sum())}
        
        self.log("Treinando DNN (Fast Mode)...", "warning")
        
        def update_chart(history):
            with self.chart_output:
                clear_output(wait=True)
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))
                
                ax1.plot(history['steps'], history['loss'], color='#d9534f', linewidth=2)
                ax1.set_title('Função de Custo (Loss)', fontsize=10, weight='bold')
                ax1.set_xlabel('Iteração', fontsize=9)
                ax1.grid(True, linestyle='--', alpha=0.5)
                
                ax2.plot(history['steps'], history['acc'], color='#0275d8', label='Treino', linewidth=2)
                ax2.plot(history['steps'], history['val_acc'], color='#5cb85c', label='Validação', linestyle='--', linewidth=2)
                ax2.set_title('Acurácia', fontsize=10, weight='bold')
                ax2.set_xlabel('Iteração', fontsize=9)
                ax2.legend(fontsize=9)
                ax2.grid(True, linestyle='--', alpha=0.5)
                
                plt.tight_layout()
                plt.show()
                
        self.trainer_instance.train(X, y, batch_size=self.w_batch.value, n_iters=self.w_iters.value, logger=self.log, update_chart_fn=update_chart)
        
        self.log("Salvando estrutura (amostras, píxeis, metadados) no GCS...", "info")
        try:
            self.trainer_instance.save(self.w_version.value, self.w_region.value, logger=self.log)
            self.log("Modelo salvo e pronto para uso no M5!", "success")
            self.log("As análises profundas podem ser disparadas abaixo quando desejar.", "info")
        except Exception as e:
            self.log(f"Erro ao salvar: {e}", "error")
            
        self.btn_extract_train.disabled = False
        self._refresh_models_list()

def run_ui():
    ui = ModelTrainerUI()
    ui.display()
    return ui

def start_training(ui):
    pass
