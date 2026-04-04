import re

with open('mapbiomas_fire_monitor/version_01/src/core/M1_export.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_ui_class = '''class ExportDispatcherUI:
    def __init__(self):
        self._build_ui()

    def _get_active_tasks(self):
        # Devuelve nombres bases que están en ejecución o listos
        import ee
        active_names = set()
        try:
            tasks = ee.batch.Task.list()
            active = [t for t in tasks if t.state in ['READY', 'RUNNING']]
            for t in active:
                desc = t.config.get('description', '')
                if desc.startswith('ASSET_') or desc.startswith('GCS_'):
                    base = desc.replace('ASSET_', '').replace('GCS_', '')
                    # GCS añade sufijos _band, cortamos eso
                    if '_blue' in base: base = base.split('_blue')[0]
                    elif '_green' in base: base = base.split('_green')[0]
                    # Cortar sufijo rápido por longitud o buscar 's2_fire_peru_year_M'
                    parts = base.split('_')
                    if len(parts) >= 4 and parts[0] == 's2':
                        # reconstruir s2_fire_peru_2020_01
                        # las ultimas labels podrian ser los meses y el año
                        clean_base = '_'.join(parts[:5]) # s2_fire_peru_2020_01
                        active_names.add(clean_base)
                        clean_base_yearly = '_'.join(parts[:4]) # s2_fire_peru_2020
                        active_names.add(clean_base_yearly)
        except Exception as e:
            print(f'Error leyendo tareas: {e}')
        return active_names

    def _build_ui(self):
        from ipywidgets import HTML, Checkbox, VBox, HBox, Button, Layout, GridBox, Label
        import ipywidgets as widgets
        from IPython.display import display, clear_output
        title = HTML("""
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#e94560;padding:16px;border-radius:10px;">
                🚀 <b>Despachador de Exportaciones</b> — GEE → GCS
            </div>
            <div style="margin-top:10px; font-style:italic;">Escaneando estado actual en GEE/GCS...</div>
        """)
        self.out = widgets.Output()
        self.ui = VBox([title, self.out])
        
        # Load state
        with self.out:
            clear_output()
            print("⏳ Consultando estado en GCS y tareas de GEE...")
            
        self.years = list(range(2019, 2027))
        self.months = list(range(1, 13))
        
        # Determine status
        from M0_auth_config import mosaic_name
        # The check_mosaic_status is actually in M1_export locally
        active_tasks = self._get_active_tasks()
        
        # Dictionary to hold checkboxes
        self.chk_dict = {}
        
        # Create Grid
        grid_items = []
        # Header row
        grid_items.append(Label('Año', layout=Layout(width='60px', font_weight='bold')))
        for m in self.months:
            grid_items.append(Label(str(m).zfill(2), layout=Layout(width='60px', font_weight='bold')))
        grid_items.append(Label('Anual', layout=Layout(width='80px', font_weight='bold')))
        
        for y in self.years:
            grid_items.append(Label(str(y), layout=Layout(width='60px', font_weight='bold')))
            monthly_status = check_mosaic_status(y, self.months, 'monthly')
            yearly_status = check_mosaic_status(y, period='yearly')
            
            for m in self.months:
                name = mosaic_name(y, m, 'monthly')
                s = monthly_status.get(name, {'chunks': 0, 'mosaic': False})
                chk = self._create_checkbox(name, y, m, 'monthly', s, active_tasks)
                self.chk_dict[name] = chk
                grid_items.append(chk)
                
            y_name = mosaic_name(y, period='yearly')
            sy = yearly_status.get(y_name, {'chunks': 0, 'mosaic': False})
            chk_y = self._create_checkbox(y_name, y, None, 'yearly', sy, active_tasks)
            self.chk_dict[y_name] = chk_y
            grid_items.append(chk_y)

        self.grid = GridBox(grid_items, layout=Layout(
            grid_template_columns='80px ' + '60px '*12 + '80px',
            grid_gap='2px', margin='10px 0px'
        ))
        
        # Options
        self.w_export_asset = Checkbox(value=True, description='EE Asset')
        self.w_export_gcs   = Checkbox(value=True, description='GCS Bucket')
        options = HBox([self.w_export_asset, self.w_export_gcs], layout=Layout(margin='10px 0px'))
        
        # Buttons
        self.btn_select_all = Button(description='☑️ Seleccionar Disp.', button_style='info')
        self.btn_clear_all  = Button(description='☐ Limpiar', button_style='')
        self.btn_execute    = Button(description='🚀 Ejecutar Exportación', button_style='danger')
        
        self.btn_select_all.on_click(self._on_select_all)
        self.btn_clear_all.on_click(self._on_clear_all)
        self.btn_execute.on_click(self._on_execute)
        
        btns = HBox([self.btn_select_all, self.btn_clear_all, self.btn_execute])
        
        title.value = title.value.replace("Escaneando estado actual en GEE/GCS...", "✅ Análisis completado. Seleccione mosaicos a exportar.")
        
        with self.out:
            clear_output()
            display(self.grid, options, btns)

        # Do not display self.ui again here, since Jupyter will render it via return

    def _create_checkbox(self, name, y, m, p, status, active_tasks):
        from ipywidgets import Checkbox, Layout
        chk = Checkbox(value=False, indent=False, layout=Layout(width='60px'))
        chk._meta = {'year': y, 'month': m, 'period': p, 'name': name}
        
        # Logica de habilitacion
        is_active = any(name in tn for tn in active_tasks)
        if status['chunks'] > 0:
            chk.description = '✅ OK'
            chk.disabled = True
            chk.style = {'description_width': 'initial', 'background': '#d4edda'}
        elif is_active:
            chk.description = '⏳ EE'
            chk.disabled = True
            chk.style = {'description_width': 'initial', 'background': '#fff3cd'}
        else:
            chk.description = '☐'
        return chk

    def _on_select_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled:
                chk.value = True

    def _on_clear_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled:
                chk.value = False

    def _on_execute(self, _):
        from IPython.display import clear_output
        to_export = []
        for chk in self.chk_dict.values():
            if chk.value and not chk.disabled:
                to_export.append(chk._meta)
        
        if not to_export:
            with self.out:
                print("⚠️ No hay ningún mosaico marcado para exportar.")
            return
            
        with self.out:
            clear_output()
            print(f"🔥 Enviando {len(to_export)} mosaicos...")
            self._dispatch(to_export)
            print("\\n✨ Tareas enviadas. Ejecute de nuevo para ver el estado actualizado.")

    def _dispatch(self, list_to_export):
        import ee
        from M0_auth_config import get_country_geometry, mosaic_name
        geom = get_country_geometry()
        for meta in list_to_export:
            y, m, p = meta['year'], meta['month'], meta['period']
            name = meta['name']
            if p == 'monthly':
                start = ee.Date(f'{y}-{m:02d}-01')
                end = start.advance(1, 'month')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=True, year=y, month=m)
                
                if self.w_export_asset.value:
                    export_to_asset(mosaic, name, y, m, 'monthly')
                if self.w_export_gcs.value:
                    export_to_gcs(mosaic, name, y, m, 'monthly')
            else:
                start = ee.Date(f'{y}-01-01')
                end = ee.Date(f'{y+1}-01-01')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=False)
                
                if self.w_export_asset.value:
                    export_to_asset(mosaic, name, y, period='yearly')
                if self.w_export_gcs.value:
                    export_to_gcs(mosaic, name, y, period='yearly')
            print(f"   🚀 Tarea {name} ENVIADA.")

    def show(self):
        from IPython.display import display
        display(self.ui)
'''

new_text = re.sub(r'class ExportDispatcherUI:.*?(?=def run_ui\(\):)', new_ui_class + '\n\n', text, flags=re.DOTALL)

with open('mapbiomas_fire_monitor/version_01/src/core/M1_export.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("M1 refactor done")
