import re

with open('mapbiomas_fire_monitor/version_01/src/core/M2_mosaic.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_ui_class = '''class MosaicAssemblerUI:
    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML, Checkbox, VBox, HBox, Button, Layout, Label
        import ipywidgets as widgets
        from IPython.display import display, clear_output
        from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, monthly_mosaic_path, yearly_chunk_path, yearly_mosaic_path

        title = HTML("""
            <div style="background:linear-gradient(135deg,#003300,#004d00);color:#b3ffb3;padding:14px;border-radius:10px;">
                🗺️ <b>Ensamblador Analítico</b> — GCS Shards → COG
            </div>
            <div style="margin-top:10px; font-style:italic;">Analizando fragmentos (shards) disponibles en GCS de manera modular...</div>
        """)
        
        self.out = widgets.Output()
        self.ui = VBox([title, self.out])
        
        with self.out:
            clear_output()
            print("⏳ Conectando e indexando disponibilidad granular por banda...")
            
        self.years = list(range(2019, 2027))
        self.months = list(range(1, 13))
        
        # === Carga en Masa ===
        from M2_mosaic import fetch_all_gcs_files, list_gcs_files
        fetch_all_gcs_files(force=False, progress_out=self.out)
        
        self.chk_dict = {}
        items_visuals = []
        
        all_bands = CONFIG['bands_all']
        
        for y in self.years:
            # Monthly
            for m in self.months:
                c_pref = monthly_chunk_path(y, m)
                m_pref = monthly_mosaic_path(y, m)
                
                chunks = list_gcs_files(c_pref)
                if not chunks:
                    continue
                    
                mosaics = list_gcs_files(m_pref)
                
                # Identify which bands have chunks
                for b in all_bands:
                    has_chunk = any(f"_{b}_" in c or c.endswith(f"_{b}.tif") for c in chunks)
                    has_cog = any(f"_{b}_cog" in m_c or m_c.endswith(f"_{b}_cog.tif") for m_c in mosaics)
                    
                    if has_chunk:
                        name = f"{y}_{m:02d}_{b}"
                        meta = {'year': y, 'month': m, 'period': 'monthly', 'band': b}
                        
                        desc = f"{y}-{m:02d} [{b}]"
                        if has_cog:
                            chk = Checkbox(description=f"✅ {desc}", value=False, disabled=True, indent=False, layout=Layout(width='160px', overflow='hidden', background='#d4edda'))
                        else:
                            chk = Checkbox(description=f"🧩 {desc}", value=False, disabled=False, indent=False, layout=Layout(width='160px', overflow='hidden', background='#cce5ff'))
                        
                        chk._meta = meta
                        self.chk_dict[name] = chk
                        items_visuals.append(chk)
            
            # Yearly
            cy_pref = yearly_chunk_path(y)
            my_pref = yearly_mosaic_path(y)
            chunks_y = list_gcs_files(cy_pref)
            if chunks_y:
                mosaics_y = list_gcs_files(my_pref)
                for b in all_bands:
                    has_chunk = any(f"_{b}_" in c or c.endswith(f"_{b}.tif") for c in chunks_y)
                    has_cog = any(f"_{b}_cog" in m_c or m_c.endswith(f"_{b}_cog.tif") for m_c in mosaics_y)
                    
                    if has_chunk:
                        name = f"{y}_ yearly_{b}"
                        meta = {'year': y, 'month': None, 'period': 'yearly', 'band': b}
                        desc = f"{y}-Anual [{b}]"
                        if has_cog:
                            chk = Checkbox(description=f"✅ {desc}", value=False, disabled=True, indent=False, layout=Layout(width='160px', overflow='hidden', background='#d4edda'))
                        else:
                            chk = Checkbox(description=f"🧩 {desc}", value=False, disabled=False, indent=False, layout=Layout(width='160px', overflow='hidden', background='#cce5ff'))
                            
                        chk._meta = meta
                        self.chk_dict[name] = chk
                        items_visuals.append(chk)

        if not items_visuals:
            items_visuals = [Label("⚠️ Nungún fragmento disponible ha sido detectado en el Bucket.")]
            
        self.flex_box = HBox(items_visuals, layout=Layout(flex_flow='row wrap', width='100%', grid_gap='5px', padding='15px'))
        
        self.btn_select_all = Button(description='☑️ Marcar Disponibles', button_style='info', layout=Layout(width='auto', min_width='160px'))
        self.btn_clear_all  = Button(description='☐ Limpiar TODAS', button_style='', layout=Layout(width='auto', min_width='130px'))
        self.btn_execute    = Button(description='🧩 Ensamblar Marcadas', button_style='warning', layout=Layout(width='auto', min_width='200px'))
        
        self.btn_select_all.on_click(self._on_select_all)
        self.btn_clear_all.on_click(self._on_clear_all)
        self.btn_execute.on_click(self._on_execute)
        
        btns = HBox([self.btn_select_all, self.btn_clear_all, self.btn_execute])
        
        title.value = title.value.replace("Analizando fragmentos (shards) disponibles en GCS de manera modular...", "✅ Análisis de GCS completado. Seleccione las bandas de mosaico a ensamblar.")
        
        with self.out:
            clear_output()
            # Mostramos el contenedor de datos-diregidos (Data-Driven Box)
            display(self.flex_box, btns)

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
        to_assemble = []
        for chk in self.chk_dict.values():
            if chk.value and not chk.disabled:
                to_assemble.append(chk._meta)
        
        if not to_assemble:
            with self.out:
                print("⚠️ No hay ningún mosaico/banda marcado para ensamblar.")
            return
            
        with self.out:
            clear_output()
            print("⏳ Limpiando caché y forzando actualización de índice antes de ensamblar...")
            from M2_mosaic import fetch_all_gcs_files, assemble_country_mosaic
            fetch_all_gcs_files(force=True)
            print(f"🛠️ Ensamblando {len(to_assemble)} mosaicos individuales (por banda)...")
            
            for meta in to_assemble:
                y, m, p, b = meta['year'], meta['month'], meta['period'], meta['band']
                assemble_country_mosaic(y, m, p, bands=[b])
                self._show_download_links(y, m, p, bands=[b])
            
            # Recargar el caché al final para tener la vista general actualizada
            fetch_all_gcs_files(force=True)
            print("\\n✨ Ensamblaje completado. Ejecute de nuevo para ver el panel de control actualizado.")

    def _show_download_links(self, year, month, period='monthly', bands=None):
        from M0_auth_config import mosaic_name, monthly_chunk_path, monthly_mosaic_path, yearly_chunk_path, yearly_mosaic_path, CONFIG
        from IPython.display import display
        import ipywidgets as widgets
        
        if period == 'monthly':
            prefix = monthly_chunk_path(year, month)
            mosaic_pref = monthly_mosaic_path(year, month)
            label = f"{year}-{month:02d}"
            base = mosaic_name(year, month, 'monthly')
        else:
            prefix = yearly_chunk_path(year)
            mosaic_pref = yearly_mosaic_path(year)
            label = f"{year} (Anual)"
            base = mosaic_name(year, period='yearly')

        target_bands = bands or CONFIG['bands_all']
        links_html = f"<b>📥 Mosaico Ensamblado ({label}):</b><br>"
        for band in target_bands:
            url = f"https://storage.googleapis.com/{CONFIG['bucket']}/{mosaic_pref}/{base}_{band}_cog.tif"
            links_html += f"• <a href='{url}' target='_blank' style='color:#4caf50;'>{band}</a> &nbsp;"
        
        display(widgets.HTML(f"<div style='background:#111;padding:12px;border-left:4px solid #4caf50;margin-top:5px;font-family:monospace;'>{links_html}</div>"))

    def show(self):
        from IPython.display import display
        display(self.ui)
'''

new_text = re.sub(r'class MosaicAssemblerUI:.*?(?=def run_ui\(\):)', new_ui_class + '\n\n', text, flags=re.DOTALL)

with open('mapbiomas_fire_monitor/version_01/src/core/M2_mosaic.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("M2 refactor done")
