import os

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M5_classifier_ui.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

# 1. Update Tab Titles
txt = txt.replace("self.tabs.set_title(0, 'Guía / Detalles')", "self.tabs.set_title(0, 'Guia')")
txt = txt.replace("self.tabs.set_title(1, 'Cadastrar Clasificaciones')", "self.tabs.set_title(1, 'Cadastrar')")
txt = txt.replace("self.tabs.set_title(2, 'Clasificaciones Pendientes')", "self.tabs.set_title(2, 'Pendentes')")
txt = txt.replace("self.tabs.set_title(3, 'Clasificaciones Concluidas')", "self.tabs.set_title(3, 'Concluidas')")

# 2. Fix the Guide tab using widgets.HTML instead of Output
old_guide = '''        # Populate guide
        with self.out_guide:
            clear_output(wait=True)
            guide_html = """
            <div style='padding:20px; font-family:sans-serif;'>
                <h3 style='color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:5px;'>M5 - Clasificación Regional de Larga Escala</h3>
                <p>Este módulo permite clasificar múltiples regiones geográficas (cartas <b>cim-world-1-250000</b>) a lo largo de diferentes meses y años, utilizando los modelos de Inteligencia Artificial entrenados en el módulo M4.</p>
                <h4>Flujo de Trabajo:</h4>
                <ol style='line-height:1.6;'>
                    <li>Vaya a la pestaña <b>Cadastrar Clasificaciones</b>.</li>
                    <li>Seleccione un modelo base entrenado en la biblioteca.</li>
                    <li>Seleccione múltiples <b>Regiones y Períodos</b> en la cuadrícula de opciones.</li>
                    <li>Haga clic en <b>Añadir Lote a la Cola</b> para generar todas las combinaciones cartesianas automáticamente.</li>
                    <li>Acompañe el progreso en las pestañas de <b>Pendientes</b> y <b>Concluidas</b>.</li>
                    <li>Para iniciar el procesamiento en segundo plano, ejecute la celda <code>run_m5_queue()</code> en su Notebook.</li>
                </ol>
            </div>
            """
            display(HTML(guide_html))'''

new_guide = '''        guide_html = """
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
        self.w_guide = widgets.HTML(value=guide_html)'''
txt = txt.replace(old_guide, new_guide)

# 3. Fix the layout of tabs in __init__
old_tabs_init = '''        # --- TABS ---
        self.out_pending = widgets.Output()
        self.out_completed = widgets.Output()
        self.out_guide = widgets.Output()
        
        self.tabs = widgets.Tab(children=[self.out_guide, widgets.VBox(), self.out_pending, self.out_completed])'''
new_tabs_init = '''        # --- TABS ---
        self.w_pend_rows = widgets.VBox()
        self.w_comp_rows = widgets.VBox()
        self.w_guide = widgets.HTML()
        
        self.tab_pending = widgets.VBox()
        self.tab_completed = widgets.VBox()
        
        self.tabs = widgets.Tab(children=[self.w_guide, widgets.VBox(), self.tab_pending, self.tab_completed])'''
txt = txt.replace(old_tabs_init, new_tabs_init)

# 4. Bind filters and rows to tab_pending / tab_completed in display()
old_display = '''        self.tabs.children = [self.out_guide, form, self.out_pending, self.out_completed]'''
new_display = '''        self.tabs.children = [self.w_guide, form, self.tab_pending, self.tab_completed]'''
txt = txt.replace(old_display, new_display)

# 5. Fix _render_pending and _render_completed
old_render_p = '''    def _render_pending(self):
        with self.out_pending:
            clear_output(wait=True)
            self.queue = load_queue()
            pending_jobs = [j for j in self.queue if j['status'] in ['PENDING', 'RUNNING']]
            
            # Filters block
            filter_box = widgets.HBox([self.f_pend_model, self.f_pend_region, self.f_pend_year], layout=widgets.Layout(margin='0 0 15px 0'))
            display(filter_box)
            
            filtered_jobs = self._apply_filters(pending_jobs, self.f_pend_model, self.f_pend_region, self.f_pend_year)
            
            if not filtered_jobs:
                display(HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No hay tareas pendientes (o ninguna coincide con los filtros).</i></div>"))
                return
                
            rows = []
            for job in filtered_jobs:
                chk = widgets.Checkbox(value=job.get('enabled', True), description=job['id'], layout=widgets.Layout(width='350px'))
                chk.observe(lambda change, jid=job['id']: self._toggle_enabled(change, jid), names='value')
                
                status_color = "#e67e22" if job['status'] == 'PENDING' else "#3498db" if job['status'] == 'RUNNING' else "#c0392b"
                lbl_status = widgets.HTML(f"<b style='color:{status_color}; width:100px; display:inline-block;'>{job['status']}</b>", layout=widgets.Layout(margin='0 10px 0 0'))
                
                lbl_prog = widgets.HTML(f"<span style='color:#555;'>{job.get('progress', '0%')}</span>", layout=widgets.Layout(width='150px'))
                
                btn_del = widgets.Button(description='Borrar', button_style='danger', layout=widgets.Layout(width='80px'))
                btn_del.on_click(lambda _, jid=job['id']: self._delete_job(jid, delete_gcs=False))
                
                row = widgets.HBox([chk, lbl_status, lbl_prog, btn_del], layout=widgets.Layout(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                rows.append(row)
                
            display(widgets.VBox(rows))'''

new_render_p = '''    def _render_pending(self):
        self.queue = load_queue()
        pending_jobs = [j for j in self.queue if j['status'] in ['PENDING', 'RUNNING']]
        
        filter_box = widgets.HBox([self.f_pend_model, self.f_pend_region, self.f_pend_year], layout=widgets.Layout(margin='0 0 15px 0'))
        filtered_jobs = self._apply_filters(pending_jobs, self.f_pend_model, self.f_pend_region, self.f_pend_year)
        
        if not filtered_jobs:
            self.w_pend_rows.children = [widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No hay tareas pendientes (o ninguna coincide con los filtros).</i></div>")]
        else:
            rows = []
            for job in filtered_jobs:
                chk = widgets.Checkbox(value=job.get('enabled', True), description=job['id'], layout=widgets.Layout(width='350px'))
                chk.observe(lambda change, jid=job['id']: self._toggle_enabled(change, jid), names='value')
                
                status_color = "#e67e22" if job['status'] == 'PENDING' else "#3498db" if job['status'] == 'RUNNING' else "#c0392b"
                lbl_status = widgets.HTML(f"<b style='color:{status_color}; width:100px; display:inline-block;'>{job['status']}</b>", layout=widgets.Layout(margin='0 10px 0 0'))
                
                lbl_prog = widgets.HTML(f"<span style='color:#555;'>{job.get('progress', '0%')}</span>", layout=widgets.Layout(width='150px'))
                
                btn_del = widgets.Button(description='Borrar', button_style='danger', layout=widgets.Layout(width='80px'))
                btn_del.on_click(lambda _, jid=job['id']: self._delete_job(jid, delete_gcs=False))
                
                row = widgets.HBox([chk, lbl_status, lbl_prog, btn_del], layout=widgets.Layout(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                rows.append(row)
            self.w_pend_rows.children = rows
            
        self.tab_pending.children = [filter_box, self.w_pend_rows]'''
txt = txt.replace(old_render_p, new_render_p)

old_render_c = '''    def _render_completed(self):
        with self.out_completed:
            clear_output(wait=True)
            self.queue = load_queue()
            completed_jobs = [j for j in self.queue if j['status'] not in ['PENDING', 'RUNNING']]
            
            # Filters block
            filter_box = widgets.HBox([self.f_comp_model, self.f_comp_region, self.f_comp_year], layout=widgets.Layout(margin='0 0 15px 0'))
            display(filter_box)
            
            filtered_jobs = self._apply_filters(completed_jobs, self.f_comp_model, self.f_comp_region, self.f_comp_year)
            
            if not filtered_jobs:
                display(HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No hay tareas completadas (o ninguna coincide con los filtros).</i></div>"))
                return
                
            # Agrupar por modelo
            grouped = {}
            for j in filtered_jobs:
                grouped.setdefault(j['model'], []).append(j)
                
            cards = []
            for model_name, jobs in grouped.items():
                card_title = widgets.HTML(f"<h4 style='margin:0; color:#2c3e50; padding:10px; background-color:#ecf0f1; border-radius:5px 5px 0 0;'>Modelo (GEE library_models/{model_name})</h4>")
                
                job_rows = []
                for job in jobs:
                    chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f"{job['region']} | {job['period']}", layout=widgets.Layout(width='300px'))
                    chk_gee.observe(lambda change, jid=job['id']: self._toggle_gee(change, jid), names='value')
                    
                    lbl_status = widgets.HTML(f"<span style='color:#27ae60; font-weight:bold; width:100px; display:inline-block;'>{job['status']}</span>")
                    
                    btn_del = widgets.Button(description='Borrar (GCS)', button_style='danger', layout=widgets.Layout(width='120px'))
                    btn_del.on_click(lambda _, jid=job['id']: self._delete_job(jid, delete_gcs=True))
                    
                    row = widgets.HBox([chk_gee, lbl_status, btn_del], layout=widgets.Layout(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                    job_rows.append(row)
                    
                card_body = widgets.VBox(job_rows, layout=widgets.Layout(padding='10px', border='1px solid #ecf0f1', border_top='none', border_radius='0 0 5px 5px'))
                cards.append(widgets.VBox([card_title, card_body], layout=widgets.Layout(margin='0 0 20px 0')))
                
            display(widgets.VBox(cards))'''

new_render_c = '''    def _render_completed(self):
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
                    chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f"{job['region']} | {job['period']}", layout=widgets.Layout(width='300px'))
                    chk_gee.observe(lambda change, jid=job['id']: self._toggle_gee(change, jid), names='value')
                    
                    lbl_status = widgets.HTML(f"<span style='color:#27ae60; font-weight:bold; width:100px; display:inline-block;'>{job['status']}</span>")
                    
                    btn_del = widgets.Button(description='Borrar (GCS)', button_style='danger', layout=widgets.Layout(width='120px'))
                    btn_del.on_click(lambda _, jid=job['id']: self._delete_job(jid, delete_gcs=True))
                    
                    row = widgets.HBox([chk_gee, lbl_status, btn_del], layout=widgets.Layout(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                    job_rows.append(row)
                    
                card_body = widgets.VBox(job_rows, layout=widgets.Layout(padding='10px', border='1px solid #ecf0f1', border_top='none', border_radius='0 0 5px 5px'))
                cards.append(widgets.VBox([card_title, card_body], layout=widgets.Layout(margin='0 0 20px 0')))
            self.w_comp_rows.children = cards
            
        self.tab_completed.children = [filter_box, self.w_comp_rows]'''
txt = txt.replace(old_render_c, new_render_c)

with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Sucesso!")
