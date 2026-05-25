import os
import json
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
from M0_auth_config import CONFIG, GLOBAL_OPTS, gcs_path, model_path
from M_cache import CacheManager, _get_fs
from M_ui_components import PipelineStepUI, make_spinner, Layout, make_empty_state, make_sync_button, make_select_all_none, make_search_box
from M_lang import L as Lang

from M4_data_extractor import extract_pixels_from_gcs, list_sample_collections_gcs, list_campaigns_gcs
from M4_algorithms_dnn import ModelTrainer, _get_tf
from M4_analytics import view_analytics, render_diagnostic_dashboard, render_model_card_html
from M4_hub_manager import list_trained_models, _load_m4_metadata, _save_m4_metadata
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
            description=Lang.APPLY_VISIBILITY, icon="play",
            button_style='success', layout=widgets.Layout(width='180px')
        )
        self.w_apply_btn.on_click(lambda _: self._update_canvas())
        
        # Sidebar containers
        self.canvas_available_box = widgets.VBox([], layout=widgets.Layout(flex='1', border='1px solid #ddd', overflow_y='auto'))
        self.canvas_selected_box = widgets.VBox([], layout=widgets.Layout(flex='1', border='1px solid #ddd', overflow_y='auto'))
        
        self.main_area.children = [widgets.HTML(f"<i>{Lang.LOADING_INTERFACE}</i>")]

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
            widgets.HTML(f"<h2 style='color:#2c3e50;'> 1. {Lang.SAMPLE_SELECTION}</h2>"),
            self.samples_area,
            widgets.HTML(f"<br><h2 style='color:#2c3e50;'> 2. {Lang.EXTRACTION_TITLE}</h2>"),
            self.extraction_area,
            widgets.HTML(f"<br><h2 style='color:#2c3e50;'> 3. {Lang.MODEL_CONFIG}</h2>"),
            hp_sec,
            widgets.HTML(f"<br><h2 style='color:#2c3e50;'> 4. {Lang.GCS_DEST}</h2>"),
            dest_sec,
        ], layout=widgets.Layout(padding='20px', background_color='white'))
        
        # 2. CANVAS (Visualização + Ranking Sidebar)
        # --- SIDEBAR (ESQUERDA) ---
        self.w_canvas_search = widgets.Text(placeholder=Lang.SEARCH_REPO, layout=widgets.Layout(width='100%'))
        self.w_canvas_search.observe(lambda c: self._on_canvas_search_change(c['new']), names='value')
        
        self.w_canvas_sort = widgets.Dropdown(
            options=[('Acurácia', 'acc'), ('F1-Fire', 'f1'), ('ID', 'id')],
            value=self.canvas_sort_col,
            description=Lang.SORT_BY,
            layout=widgets.Layout(width='100%'),
            style={'description_width': '60px'}
        )
        def _on_sort_change(change):
            self.canvas_sort_col = change['new']
            self._refresh_canvas_hub()
        self.w_canvas_sort.observe(_on_sort_change, names='value')

        btn_sync, _ = make_sync_button(Lang.REPO_SYNC, "refresh", lambda: self._sync_repository(show_loader=True, force_refresh=True), width='100%', button_style='primary')

        btn_all_canvas = widgets.Button(description=Lang.ALL, icon="check-square", layout=widgets.Layout(width='48%'), button_style='info')
        btn_none_canvas = widgets.Button(description=Lang.CLEAR, icon="square-o", layout=widgets.Layout(width='48%'), button_style='warning')
        btn_all_canvas.on_click(lambda _: self._on_canvas_batch_action('all'))
        btn_none_canvas.on_click(lambda _: self._on_canvas_batch_action('none'))
        
        sidebar_vbox = widgets.VBox([
            widgets.HTML(f"<b style='font-size:13px; color:#2c3e50;'> {Lang.REPO_TITLE}</b>"),
            self.w_canvas_search,
            self.w_canvas_sort,
            btn_sync,
            self.canvas_available_box,
            widgets.HBox([btn_all_canvas, btn_none_canvas], layout=widgets.Layout(justify_content='space-between', margin='5px 0')),
            widgets.HTML(f"<b style='font-size:13px; color:#2c3e50; margin-top:10px;'> {Lang.SELECTED_CANVAS}</b>"),
            self.canvas_selected_box
        ], layout=widgets.Layout(width='320px', padding='10px', background_color='#fcfcfc', border_right='2px solid #eee'))

        main_canvas_vbox = widgets.VBox([
            widgets.HTML(f"<h3 style='color:#2c3e50; margin:0 0 10px 0;'> {Lang.CANVAS_TITLE}</h3>"),
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
        self.tab.set_title(0, f' {Lang.USAGE_GUIDE}')
        self.tab.set_title(1, f' {Lang.NEW_TRAINING}')
        self.tab.set_title(2, f' {Lang.TRAININGS}')
        
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
        self.canvas_search_query = change['new']
        self._refresh_canvas_hub()

    def _on_sort_change(self, change):
        if change['name'] == 'value':
            self.canvas_sort_col = change['new']
            self._refresh_canvas_hub()
            
    def _on_sort_order_change(self, change):
        self.canvas_sort_asc = not self.canvas_sort_asc
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
            return make_empty_state('No se han encontrado resultados con este filtro.', padding='10px')
            
        return widgets.VBox(matrix_rows)

    def _build_matrix(self):
        L = widgets.Layout
        css = PipelineStepUI.get_status_css()
        
        # BARRA DE BUSCA E SELETOR DE CAMPANHA
        self.txt_search_samples = widgets.Text(
            value=self.search_query_samples,
            placeholder=Lang.SEARCH_SAMPLES,
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
            # Limpa cache de sample_collections para forçar refresh real
            state = CacheManager.get_state()
            if state.get('sample_collections'):
                state['sample_collections'] = []
                CacheManager._state = state
                CacheManager.save()
            # Refresh UI
            self._refresh_samples_panes()
            
        self.w_campaign.observe(_on_campaign_change, names='value')

        btn_all, btn_none, _ = make_select_all_none(self._on_select_all_samples, self._on_select_none_samples)
        
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
                btn = widgets.Button(description=f" {s}", layout=L(width='100%', min_height='28px', margin='1px 0'), style={'button_color': '#e3f2fd'})
                def _remove(b, name=s):
                    self.chk_dict[name].value = False
                    self._refresh_samples_panes()
                btn.on_click(_remove)
                selected_widgets.append(btn)
        
        self.selected_samples_container.children = selected_widgets

    def _build_extraction_matrix(self):
        """Constrói a matriz dinâmica priorizando o cache local 'state.json'."""
        L = widgets.Layout
        
        # --- CABEÇALHO COM BOTÃO DE SYNC ---
        def _sync_body():
            print(Lang.REPO_SCANNING)
            CacheManager.build_cache_from_gcs()
            self._refresh_matrix_only()
            print(Lang.REPO_SCAN_DONE)

        btn_sync, sync_out = make_sync_button(Lang.SYNC_CATALOG, "sync", _sync_body, width='220px', height='30px')
        
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
                ('sentinel2', 'minnbr', 'mensal'): set(['red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']),
                ('sentinel2', 'minnbr_buffer', 'mensal'): set(['red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear']),
                ('landsat', 'minnbr', 'mensal'): set(['red', 'nir', 'swir1', 'swir2', 'nbr', 'ndvi', 'dayOfYear'])
            }

        if not available_combos:
            return make_empty_state('No se han encontrado COGs en el repositorio GCS.')

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
                if s == 'sentinel2' and m == 'minnbr' and b in ('red', 'nir', 'swir1', 'swir2'): chk.value = True
                
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
        self.w_training_id = widgets.Text(value=next_id, description=Lang.TRAINING_ID, style={'description_width': '120px'}, layout=L(width='300px'))
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

        self.w_comment = widgets.Textarea(placeholder=Lang.COMMENTS, layout=L(width='98%', height='60px'))
        
        return widgets.VBox([
            widgets.HTML("<b style='font-size:14px; color:#2c3e50;'>Destino de los Resultados</b>"),
            widgets.HBox([self.w_training_id, self.w_shortname], layout=L(gap='15px')),
            self.w_comment,
        ], layout=L(padding='15px', border='1px solid #eee', border_radius='8px', margin='0 0 15px 0'))

    def _refresh_ui(self):
        self._refresh_canvas_hub()
        

    def make_spinner(self, msg=Lang.LOADING):
        return make_spinner(msg=msg)

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
        
        cache = _load_m4_metadata()
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
                    except Exception as e:
                        pass  # metrics.json é opcional
                    
                    metadata_cache[m_id] = meta
                    updated_cache = True
                except Exception as e:
                    print(f"[WARN] Erro ao carregar metadados de {m_id}: {e}")
        
        if updated_cache:
            cache['metadata'] = metadata_cache
            _save_m4_metadata(cache)
            
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
        with self._live_plots_out:
            self._live_plots_out.clear_output(wait=True)

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
        cache = _load_m4_metadata()
        
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
            'title': Lang.VIZ_METADATA, 'scores': Lang.VIZ_KPIS, 'cm': Lang.VIZ_CONFUSION, 
            'history': Lang.VIZ_HISTORY, 'prob': Lang.VIZ_PROB, 'pr': Lang.VIZ_PR_CURVE, 
            'pca2d': 'PCA 2D', 'pca3d_static': 'PCA 3D (Est)', 'pca3d': 'PCA 3D (Int)',
            'tsne3d_static': 't-SNE 3D (Est)', 'tsne3d': 't-SNE 3D (Int)',
            'management': Lang.VIZ_MANAGEMENT
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
        row5 = _make_row(Lang.VIZ_MANAGEMENT, ['management'])
        
        chk_container = widgets.VBox([row1, row2, row3, row4, row5])
        
        # 3. Botões de Ação na parte inferior
        btn_all = widgets.Button(description=Lang.ALL, layout=L(width='70px'), button_style='info')
        btn_none = widgets.Button(description=Lang.NONE, layout=L(width='70px'), button_style='warning')
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
                display(HTML(f"<div style='padding:100px; text-align:center; background:white; border-radius:8px;'> <span style='font-size:50px;'></span><br><h3 style='color:#999;'>{Lang.CANVAS_EMPTY}</h3><p style='color:#ccc;'>{Lang.CANVAS_HINT}</p></div>"))
                return
            
            # --- AJUSTE DINÂMICO DO SLIDER GLOBAL ---
            max_steps = 1
            for mid, info in self.selected_models.items():
                hp_override = info.get('_hp_override')
                h = hp_override.get('history', {}) if hp_override else info.get('history', {})
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
                    view_analytics(info, out_widget=None, clear_before=False, viz_config=self.viz_config, epoch_index=self.canvas_slider_val, hp_override=info.get('_hp_override'))
                cards.append(card_out)
            
            # Grid responsivo: ocupa o espaço disponível, quebrando linhas conforme necessário
            grid = widgets.GridBox(cards, layout=widgets.Layout(
                grid_template_columns='repeat(auto-fill, minmax(550px, 1fr))',
                grid_gap='20px',
                width='100%'
            ))
            display(grid)

def start_training(ui):
    tf_avail = _get_tf(force=True)
    if tf_avail is None:
        print("\n" + "="*70)
        print(" [WARNING] INCOMPATIBLE LOCAL ENVIRONMENT")
        print(" Your CPU does not support AVX/AVX2 instructions required by TensorFlow.")
        print(" PLEASE: Run this training on Google Colab.")
        print("="*70 + "\n")
        return
    # -----------------------------------------------------------------
    # 1 Retraining intent (checked via the UI state)
    # -----------------------------------------------------------------
    intent = ui.retrain_intent
    if intent.get('mode'):
        hp = intent.get('hp')
        
        # Determine training ID and shortname for the target model
        target_id = hp['training_id'] if hp else ui.w_training_id.value
        target_short = hp['shortname'] if hp else ui.w_shortname.value
        
        # If 'borrar' mode is selected, delete the target model first.
        if intent['mode'] == 'borrar':
            print(f" Deleting previous model: {target_id} ({target_short})")
            ModelTrainer.delete_model(target_id, target_short)
            
        # If hp is provided, load its full configuration into the widgets.
        if hp:
            ui._load_config_into_widgets(hp)
            selected_samples = hp.get('sample_collections', [])
            
        print(f" Mode '{intent['mode']}' activated for {target_id}")
        
        # Reset the intent so it does not fire again accidentally.
        ui.retrain_intent = {'mode': None, 'hp': None}
        # Reset the checkboxes visually too
        for cb in [ui.cb_retrain, ui.cb_reextract, ui.cb_borrar_retrain]:
            cb.unobserve(ui._on_intent_cb_change, names='value')
            cb.value = False
            cb.observe(ui._on_intent_cb_change, names='value')
    
    # 2 Get parameters from UI
    if not intent.get('mode') or not hp:
        selected_samples = [name for name, chk in ui.chk_dict.items() if chk.value]

    if not selected_samples:
        print("Error: No samples selected.")
        return

    # 3 Constrói o dicionário de configuração de bandas a partir da Matriz Dinâmica
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
        print("Error: No bands selected in the Extraction Matrix.")
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

    try:
        layers = [int(x.strip()) for x in ui.w_layers.value.split(',')]
        iters = int(ui.w_iters.value)
        batch = int(ui.w_batch.value)
        lr = float(ui.w_lr.value)
    except ValueError as e:
        print(f"Error: Valor inválido nos hiperparâmetros: {e}")
        return
    
    print(f"Extracting pixels from {len(selected_samples)} collections using Flexible Matrix ({len(bands_config)} bands). Please wait...")
    
    def _logger(msg, level="info"):
        print(msg)
        
    X, y = extract_pixels_from_gcs(selected_samples, bands_config, logger=_logger)
    
    if len(X) == 0:
        print("Failed to extract pixels.")
        return
        
    print(f"Success: {len(X)} pixels extracted (Fire: {y.sum()} | No-fire: {(y==0).sum()}).")
    
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    ui.trainer_instance = ModelTrainer(num_input=len(bands_config), layers=layers, lr=lr)
    ui.trainer_instance._bands_input = sorted(bands_config.keys())
    ui.trainer_instance._bands_config = bands_config
    ui.trainer_instance._sample_collections = selected_samples
    ui.trainer_instance._sample_count = {'burned': int(y.sum()), 'not_burned': int((y==0).sum())}
    
    print("Training DNN...")
    
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
    print("\n Training completed. Generating high-resolution t-SNE audit...")
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
            
            print("  - Computing t-SNE manifold (this may take a while)...")
            tsne = TSNE(n_components=3, perplexity=30, random_state=42, max_iter=1000)
            coords_tsne = tsne.fit_transform(emb_v)
            
            ui.trainer_instance.tsne_snapshot = coords_tsne.tolist()
            
            print("  - Generating interactive figure...")
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
            print("[OK] t-SNE audit ready.")
        except Exception as e:
            print(f"[WARNING] Could not generate final t-SNE: {e}")

    print("Saving structure (samples, pixels, metadata, metrics) to GCS...")
    try:
        saved_meta = ui.trainer_instance.save(ui.w_training_id.value, ui.w_shortname.value, comment=ui.w_comment.value, logger=_logger)
        print("Model and Model Card saved successfully!")
        
        # Inserir o modelo fresquinho na Mesa do Canvas automaticamente
        final_id = f"training_{ui.w_training_id.value}_{ui.w_shortname.value}_{GLOBAL_OPTS['SENSOR'][0].lower()}"
        ui.selected_models = {
            final_id: {
                'training_id': final_id,
                'path': model_path(ui.w_training_id.value, ui.w_shortname.value),
                '_hp_override': saved_meta
            }
        }
        
        ui.live_training_info = None  # Remove o status de LIVE após conclusão
        ui._live_initialized = False
        ui._sync_repository(show_loader=False)
        ui._update_canvas()  # Pinta o card final!
        
    except Exception as e:
        print(f"Error saving: {e}")

def run_ui():
    ui = ModelTrainerUI()
    ui.display()
    return ui

