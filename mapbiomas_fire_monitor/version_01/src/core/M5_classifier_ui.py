import os
import json
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from M0_auth_config import CONFIG, _get_fs

def get_queue_file():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_dir, 'm5_queue.json')

def load_queue():
    q_file = get_queue_file()
    if os.path.exists(q_file):
        with open(q_file, 'r') as f:
            return json.load(f)
    return []

def save_queue(q):
    with open(get_queue_file(), 'w') as f:
        json.dump(q, f, indent=2)

class M5QueueUI:
    def __init__(self, years=None, peridiocity_active=None):
        self.years = years or [2025, 2026]
        self.peridiocity_active = peridiocity_active or ['monthly']
        self.queue = load_queue()
        
        # --- WIDGETS DE CADASTRO ---
        self.w_model_box = widgets.VBox()
        self.w_region_box = widgets.VBox()
        self.w_period_box = widgets.VBox()
        
        self.chk_models = []
        self.chk_regions = []
        self.chk_periods = []
        
        self.btn_add = widgets.Button(description='Añadir Lote a la Cola', button_style='primary', icon='plus', layout=widgets.Layout(width='200px'))
        self.btn_add.on_click(self._on_add_click)
        
        self.btn_refresh = widgets.Button(description='Actualizar Vista', icon='refresh', layout=widgets.Layout(width='150px'))
        self.btn_refresh.on_click(lambda _: self._refresh_ui())
        
        self.btn_clear = widgets.Button(description='Limpiar Cola', button_style='danger', icon='trash', layout=widgets.Layout(width='150px'))
        self.btn_clear.on_click(self._on_clear_click)
        
        # --- TABS ---
        self.w_pend_rows = widgets.VBox()
        self.w_comp_rows = widgets.VBox()
        self.w_guide = widgets.HTML()
        
        self.tab_pending = widgets.VBox()
        self.tab_completed = widgets.VBox()
        
        self.tabs = widgets.Tab(children=[self.w_guide, widgets.VBox(), self.tab_pending, self.tab_completed])
        self.tabs.set_title(0, 'Guia')
        self.tabs.set_title(1, 'Cadastrar')
        self.tabs.set_title(2, 'Pendentes')
        self.tabs.set_title(3, 'Concluidas')
        
        self.out_msg = widgets.Output()
        
        # --- FILTROS (Pendientes) ---
        self.f_pend_model = widgets.Dropdown(description='Modelo:', options=['Todos'], layout=widgets.Layout(width='250px'))
        self.f_pend_region = widgets.Dropdown(description='Región:', options=['Todas'], layout=widgets.Layout(width='250px'))
        self.f_pend_year = widgets.Dropdown(description='Año:', options=['Todos'], layout=widgets.Layout(width='200px'))
        for f in [self.f_pend_model, self.f_pend_region, self.f_pend_year]:
            f.observe(lambda _: self._render_pending(), names='value')
            
        # --- FILTROS (Concluidas) ---
        self.f_comp_model = widgets.Dropdown(description='Modelo:', options=['Todos'], layout=widgets.Layout(width='250px'))
        self.f_comp_region = widgets.Dropdown(description='Región:', options=['Todas'], layout=widgets.Layout(width='250px'))
        self.f_comp_year = widgets.Dropdown(description='Año:', options=['Todos'], layout=widgets.Layout(width='200px'))
        for f in [self.f_comp_model, self.f_comp_region, self.f_comp_year]:
            f.observe(lambda _: self._render_completed(), names='value')

        guide_html = """
        <div style='padding:20px; font-family:sans-serif;'>
            <h3 style='color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:5px;'>M5 - Clasificación Regional de Larga Escala</h3>
            <p>Este módulo permite clasificar múltiples regiones geográficas (cartas <b>cim-world-1-250000</b>) a lo largo de diferentes meses y años, utilizando los modelos de Inteligencia Artificial entrenados en el módulo M4.</p>
            <h4>Flujo de Trabajo:</h4>
            <ol style='line-height:1.6;'>
                <li>Vaya a la pestaña <b>Cadastrar</b>.</li>
                <li>Seleccione un modelo base entrenado en la biblioteca.</li>
                <li>Seleccione múltiples <b>Regiones y Períodos</b> en la cuadrícula de opciones.</li>
                <li>Haga clic en <b>Añadir Lote a la Cola</b> para generar todas las combinaciones cartesianas automáticamente.</li>
                <li>Acompañe el progreso en las pestañas de <b>Pendientes</b> y <b>Concluidas</b>.</li>
                <li>Para iniciar el procesamiento en segundo plano, ejecute la celda <code>run_m5_queue()</code> en su Notebook.</li>
            </ol>
        </div>
        """
        self.w_guide = widgets.HTML(value=guide_html)
        
        self._populate_dropdowns()
        
    def _create_checkbox_grid(self, options, description, single_select=False, bg_color='#fafafa', columns=None):
        title = widgets.HTML(f"<div style='margin-bottom:5px; color:#2c3e50;'><b>{description}</b></div>")
        checkboxes = []
        for opt in options:
            chk = widgets.Checkbox(value=False, description=str(opt), indent=False, style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', margin='0 5px 5px 0'))
            checkboxes.append(chk)
            
        if single_select:
            def on_change(change, current_chk):
                if change['new']:
                    for c in checkboxes:
                        if c != current_chk:
                            c.value = False
            for chk in checkboxes:
                chk.observe(lambda change, c=chk: on_change(change, c), names='value')
                
        gtc = f"repeat({columns}, 1fr)" if columns else "repeat(auto-fill, minmax(280px, 1fr))"
        grid = widgets.GridBox(checkboxes, layout=widgets.Layout(grid_template_columns=gtc, width='100%'))
        container = widgets.VBox([title, grid], layout=widgets.Layout(margin='0 0 15px 0', padding='10px', border='1px solid #ccc', border_radius='5px', background_color=bg_color))
        return container, checkboxes

    def _populate_dropdowns(self):
        # 1. Models
        try:
            from M4_model_trainer import list_trained_models
            models = list_trained_models()
        except Exception as e:
            models = []
            
        box, self.chk_models = self._create_checkbox_grid(models, "1. Seleccione Modelo (Única):", single_select=True, bg_color='#e8f4fd')
        self.w_model_box.children = box.children
        
        # 2. Regions from GEE
        regions = ['Peru', 'Amazonia', 'Cerrado'] # Fallback
        try:
            import ee
            if not getattr(ee.data, '_credentials', None):
                from M0_auth_config import authenticate
                authenticate()
            asset = CONFIG.get('asset_regions', 'projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000') 
            fc = ee.FeatureCollection(asset)
            names = fc.aggregate_array('region_nam').distinct().getInfo()
            if names:
                regions = sorted([n for n in names if n])
        except Exception as e:
            print("EE fetch error (using fallback):", e)
            
        box, self.chk_regions = self._create_checkbox_grid(regions, "2. Seleccione Regiones:", bg_color='#fdf7e8')
        self.w_region_box.children = box.children
        
        # 3. Periods
        import datetime
        now = datetime.datetime.now()
        
        periods = []
        for y in self.years:
            if "yearly" in self.peridiocity_active:
                if y < now.year:
                    periods.append(str(y))
            if "monthly" in self.peridiocity_active:
                max_m = (now.month - 1) if y == now.year else (12 if y < now.year else 0)
                for m in range(1, max_m + 1):
                    periods.append(f"{y}_{m:02d}")
                    
        periods.sort(reverse=True)
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Períodos (Año / Año_Mes):", bg_color='#ebf5eb', columns=4)
        self.w_period_box.children = box.children

    def _on_add_click(self, b):
        model = next((c.description for c in self.chk_models if c.value), None)
        regions = [c.description for c in self.chk_regions if c.value]
        periods = [c.description for c in self.chk_periods if c.value]
        
        if not model or not regions or not periods:
            with self.out_msg:
                clear_output()
                display(HTML("<b style='color:red;'>Atencion: Seleccione 1 Modelo y al menos una Región y un Período.</b>"))
            return
            
        added = 0
        skipped = 0
        
        try:
            from M0_auth_config import CONFIG, _get_fs
            fs = _get_fs()
        except Exception:
            fs = None
            
        for r in regions:
            for period in periods:
                job_id = f"{model} | {r} | {period}"
                
                # Check if already in queue
                if any(job['id'] == job_id for job in self.queue):
                    skipped += 1
                    continue
                    
                # Check if already processed in GCS
                if fs is not None:
                    gcs_dir = f"{CONFIG['bucket']}/{CONFIG['gcs_library_classifications']}/{model}/{period}"
                    # Se achar arquivos para essa região, considera bloqueado
                    try:
                        if len(fs.glob(f"{gcs_dir}/*{r}*.tif")) > 0:
                            skipped += 1
                            continue
                    except:
                        pass
                    
                self.queue.append({
                    'id': job_id,
                    'model': model,
                    'region': r,
                    'period': period,
                    'status': 'PENDING',
                    'enabled': True,
                    'upload_gee': False,
                    'progress': '0%'
                })
                added += 1
                    
        save_queue(self.queue)
        
        for c in self.chk_regions + self.chk_periods:
            c.value = False
        
        with self.out_msg:
            clear_output()
            if added > 0:
                msg = f"<b style='color:green;'>Exito: {added} tareas añadidas a la cola.</b>"
                if skipped > 0:
                    msg += f"<br><span style='color:orange;'>Atencion: {skipped} omitidas (ya en cola o clasificadas en GCS).</span>"
                display(HTML(msg))
            else:
                display(HTML(f"<b style='color:orange;'>Atencion: {skipped} tareas omitidas. Ya estaban en la cola o ya se clasificaron en el Storage.</b>"))
            
        self._refresh_ui()

    def _on_clear_click(self, b):
        self.queue = []
        save_queue(self.queue)
        with self.out_msg:
            clear_output()
            display(HTML("<b style='color:red;'>Cola vaciada.</b>"))
        self._refresh_ui()

    def _delete_job(self, job_id, delete_gcs=False):
        self.queue = load_queue()
        
        # Delete from GCS
        if delete_gcs:
            job = next((j for j in self.queue if j['id'] == job_id), None)
            if job:
                try:
                    fs = _get_fs()
                    # O path gerado em M5_classifier.py
                    gcs_path = f"{CONFIG['bucket']}/{CONFIG['gcs_library_classifications']}/{job['model']}/{job['period']}"
                    # Procurar arquivos que contem os identificadores. Como podem ser varios tiles, vamos buscar e apagar
                    # Para simplificar, listamos e apagamos o que cruza com a region e o period.
                    # Mas como isso pode ser pesado, o ideal é o usuario saber que apaga tudo do diretorio dele
                    # Vamos fazer uma remocao generica na biblioteca para a string basica.
                    files = fs.glob(f"{gcs_path}/*{job['region']}*.tif")
                    for f in files:
                        fs.rm(f)
                    print(f"Borrados {len(files)} archivos GCS.")
                except Exception as e:
                    print(f"Error al borrar GCS: {e}")
                    
        self.queue = [j for j in self.queue if j['id'] != job_id]
        save_queue(self.queue)
        self._refresh_ui()
        
    def _toggle_enabled(self, change, job_id):
        if 'new' in change:
            self.queue = load_queue()
            for j in self.queue:
                if j['id'] == job_id:
                    j['enabled'] = change['new']
            save_queue(self.queue)

    def _toggle_gee(self, change, job_id):
        if 'new' in change:
            self.queue = load_queue()
            for j in self.queue:
                if j['id'] == job_id:
                    j['upload_gee'] = change['new']
            save_queue(self.queue)

    def _update_filters(self, jobs, f_model, f_region, f_year):
        models = sorted(list(set(j['model'] for j in jobs)))
        regions = sorted(list(set(j['region'] for j in jobs)))
        years = sorted(list(set(j['period'].split('_')[0] for j in jobs)), reverse=True)
        
        f_model.options = ['Todos'] + models
        f_region.options = ['Todas'] + regions
        f_year.options = ['Todos'] + years

    def _apply_filters(self, jobs, f_model, f_region, f_year):
        if f_model.value != 'Todos':
            jobs = [j for j in jobs if j['model'] == f_model.value]
        if f_region.value != 'Todas':
            jobs = [j for j in jobs if j['region'] == f_region.value]
        if f_year.value != 'Todos':
            jobs = [j for j in jobs if j['period'].split('_')[0] == f_year.value]
        return jobs

    def _render_pending(self):
        self.queue = load_queue()
        pending_jobs = [j for j in self.queue if j['status'] in ['PENDING', 'RUNNING']]
        
        filter_box = widgets.HBox([self.f_pend_model, self.f_pend_region, self.f_pend_year], layout=widgets.Layout(margin='0 0 15px 0'))
        filtered_jobs = self._apply_filters(pending_jobs, self.f_pend_model, self.f_pend_region, self.f_pend_year)
        
        if not filtered_jobs:
            self.w_pend_rows.children = [widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No hay tareas pendientes (o ninguna coincide con los filtros).</i></div>")]
        else:
            rows = []
            for job in filtered_jobs:
                chk = widgets.Checkbox(value=job.get('enabled', True), description=job['id'], style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', max_width='100%'))
                chk.observe(lambda change, jid=job['id']: self._toggle_enabled(change, jid), names='value')
                
                status_color = "#e67e22" if job['status'] == 'PENDING' else "#3498db" if job['status'] == 'RUNNING' else "#c0392b"
                lbl_status = widgets.HTML(f"<b style='color:{status_color}; width:100px; display:inline-block;'>{job['status']}</b>", layout=widgets.Layout(margin='0 10px 0 0'))
                
                lbl_prog = widgets.HTML(f"<span style='color:#555;'>{job.get('progress', '0%')}</span>", layout=widgets.Layout(width='150px'))
                
                btn_del = widgets.Button(description='Borrar', button_style='danger', layout=widgets.Layout(width='80px'))
                btn_del.on_click(lambda _, jid=job['id']: self._delete_job(jid, delete_gcs=False))
                
                row = widgets.HBox([chk, lbl_status, lbl_prog, btn_del], layout=widgets.Layout(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                rows.append(row)
            self.w_pend_rows.children = rows
            
        self.tab_pending.children = [filter_box, self.w_pend_rows]

    def _render_completed(self):
        self.queue = load_queue()
        completed_jobs = [j for j in self.queue if j['status'] not in ['PENDING', 'RUNNING']]
        
        filter_box = widgets.HBox([self.f_comp_model, self.f_comp_region, self.f_comp_year], layout=widgets.Layout(margin='0 0 15px 0'))
        filtered_jobs = self._apply_filters(completed_jobs, self.f_comp_model, self.f_comp_region, self.f_comp_year)
        
        if not filtered_jobs:
            self.w_comp_rows.children = [widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No hay tareas completadas (o ninguna coincide con los filtros).</i></div>")]
        else:
            grouped = {}
            for j in filtered_jobs:
                grouped.setdefault(j['model'], []).append(j)
                
            cards = []
            for model_name, jobs in grouped.items():
                card_title = widgets.HTML(f"<h4 style='margin:0; color:#2c3e50; padding:10px; background-color:#ecf0f1; border-radius:5px 5px 0 0;'>Modelo (GEE library_models/{model_name})</h4>")
                
                job_rows = []
                for job in jobs:
                    chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f"{job['region']} | {job['period']}", style={'description_width': 'initial'}, layout=widgets.Layout(width='auto', max_width='100%'))
                    chk_gee.observe(lambda change, jid=job['id']: self._toggle_gee(change, jid), names='value')
                    
                    lbl_status = widgets.HTML(f"<span style='color:#27ae60; font-weight:bold; width:100px; display:inline-block;'>{job['status']}</span>")
                    
                    btn_del = widgets.Button(description='Borrar (GCS)', button_style='danger', layout=widgets.Layout(width='120px'))
                    btn_del.on_click(lambda _, jid=job['id']: self._delete_job(jid, delete_gcs=True))
                    
                    row = widgets.HBox([chk_gee, lbl_status, btn_del], layout=widgets.Layout(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                    job_rows.append(row)
                    
                card_body = widgets.VBox(job_rows, layout=widgets.Layout(padding='10px', border='1px solid #ecf0f1', border_top='none', border_radius='0 0 5px 5px'))
                cards.append(widgets.VBox([card_title, card_body], layout=widgets.Layout(margin='0 0 20px 0')))
            self.w_comp_rows.children = cards
            
        self.tab_completed.children = [filter_box, self.w_comp_rows]

    def _refresh_ui(self):
        self.queue = load_queue()
        
        pending_jobs = [j for j in self.queue if j['status'] in ['PENDING', 'RUNNING']]
        completed_jobs = [j for j in self.queue if j['status'] not in ['PENDING', 'RUNNING']]
        
        # Populate dropdown options safely without overwriting current selection if valid
        def _safe_update(f, new_ops):
            old = f.value
            f.options = new_ops
            if old in new_ops: f.value = old
            else: f.value = new_ops[0]
            
        models = ['Todos'] + sorted(list(set(j['model'] for j in pending_jobs)))
        regions = ['Todas'] + sorted(list(set(j['region'] for j in pending_jobs)))
        years = ['Todos'] + sorted(list(set(j['period'].split('_')[0] for j in pending_jobs)), reverse=True)
        _safe_update(self.f_pend_model, models)
        _safe_update(self.f_pend_region, regions)
        _safe_update(self.f_pend_year, years)
        
        c_models = ['Todos'] + sorted(list(set(j['model'] for j in completed_jobs)))
        c_regions = ['Todas'] + sorted(list(set(j['region'] for j in completed_jobs)))
        c_years = ['Todos'] + sorted(list(set(j['period'].split('_')[0] for j in completed_jobs)), reverse=True)
        _safe_update(self.f_comp_model, c_models)
        _safe_update(self.f_comp_region, c_regions)
        _safe_update(self.f_comp_year, c_years)

        self._render_pending()
        self._render_completed()

    def display(self):
        self._refresh_ui()
        form = widgets.VBox([
            self.w_model_box,
            self.w_region_box,
            self.w_period_box,
            widgets.HBox([self.btn_add], layout=widgets.Layout(margin='15px 0 10px 0', align_items='center')),
            self.out_msg
        ], layout=widgets.Layout(padding='20px'))
        
        self.tabs.children = [self.w_guide, form, self.tab_pending, self.tab_completed]
        
        header_actions = widgets.HBox([
            widgets.HTML("<b style='color:#2c3e50; font-size:14px; margin-right:15px;'>Acciones Globales:</b>"),
            self.btn_refresh, 
            widgets.HTML("<div style='width:10px'></div>"),
            self.btn_clear
        ], layout=widgets.Layout(margin='0 0 15px 0', align_items='center', padding='10px', border='1px solid #e0e0e0', background_color='#fcfcfc', border_radius='5px'))
        
        display(widgets.VBox([header_actions, self.tabs]))

def run_m5_ui(years=None, peridiocity_active=None):
    ui = M5QueueUI(years=years, peridiocity_active=peridiocity_active)
    ui.display()
    return ui
