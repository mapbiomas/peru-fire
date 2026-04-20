"""
2: M4 — Entrenador del Modelo
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Arquitectura DNN (NUM_INPUT dinámico basado en las bandas seleccionadas)
  2. Normalización de datos por banda
  3. División entrenamiento / prueba + evaluación
  4. Guardar modelo + hyperparameters.json en GCS
  5. Interfaz de ipywidgets para Colab
"""

import os
import json
import time
import numpy as np
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

import ipywidgets as widgets
from IPython.display import display, clear_output
from datetime import datetime
from M0_auth_config import CONFIG, gcs_path, model_path

# ─── NORMALIZACIÓN ────────────────────────────────────────────────────────────

def compute_normalizer(X):
    """
    Calcular la media y la desviación estándar por banda para la normalización.
    Devuelve un diccionario: {band_index: (mean, std)}
    """
    stats = {}
    for i in range(X.shape[1]):
        col = X[:, i]
        stats[i] = (float(col.mean()), float(col.std() + 1e-8))
    return stats


def normalize(X, stats):
    """Aplicar la normalización de puntuación z utilizando estadísticas precalculadas."""
    X_norm = X.copy()
    for i, (mean, std) in stats.items():
        X_norm[:, i] = (X_norm[:, i] - mean) / std
    return X_norm


# ─── ARQUITECTURA DNN ─────────────────────────────────────────────────────────

class ModelTrainer:
    """
    DNN de TensorFlow 1.x para la detección de áreas quemadas.
    NUM_INPUT dinámico: se adapta a cualquier número de bandas de entrada.
    Arquitectura: capas FC con ReLU → salida sigmoidea.
    """

    def __init__(self, num_input, layers=None, lr=None, seed=42):
        self.num_input  = num_input
        self.layers     = layers or CONFIG['model_layers']
        self.lr         = lr     or CONFIG['model_lr']
        self.seed       = seed
        self.graph      = None
        self.session    = None
        self.norm_stats = None
        self._is_built  = False

    def _build_graph(self):
        """Construir el gráfico computacional de TF1."""
        tf.reset_default_graph()
        tf.set_random_seed(self.seed)

        self.x   = tf.placeholder(tf.float32, [None, self.num_input], name='x')
        self.y   = tf.placeholder(tf.float32, [None, 1],              name='y')
        self.keep_prob = tf.placeholder(tf.float32, name='keep_prob')

        # Construir capas ocultas
        layer = self.x
        for i, n_units in enumerate(self.layers):
            layer = tf.layers.dense(
                layer, n_units,
                activation=tf.nn.relu,
                kernel_initializer=tf.glorot_uniform_initializer(seed=self.seed),
                name=f'fc_{i}'
            )
            layer = tf.nn.dropout(layer, rate=1 - self.keep_prob)

        # Salida: sigmoidea (clasificación binaria)
        self.logits = tf.layers.dense(layer, 1, name='output')
        self.pred   = tf.nn.sigmoid(self.logits)

        # Pérdida + optimizador
        self.loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(
                labels=self.y, logits=self.logits
            )
        )
        self.train_op = tf.train.AdamOptimizer(self.lr).minimize(self.loss)
        self.saver    = tf.train.Saver()
        self._is_built = True

    def train(self, X, y, batch_size=None, n_iters=None, split=None,
              keep_prob=0.8, out_widget=None):
        """
        Entrenar el modelo.
        Devuelve el diccionario del historial de entrenamiento.
        """
        batch_size = batch_size or CONFIG['model_batch']
        n_iters    = n_iters    or CONFIG['model_iters']
        split      = split      or CONFIG['model_split']

        # Calcular el normalizador a partir de los datos de entrenamiento
        self.norm_stats = compute_normalizer(X)
        X_norm = normalize(X, self.norm_stats)

        # División entrenamiento / prueba
        n = len(X_norm)
        idx = np.random.permutation(n)
        n_train = int(n * split)
        X_tr, y_tr = X_norm[idx[:n_train]], y[idx[:n_train]].reshape(-1, 1)
        X_te, y_te = X_norm[idx[n_train:]], y[idx[n_train:]].reshape(-1, 1)

        self._build_graph()
        history = {'loss': [], 'acc': [], 'val_acc': []}

        def _print(msg):
            if out_widget:
                with out_widget:
                    print(msg)
            else:
                print(msg)

        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            self.session = sess

            for i in range(1, n_iters + 1):
                # Mini-lote
                b_idx = np.random.randint(0, n_train, batch_size)
                X_b   = X_tr[b_idx]
                y_b   = y_tr[b_idx]

                _, loss_val = sess.run(
                    [self.train_op, self.loss],
                    feed_dict={self.x: X_b, self.y: y_b, self.keep_prob: keep_prob}
                )

                if i % max(1, n_iters // 20) == 0 or i == n_iters:
                    # Precisión de entrenamiento
                    pred_tr = sess.run(self.pred,
                        feed_dict={self.x: X_tr, self.y: y_tr, self.keep_prob: 1.0})
                    acc_tr = ((pred_tr > 0.5).astype(int) == y_tr.astype(int)).mean()

                    # Precisión de validación
                    pred_te = sess.run(self.pred,
                        feed_dict={self.x: X_te, self.y: y_te, self.keep_prob: 1.0})
                    acc_te = ((pred_te > 0.5).astype(int) == y_te.astype(int)).mean()

                    history['loss'].append(loss_val)
                    history['acc'].append(acc_tr)
                    history['val_acc'].append(acc_te)

                    _print(f"  iter {i:5d}/{n_iters}  |  "
                           f"loss={loss_val:.4f}  |  acc={acc_tr:.3f}  |  val_acc={acc_te:.3f}")

            # Guardado final
            self._saved_vars = {v.name: sess.run(v)
                                for v in tf.global_variables()}
            self._history = history

        return history

    def save(self, version, region):
        """Guardar pesos del modelo + hyperparameters.json en GCS."""
        import subprocess, tempfile, pickle

        base_path = model_path(version, region)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Guardar pesos como numpy .npz
            np.savez(os.path.join(tmpdir, 'weights.npz'), **self._saved_vars)

            # Guardar hiperparámetros
            hp = {
                'version':      version,
                'country':      CONFIG['country'],
                'region':       region,
                'sensor':       'sentinel2',
                'period_type':  'monthly',
                'bands_input':  getattr(self, '_bands_input', CONFIG['bands_model_default']),
                'num_input':    self.num_input,
                'label_index':  self.num_input,
                'layers':       self.layers,
                'lr':           self.lr,
                'training_date': datetime.now().isoformat(),
                'norm_stats':   {str(k): list(v) for k, v in self.norm_stats.items()},
                'history':      self._history,
                'gcs_model_path': gcs_path(base_path),
                'sample_collection': getattr(self, '_sample_collection', ''),
                'sample_count': getattr(self, '_sample_count', {}),
            }
            with open(os.path.join(tmpdir, 'hyperparameters.json'), 'w') as f:
                json.dump(hp, f, indent=2)

            # Subir ambos archivos
            for fname in ['weights.npz', 'hyperparameters.json']:
                src  = os.path.join(tmpdir, fname)
                dest = gcs_path(f"{base_path}/{fname}")
                subprocess.run(['gsutil', 'cp', src, dest], check=True)
                print(f"  ☁️  Subido: {dest}")

        print(f"  ✅  Modelo guardado: gs://{CONFIG['bucket']}/{base_path}/")
        return hp

    def load(self, version, region):
        """Cargar pesos del modelo + hiperparámetros desde GCS."""
        import subprocess, tempfile

        base_path = model_path(version, region)

        with tempfile.TemporaryDirectory() as tmpdir:
            for fname in ['weights.npz', 'hyperparameters.json']:
                src  = gcs_path(f"{base_path}/{fname}")
                dest = os.path.join(tmpdir, fname)
                subprocess.run(['gsutil', 'cp', src, dest], check=True)

            hp_path = os.path.join(tmpdir, 'hyperparameters.json')
            with open(hp_path) as f:
                hp = json.load(f)

            self.num_input      = hp['num_input']
            self.layers         = hp['layers']
            self.lr             = hp['lr']
            self.norm_stats     = {int(k): tuple(v)
                                   for k, v in hp['norm_stats'].items()}
            self._bands_input   = hp['bands_input']
            self._sample_count  = hp['sample_count']
            self._history       = hp.get('history', {})

            wt_path = os.path.join(tmpdir, 'weights.npz')
            self._saved_vars = dict(np.load(wt_path, allow_pickle=True))

        print(f"  ✅  Modelo cargado: {version}/{region}")
        print(f"      Bandas     : {self._bands_input}  (NUM_INPUT={self.num_input})")
        print(f"      Muestras   : {self._sample_count}")
        return hp

    def predict_array(self, X_raw, threshold=0.5):
        """
        Ejecutar inferencia en una matriz numpy cruda.
        Devuelve predicciones binarias (0/1).
        """
        X_norm = normalize(X_raw, self.norm_stats)
        self._build_graph()
        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            # Restaurar pesos
            for var in tf.global_variables():
                if var.name in self._saved_vars:
                    sess.run(var.assign(self._saved_vars[var.name]))
            preds = sess.run(self.pred,
                             feed_dict={self.x: X_norm, self.keep_prob: 1.0})
        return (preds.flatten() > threshold).astype(np.uint8)


# ─── INTERFAZ DE IPYWIDGETS ───────────────────────────────────────────────────

class ModelTrainerUI:
    """
    Interfaz para configurar el entrenamiento del modelo.
    """

    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        from M3_sample_manager import list_sample_collections, ALL_BANDS

        title = HTML("""
            <div style="background:linear-gradient(135deg,#0a0a0a,#1e1e2e); color:#cba6f7;padding:14px 18px;border-radius:10px; font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                🧠 <b>Entrenador del Modelo</b> — DNN Detección Áreas Quemadas<br>
                <span style="color:#8892b0;font-size:11px;">Configura hiperparámetros y extrae píxeles reales para entrenamiento</span>
            </div>
        """)

        # Fetch sample collections from GEE (or GCS logic adapted)
        sample_groups = list_sample_collections()
        
        self.w_sample_group = widgets.Dropdown(
            options=sample_groups or ['(ninguno encontrado)'],
            description='Grupo Muestras:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='380px')
        )
        
        self.w_version = widgets.Text(value='v1', description='Versión Salida:', style={'description_width': '120px'}, layout=widgets.Layout(width='250px'))
        self.w_region  = widgets.Text(value='peru_r1', description='Región Salida:', style={'description_width': '120px'}, layout=widgets.Layout(width='250px'))
        self.w_iters   = widgets.IntSlider(value=CONFIG['model_iters'], min=1000, max=20000, step=500, description='Iteraciones:', style={'description_width': '120px'}, layout=widgets.Layout(width='380px'))
        self.w_batch   = widgets.IntSlider(value=CONFIG['model_batch'], min=100, max=5000, step=100, description='Lote:', style={'description_width': '120px'}, layout=widgets.Layout(width='380px'))
        self.w_lr      = widgets.FloatText(value=CONFIG['model_lr'], description='Learn Rate:', style={'description_width': '120px'}, layout=widgets.Layout(width='200px'))
        self.w_layers  = widgets.Text(value=str(CONFIG['model_layers']), description='Capas (Layers):', style={'description_width': '120px'}, layout=widgets.Layout(width='300px'))

        band_items = []
        for band, info in ALL_BANDS.items():
            chk = widgets.Checkbox(value=info['default'], description=f"{band} ({info['desc']})")
            band_items.append((band, chk))
        self.band_checkboxes = dict(band_items)
        
        band_box = widgets.VBox(
            [widgets.Label('📡 Seleccione bandas para cruzar:')] + [chk for _, chk in band_items],
            layout=widgets.Layout(border='1px solid #333', padding='8px', border_radius='6px')
        )

        self.ui = widgets.VBox([
            title,
            widgets.HBox([self.w_sample_group, self.w_version, self.w_region]),
            widgets.HBox([
                widgets.VBox([self.w_iters, self.w_batch, self.w_lr, self.w_layers]),
                band_box
            ])
        ])

    def get_selection(self):
        layers_raw = self.w_layers.value.strip('[]').split(',')
        layers = [int(x.strip()) for x in layers_raw]
        
        bands = [b for b, chk in self.band_checkboxes.items() if chk.value]
        
        return {
            'sample_group': self.w_sample_group.value,
            'version_out': self.w_version.value,
            'region_out': self.w_region.value,
            'bands': bands,
            'hp': {
                'layers': layers,
                'lr': self.w_lr.value,
                'batch_size': self.w_batch.value,
                'n_iters': self.w_iters.value
            }
        }

    def show(self):
        display(self.ui)


def run_ui():
    """Iniciar la interfaz del entrenador del modelo."""
    ui = ModelTrainerUI()
    ui.show()
    return ui

def start_training(ui):
    if not isinstance(ui, ModelTrainerUI):
        print("⚠️ Se requiere el objeto devuelto por run_ui() de M4.")
        return
        
    config = ui.get_selection()
    sample_group = config['sample_group']
    bands = config['bands']
    hp = config['hp']
    
    print(f"🚀 Iniciando entrenamiento")
    print(f"   Grupo      : {sample_group}")
    print(f"   Bandas     : {bands} (NUM_INPUT={len(bands)})")
    
    from M3_sample_manager import load_sample_fc, samples_to_array
    
    fc = load_sample_fc(sample_group)
    print("   Extrayendo píxeles de mosaicos GEE (esto puede tardar)...")
    
    X, y = samples_to_array(fc, bands)
    if len(X) == 0:
        print("   ❌ Error: No se extrajeron muestras. Revise los mosaicos.")
        return
        
    print(f"   Muestras   : {len(X):,} reales. (quemado={y.sum():,}, no-quemado={(y==0).sum():,})")
    
    trainer = ModelTrainer(
        num_input=len(bands),
        layers=hp['layers'],
        lr=hp['lr']
    )
    trainer._bands_input = bands
    trainer._sample_count = {'burned': int(y.sum()), 'not_burned': int((y==0).sum())}
    trainer._sample_collection = sample_group
    
    import ipywidgets as widgets
    out = widgets.Output()
    display(out)
    
    trainer.train(X, y, batch_size=hp['batch_size'], n_iters=hp['n_iters'], out_widget=out)
    
    print("\n   💾 Entrenamiento completado. Guardando pesos en GCS...")
    hp_saved = trainer.save(version=config['version_out'], region=config['region_out'])
    
    print(f"✅ DNN guardada con éxito en versión {config['version_out']} - {config['region_out']}")
