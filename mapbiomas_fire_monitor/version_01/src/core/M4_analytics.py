import os, io
import json
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML, Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import time
from M0_auth_config import CONFIG, GLOBAL_OPTS, gcs_path, model_path
from M_cache import _get_fs
from M4_algorithms_dnn import ModelTrainer
from M_lang import L as Lang

def render_diagnostic_dashboard(history, embeds, preds, y_true, coords_override=None, save_path=None, viz_config=None):
    """
    Motor gráfico unificado para o grid 2x3 (Treino e Histórico).
    viz_config: dict com flags de visibilidade.
    """
    if viz_config is None:
        viz_config = {k: True for k in ['cm', 'history', 'prob', 'pr', 'pca2d', 'pca3d', 'pca3d_static', 'tsne3d_static']}
    from sklearn.metrics import confusion_matrix, precision_recall_curve, average_precision_score
    from sklearn.decomposition import PCA

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
    
    fig = Figure(figsize=(18, 4.5 * rows))
    
    for idx, ptype in enumerate(active_plots):
        if ptype == 'cm':
            ax = fig.add_subplot(rows, cols, idx + 1)
            ax.matshow(cm_norm, cmap='Blues', alpha=0.8, vmin=0, vmax=1)
            for (i, j), z in np.ndenumerate(cm):
                ax.text(j, i, f"{z:,}\n({cm_norm[i,j]:.1%})", ha='center', va='center', weight='bold', color='black' if cm_norm[i,j] < 0.5 else 'white')
            ax.set_title(Lang.CONFUSION_MATRIX, pad=15, weight='bold')
            ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
            ax.set_xticklabels([Lang.NO_FIRE, Lang.FIRE]); ax.set_yticklabels([Lang.NO_FIRE, Lang.FIRE])

        elif ptype == 'history':
            if history and 'steps' in history and len(history['steps']) > 0:
                ax = fig.add_subplot(rows, cols, idx + 1)
                ax.plot(history['steps'], history['acc'], color='#28a745', label='Acc', linewidth=2)
                if 'val_acc' in history: ax.plot(history['steps'], history['val_acc'], color='#28a745', label='Val', linestyle='--', alpha=0.6)
                ax.set_ylabel(Lang.ACCURACY, color='#28a745', weight='bold')
                axb = ax.twinx()
                axb.plot(history['steps'], history['loss'], color='#dc3545', label='Loss', linewidth=1.5, alpha=0.7)
                axb.set_ylabel(Lang.COST_LOSS, color='#dc3545', weight='bold')
                ax.set_title(Lang.HISTORICAL_EVOLUTION, weight='bold')
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
                ax.set_title(Lang.LATENT_PROJ_2D, weight='bold', fontsize=10)
                ax.set_xticks([]); ax.set_yticks([])

        elif ptype == 'prob':
            ax = fig.add_subplot(rows, cols, idx + 1)
            if len(preds_f) > 0 and len(y_true_f) > 0:
                ax.hist(preds_f[y_true_f==0], bins=30, alpha=0.5, color='#007bff', label=Lang.NO_FIRE, density=True)
                ax.hist(preds_f[y_true_f==1], bins=30, alpha=0.5, color='#ff4d4d', label=Lang.FIRE, density=True)
            ax.set_title(Lang.PROB_DISTRIBUTION, weight='bold', fontsize=10)
            ax.set_xlabel(Lang.CONFIDENCE); ax.legend(fontsize=8); ax.grid(True, alpha=0.2)

        elif ptype == 'pr':
            try:
                precision, recall, _ = precision_recall_curve(y_true_f, preds_f)
                ap_score = average_precision_score(y_true_f, preds_f)
                ax = fig.add_subplot(rows, cols, idx + 1)
                ax.plot(recall, precision, color='#17a2b8', linewidth=2, label=f'AP={ap_score:.3f}')
                ax.fill_between(recall, precision, alpha=0.2, color='#17a2b8')
                ax.set_title(Lang.VIZ_PR_CURVE, weight='bold', fontsize=10)
                ax.set_xlabel(Lang.RECALL); ax.legend(loc='lower left', fontsize=8); ax.grid(True, alpha=0.3)
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
                t = Lang.PCA_3D if is_pca else Lang.TSNE_3D
                ax.set_title(f"{t} (Ang {azim}deg)", fontsize=9, weight='bold')
                ax.set_xticks([]); ax.set_yticks([]); ax.set_zticks([])

    fig.tight_layout()
    if not save_path:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        display(Image(buf.getvalue(), format='png'))
        plt.close(fig)

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=100, bbox_inches='tight')

def render_model_card_html(hp, metrics, only_header=False):
    """Gera o HTML dos cards de metadados sem emojis.
    only_header=True: apenas o cabeçalho.
    only_header=False: card principal + card colapsável com todos os parâmetros.
    """
    import hashlib
    _uid = hashlib.md5(str(hp.get('training_id', '')).encode()).hexdigest()[:8]
    style = """
    <style>
        .dash-card-header { background: #2c3e50; color: white; padding: 10px 15px; font-size: 14px; font-weight: bold; border-radius: 8px 8px 0 0; border: 1px solid #2c3e50; }
        .dash-card-body { border: 1px solid #dee2e6; border-top: none; background: white; padding: 15px; font-family: sans-serif; }
        .meta-text { margin: 3px 0; font-size: 12px; color: #444; }
        .meta-label { font-weight: bold; color: #222; width: 110px; display: inline-block; }
        .dash-card-advanced { border: 1px solid #dee2e6; background: #f8f9fa; padding: 15px; font-family: sans-serif; border-radius: 0 0 8px 8px; margin-top: -1px; }
        .dash-toggle { cursor: pointer; color: #3498db; font-size: 12px; text-decoration: none; display: inline-block; margin-top: 8px; }
        .dash-toggle:hover { text-decoration: underline; }
    </style>
    """
    if only_header:
        return f"{style}<div class='dash-card-header'>{Lang.MODEL}: {hp.get('training_id')} / {hp.get('shortname')}</div>"

    date_str = hp.get('training_date', Lang.TRAINING_IN_PROGRESS)
    if date_str and 'T' in date_str: date_str = date_str[:16].replace('T', ' ')

    rep = metrics.get('classification_report', {}) if metrics else {}
    acc = f"{rep.get('accuracy', 0):.1%}"
    f1 = f"{rep.get('1', {}).get('f1-score', 0):.1%}"

    n_iters = hp.get('n_iters', '?')
    batch   = hp.get('batch_size', '?')
    lr      = hp.get('lr', '?')
    layers  = hp.get('layers', '?')
    sensor  = hp.get('sensor', GLOBAL_OPTS.get('SENSOR', ['?'])[0])

    param_rows = ""
    for k, v in sorted(hp.items()):
        if k in ('history', 'metrics', 'norm_stats', 'bands_config', 'sample_count', 'global_opts', '_last_saved_metadata'):
            continue
        if isinstance(v, (dict, list)):
            v_str = json.dumps(v, default=str)
        else:
            v_str = str(v)
        param_rows += f"<tr><td style='padding:2px 8px; font-weight:bold; color:#555; vertical-align:top; white-space:nowrap;'>{k}</td><td style='padding:2px 8px; color:#333; word-break:break-all; font-family:monospace; font-size:11px;'>{v_str}</td></tr>"

    main_card = f"""
    <div class="dash-card-body">
        <div style="display: flex; flex-wrap: wrap; gap: 15px;">
            <div style="flex: 2; min-width: 300px;">
                <p class="meta-text"><span class="meta-label">{Lang.DATE}:</span> {date_str}</p>
                <p class="meta-text"><span class="meta-label">{Lang.SENSOR}:</span> {sensor}</p>
                <p class="meta-text"><span class="meta-label">{Lang.LAYERS_LABEL}</span> {layers} | <b>{Lang.LR_ABBR}</b> {lr}</p>
                <p class="meta-text"><span class="meta-label">{Lang.ITERATIONS}:</span> {n_iters} | <b>{Lang.BATCH_SIZE}:</b> {batch}</p>
                <p class="meta-text"><span class="meta-label">{Lang.ACCURACY}:</span> {acc} | <b>{Lang.F1_SCORE}:</b> {f1}</p>
                <p class="meta-text"><span class="meta-label">{Lang.SAMPLES_LABEL}</span> {', '.join(hp.get('sample_collections', []))}</p>
                <div style="margin-top:8px; padding:8px; background:#fff3cd; border-radius:4px; border:1px solid #ffeeba;">
                    <p class="meta-text" style="color:#856404; font-weight:bold; margin-bottom:3px;">{Lang.COMMENTS}:</p>
                    <p class="meta-text" style="color:#856404; font-style:italic;">{hp.get('comment', Lang.NO_COMMENTS)}</p>
                </div>
            </div>
        </div>
        <a class="dash-toggle" onclick="
            var el = document.getElementById('advanced_params_{_uid}');
            var btn = this;
            if (el.style.display === 'none' || el.style.display === '') {{
                el.style.display = 'block';
                btn.innerText = '{Lang.HIDE_ADVANCED}';
            }} else {{
                el.style.display = 'none';
                btn.innerText = '{Lang.SHOW_ALL_PARAMS}';
            }}
        ">{Lang.SHOW_ALL_PARAMS}</a>
    </div>
    <div id="advanced_params_{_uid}" class="dash-card-advanced" style="display:none;">
        <table style="width:100%; border-collapse:collapse;">{param_rows}</table>
    </div>
    """
    return style + main_card

def view_analytics(model_info, out_widget=None, clear_before=True, viz_config=None, epoch_index=None, hp_override=None, ui=None):
    """
    Visualiza as métricas e o card de um modelo salvo no GCS.
    viz_config: dict opcional com flags de visibilidade.
    epoch_index: índice da época para renderizar dados passados (Time Machine).
    hp_override: dict opcional com metadados para evitar leitura do GCS (pós-treino).
    """
    if viz_config is None:
        viz_config = {k: True for k in ['title', 'scores', 'cm', 'history', 'prob', 'pr', 'pca2d', 'pca3d', 'tsne3d']}
    
    fs = _get_fs()
    from M0_auth_config import CONFIG, gcs_models_path
    try:
        import urllib.parse
        m_path = model_info.get('path')
        if not m_path:
            m_path = f"{gcs_models_path()}/{model_info['training_id']}"
        m_path = urllib.parse.unquote(m_path)
        clean_path = m_path
        # Handle gs://bucket/ prefix
        gs_prefix = f'gs://{CONFIG["bucket"]}/'
        if clean_path.startswith(gs_prefix):
            clean_path = clean_path[len(gs_prefix):]
        # Handle gcsfs internal path: b/<bucket>/o/<path>
        elif '/o/' in clean_path:
            idx = clean_path.find('/o/')
            clean_path = clean_path[idx + 3:]
        clean_path = clean_path.lstrip('/')

        # clean_path pode ser o dir do modelo ou ja apontar para metadata.json
        meta_suffix = '/metadata.json'
        has_meta = clean_path.endswith(meta_suffix)
        base_dir = clean_path[:-len(meta_suffix)] if has_meta else clean_path

        if hp_override:
            hp = hp_override
            metrics = hp.get('metrics', {})
        else:
            # 1. Carrega Metadados e Métricas Base
            meta_path = clean_path if has_meta else f"{clean_path}/metadata.json"
            with fs.open(f"{CONFIG['bucket']}/{meta_path}", 'r') as f: hp = json.load(f)
            try:
                with fs.open(f"{CONFIG['bucket']}/{base_dir}/metrics.json", 'r') as f: metrics = json.load(f)
            except Exception:
                metrics = {}
                display(HTML(f"<i style='color:#7f8c8d;'>{Lang.NO_METRICS}</i>"))
        # 2. Carrega Dados de Snapshots para o Time Machine se solicitado
        snap_data = None
        if epoch_index is not None:
            try:
                with fs.open(f"{CONFIG['bucket']}/{base_dir}/history/snapshots_data.npz", 'rb') as f:
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

            kpi_acc = make_kpi_card(Lang.ACCURACY, f"{rep.get('accuracy', 0):.1%}", "#2c3e50", icon="crosshairs")
            kpi_prec = make_kpi_card(Lang.PRECISION, f"{rep.get('1', {}).get('precision', 0):.1%}", "#8e44ad", icon="bullseye")
            kpi_rec = make_kpi_card(Lang.RECALL, f"{rep.get('1', {}).get('recall', 0):.1%}", "#e67e22", icon="search-plus")
            kpi_f1 = make_kpi_card(Lang.F1_SCORE, f"{rep.get('1', {}).get('f1-score', 0):.1%}", "#16a085", icon="balance-scale")
            kpi_auto = make_kpi_card(Lang.AI_NOTE, f"{a_rating}/5", "#34495e", icon="flash")

            # Nota Humana Interativa no KPI
            user_stars_container = widgets.HBox([], layout=widgets.Layout(margin='0', align_items='center'))
            def _show_stars():
                btns = []
                for i in range(1, 6):
                    btn = widgets.Button(description="" if i <= h_rating else "", 
                                       layout=widgets.Layout(width='22px', height='22px', margin='0', padding='0'),
                                       style={'button_color': '#f1c40f' if i <= h_rating else '#fff'})
                    def _hnd_click(b, val=i):
                        btn_ok = widgets.Button(description=Lang.OK, layout=widgets.Layout(width='35px', height='22px'), button_style='success')
                        btn_no = widgets.Button(description=Lang.BTN_CLOSE, layout=widgets.Layout(width='25px', height='22px'), button_style='danger')
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
                widgets.HTML(f"<div style='font-size: 10px; color: #7f8c8d; text-transform: uppercase; font-weight: bold; margin-bottom: 2px;'>{Lang.HUMAN_NOTE}</div>"),
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
                display(HTML(f"<h4 style='color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px; margin-top:20px;'> {Lang.VIZ_MANAGEMENT}</h4>"))

                btn_retrain = widgets.Button(description=Lang.RETRAIN, icon="refresh", layout=widgets.Layout(width='120px'), button_style='danger')
                def _on_retrain(_):
                    if ui:
                        ui.retrain_intent = {'mode': 'borrar', 'hp': hp}
                        ui._load_config_into_widgets(hp)
                        ui.tab.selected_index = 1
                btn_retrain.on_click(_on_retrain)

                del_out = widgets.Output()
                def _show_del_btn():
                    del_out.clear_output()
                    btn_del = widgets.Button(description=Lang.DELETE_MODEL, icon="trash", layout=widgets.Layout(width='140px'), button_style='danger')
                    def _on_del_click(_):
                        import threading
                        btn_conf = widgets.Button(description=Lang.CONFIRM, button_style='warning', layout=widgets.Layout(width='100px'))
                        btn_canc = widgets.Button(description=Lang.BTN_CLOSE, button_style='info', layout=widgets.Layout(width='30px'))
                        msg = widgets.HTML("<span style='color:red; font-size:10px; margin-left:5px;'>5s</span>")
                        del_out.clear_output()
                        with del_out: display(widgets.HBox([btn_conf, btn_canc, msg]))
                        stop = [False]
                        def _do_conf(_):
                            stop[0] = True
                            del_out.clear_output()
                            with del_out: display(widgets.HTML(f"<i>{Lang.DELETING}</i>"))
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
                        threading.Thread(target=_timer, daemon=False).start()
                    btn_del.on_click(_on_del_click)
                    with del_out: display(btn_del)
                _show_del_btn()

                display(widgets.HBox([btn_retrain, widgets.HTML("<div style='width:20px'></div>"), del_out], 
                                    layout=widgets.Layout(margin='5px 0 15px 0', align_items='center')))

            # --- GRUPOS DE GRÁFICOS ---
            # 1. MÉTRICAS CLÁSSICAS (Incluindo Estáticas 3D)
            classic_keys = ['cm', 'history', 'prob', 'pr', 'pca3d_static', 'tsne3d_static']
            if any(viz_config.get(k) for k in classic_keys):
                display(HTML(f"<h4 style='color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px;'> {Lang.CLASSIC_METRICS}</h4>"))
                
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
                display(HTML(f"<h4 style='color:#7f8c8d; border-bottom:1px solid #eee; padding-bottom:5px; margin-top:20px;'> {Lang.INTERACTIVE_LATENT}</h4>"))
                import plotly.graph_objects as go
                fire_colorscale = [[0, '#2c3e50'], [0.5, '#bdc3c7'], [1, '#e67e22']]
                
                out_pca = widgets.Output(layout=widgets.Layout(width='50%'))
                out_tsne = widgets.Output(layout=widgets.Layout(width='50%'))
                display(widgets.HBox([out_pca, out_tsne], layout=widgets.Layout(width='100%')))

                if viz_config.get('pca3d') and pca_coords_final is not None and len(pca_coords_final) > 0:
                    fig_pca = go.Figure(data=[go.Scatter3d(
                        x=pca_coords_final[:,0], y=pca_coords_final[:,1], z=pca_coords_final[:,2], mode='markers',
                        marker=dict(size=3, color=preds_final, colorscale=fire_colorscale, opacity=0.7),
                        text=[f"{l}<br>Pred: {p:.2%}" for l, p in zip(y_true_final, preds_final)]
                    )])
                    fig_pca.update_layout(title=Lang.PCA_3D_INTERACTIVE, margin=dict(l=0, r=0, b=0, t=30), height=400)
                    with out_pca: display(HTML(fig_pca.to_html(include_plotlyjs=True, full_html=False)))

                if viz_config.get('tsne3d') and tsne_coords_final is not None and len(tsne_coords_final) > 0:
                    fig_tsne = go.Figure(data=[go.Scatter3d(
                        x=tsne_coords_final[:,0], y=tsne_coords_final[:,1], z=tsne_coords_final[:,2], mode='markers',
                        marker=dict(size=3, color=preds_final, colorscale=fire_colorscale, opacity=0.7),
                        text=[f"{l}<br>Pred: {p:.2%}" for l, p in zip(y_true_final, preds_final)]
                    )])
                    fig_tsne.update_layout(title=Lang.TSNE_3D_INTERACTIVE, margin=dict(l=0, r=0, b=0, t=30), height=400)
                    with out_tsne: display(HTML(fig_tsne.to_html(include_plotlyjs=True, full_html=False)))

            # --- TENSORBOARD PROJECTOR ---
            # (Opcional: Adicionar links se necessário)

        if out_widget:
            if clear_before: out_widget.clear_output(wait=True)
            with out_widget: _render_content()
        else:
            _render_content()
    except Exception as e:
        msg = f"[ERR] Error loading analytics: {e}"
        if out_widget:
            with out_widget: print(msg)
        else: print(msg)

