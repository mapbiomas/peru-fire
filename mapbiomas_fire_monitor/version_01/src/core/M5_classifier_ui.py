import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import json
import os
from M0_auth_config import CONFIG

def get_queue_file():
    # Salva no raiz do version_01 para persistência
    return os.path.join(os.path.dirname(__file__), "..", "..", "m5_queue.json")

def load_queue():
    qf = get_queue_file()
    if os.path.exists(qf):
        with open(qf, 'r') as f:
            return json.load(f)
    return []

def save_queue(q):
    with open(get_queue_file(), 'w') as f:
        json.dump(q, f, indent=2)

class M5QueueUI:
    def __init__(self):
        self.queue = load_queue()
        
        # --- WIDGETS ---
        self.w_model = widgets.Dropdown(description='Modelo:', style={'description_width': '80px'}, layout=widgets.Layout(width='300px'))
        self.w_region = widgets.SelectMultiple(
            options=['Peru', 'Amazonia', 'Cerrado', 'Pantanal'],
            description='Regiones:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='300px', height='120px')
        )
        self.w_year = widgets.SelectMultiple(description='Años:', style={'description_width': '80px'}, layout=widgets.Layout(width='150px', height='120px'))
        self.w_month = widgets.SelectMultiple(description='Meses:', options=[('Anual', 0)] + [(str(m), m) for m in range(1, 13)], style={'description_width': '80px'}, layout=widgets.Layout(width='150px', height='120px'))
        
        self.btn_add = widgets.Button(description='Añadir Lote a la Cola', button_style='primary', icon='plus', layout=widgets.Layout(width='200px'))
        self.btn_add.on_click(self._on_add_click)
        
        self.btn_refresh = widgets.Button(description='Actualizar Vista', icon='refresh', layout=widgets.Layout(width='150px'))
        self.btn_refresh.on_click(lambda _: self._refresh_ui())
        
        self.btn_clear = widgets.Button(description='Limpiar Cola', button_style='danger', icon='trash', layout=widgets.Layout(width='150px'))
        self.btn_clear.on_click(self._on_clear_click)
        
        self.out_pending = widgets.Output()
        self.out_completed = widgets.Output()
        
        self.tabs = widgets.Tab(children=[self.out_pending, self.out_completed])
        self.tabs.set_title(0, 'En Proceso / Pendientes')
        self.tabs.set_title(1, 'Completados / Fallidos')
        
        self.out_msg = widgets.Output()
        
        self._populate_dropdowns()
        
    def _populate_dropdowns(self):
        # Fetch trained models dynamically
        try:
            from M4_model_trainer import list_trained_models
            models = list_trained_models()
            self.w_model.options = models
        except Exception as e:
            self.w_model.options = ['(Error cargando modelos)']
            print(f"Error loading models: {e}")
        
        # Years (2016 to current year)
        self.w_year.options = [str(y) for y in range(2016, 2026)]

    def _on_add_click(self, b):
        model = self.w_model.value
        regions = self.w_region.value
        years = self.w_year.value
        months = self.w_month.value
        
        if not model or not regions or not years or not months:
            with self.out_msg:
                clear_output()
                display(HTML("<b style='color:red;'>⚠️ Seleccione Modelo y al menos una Región, un Año y un Mes.</b>"))
            return
            
        added = 0
        for r in regions:
            for y in years:
                for m in months:
                    period = f"{y}_{m:02d}" if m > 0 else f"{y}"
                    job_id = f"{model} | {r} | {period}"
                    
                    # Check if already in queue
                    if any(job['id'] == job_id for job in self.queue):
                        continue
                        
                    self.queue.append({
                        'id': job_id,
                        'model': model,
                        'region': r,
                        'period': period,
                        'status': 'PENDING',
                        'progress': '0%'
                    })
                    added += 1
                    
        save_queue(self.queue)
        
        # Reset selections (keeping the model)
        self.w_region.value = tuple()
        self.w_year.value = tuple()
        self.w_month.value = tuple()
        
        with self.out_msg:
            clear_output()
            if added > 0:
                display(HTML(f"<b style='color:green;'>✅ {added} tareas añadidas a la cola exitosamente.</b>"))
            else:
                display(HTML(f"<b style='color:orange;'>⚠️ Las combinaciones seleccionadas ya estaban en la cola.</b>"))
            
        self._refresh_ui()

    def _on_clear_click(self, b):
        self.queue = []
        save_queue(self.queue)
        with self.out_msg:
            clear_output()
            display(HTML("<b style='color:red;'>🗑️ Cola vaciada.</b>"))
        self._refresh_ui()

    def _refresh_ui(self):
        self.queue = load_queue()
        
        pending_jobs = [j for j in self.queue if j['status'] in ['PENDING', 'RUNNING']]
        completed_jobs = [j for j in self.queue if j['status'] not in ['PENDING', 'RUNNING']]
        
        def _render_table(jobs, out_widget, empty_msg):
            with out_widget:
                clear_output(wait=True)
                if not jobs:
                    display(HTML(f"<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc; border-radius:8px;'><i>{empty_msg}</i></div>"))
                    return
                    
                html = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; text-align: left;'>"
                html += "<tr style='background-color:#2c3e50; color:white;'><th style='padding:10px; border:1px solid #ddd;'>Tarea (ID)</th><th style='padding:10px; border:1px solid #ddd;'>Status</th><th style='padding:10px; border:1px solid #ddd;'>Progreso</th></tr>"
                
                for job in jobs:
                    color = "#e67e22" if job['status'] == 'PENDING' else "#3498db" if job['status'] == 'RUNNING' else "#c0392b" if 'FAIL' in job['status'] else "#27ae60"
                    html += f"<tr><td style='padding:10px; border:1px solid #ddd; font-weight:bold;'>{job['id']}</td>"
                    html += f"<td style='padding:10px; border:1px solid #ddd; color:{color}; font-weight:bold;'>{job['status']}</td>"
                    html += f"<td style='padding:10px; border:1px solid #ddd;'>{job.get('progress', '0%')}</td></tr>"
                
                html += "</table>"
                display(HTML(html))

        _render_table(pending_jobs, self.out_pending, "No hay tareas pendientes en la cola. Agregue tareas arriba.")
        _render_table(completed_jobs, self.out_completed, "No hay tareas completadas todavía.")

    def display(self):
        self._refresh_ui()
        form = widgets.VBox([
            widgets.HTML("<h3 style='color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:5px; margin-top:0;'>M5 - Registro de Cola de Clasificación</h3>"),
            widgets.HTML("<p style='font-size:13px; color:#666;'>Agende múltiples tareas de clasificación. El procesamiento real se realizará de forma desacoplada y tolerante a fallos.</p>"),
            widgets.HBox([self.w_model, self.w_region], layout=widgets.Layout(margin='0 0 10px 0')),
            widgets.HBox([self.w_year, self.w_month], layout=widgets.Layout(margin='0 0 15px 0')),
            widgets.HBox([self.btn_add, widgets.HTML("<div style='width:20px'></div>"), self.btn_refresh, self.btn_clear], layout=widgets.Layout(margin='0 0 10px 0', align_items='center')),
            self.out_msg
        ], layout=widgets.Layout(padding='20px', border='1px solid #e0e0e0', background_color='#fcfcfc', margin='0 0 20px 0', border_radius='8px'))
        
        display(widgets.VBox([
            form, 
            widgets.HTML("<h4 style='color:#34495e; margin:0 0 10px 0;'>Estado Actual de la Cola</h4>"), 
            self.tabs,
            widgets.HTML("<div style='margin-top:15px; padding:10px; background-color:#e8f4fd; border-left:4px solid #3498db; font-size:13px; color:#2c3e50;'><b>Para iniciar el procesamiento:</b> Ejecute la celda <code>run_m5_queue()</code> ubicada más abajo en el notebook.</div>")
        ]))

def run_m5_ui():
    ui = M5QueueUI()
    ui.display()
    return ui
