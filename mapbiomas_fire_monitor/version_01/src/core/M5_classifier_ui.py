import os
import base64
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from M0_auth_config import CONFIG, _get_fs
from M5_queue import load_queue, save_queue, make_job_id, new_job, gcs_full, classified_tiles_dir, \
    tarea_path, save_tarea, delete_tarea, list_tareas

L = widgets.Layout

class M5QueueUI:
    def __init__(self, years=None, peridiocity_active=None):
        self.years = years or [2025, 2026]
        self.peridiocity_active = peridiocity_active or ['monthly']
        self.queue = load_queue()

        self._thumb_cache = {}
        self._grid_count_cache = {}

        self.w_model_box = widgets.VBox()
        self.w_region_box = widgets.VBox()
        self.w_period_box = widgets.VBox()

        self.chk_models = []
        self.chk_regions = []
        self.chk_periods = []

        self.btn_add = widgets.Button(description='Agregar Lote a la Cola', button_style='primary', icon='plus', layout=L(width='200px'))
        self.btn_add.on_click(self._on_add_click)

        self.btn_refresh = widgets.Button(description='Actualizar Vista', icon='refresh', layout=L(width='150px'))
        self.btn_refresh.on_click(lambda _: self._refresh_ui())

        self.w_guide = widgets.HTML()

        self.w_pend_rows = widgets.VBox()
        self.tab_pending = widgets.VBox()
        self.f_pend_model = widgets.Dropdown(description='Modelo:', options=['Todos'], layout=L(width='250px'))
        self.f_pend_region = widgets.Dropdown(description='Region:', options=['Todas'], layout=L(width='250px'))
        self.f_pend_year = widgets.Dropdown(description='Anio:', options=['Todos'], layout=L(width='200px'))
        for f in [self.f_pend_model, self.f_pend_region, self.f_pend_year]:
            f.observe(lambda _: self._render_pending(), names='value')

        self.w_pub_rows = widgets.VBox()
        self.tab_publish = widgets.VBox()
        self.f_pub_model = widgets.Dropdown(description='Modelo:', options=['Todos'], layout=L(width='250px'))
        self.f_pub_region = widgets.Dropdown(description='Region:', options=['Todas'], layout=L(width='250px'))
        self.f_pub_year = widgets.Dropdown(description='Anio:', options=['Todos'], layout=L(width='200px'))
        for f in [self.f_pub_model, self.f_pub_region, self.f_pub_year]:
            f.observe(lambda _: self._render_publish(), names='value')

        self.w_mapa_rows = widgets.VBox()
        self.tab_mapa = widgets.VBox()
        self.f_mapa_model = widgets.Dropdown(description='Modelo:', options=['Todos'], layout=L(width='250px'))
        self.f_mapa_region = widgets.Dropdown(description='Region:', options=['Todas'], layout=L(width='250px'))
        self.f_mapa_year = widgets.Dropdown(description='Anio:', options=['Todos'], layout=L(width='200px'))
        self.btn_mapa_refresh = widgets.Button(description='Actualizar Mapa', icon='refresh', layout=L(width='150px'))
        self.btn_mapa_refresh.on_click(lambda _: self._render_mapa())
        for f in [self.f_mapa_model, self.f_mapa_region, self.f_mapa_year]:
            f.observe(lambda _: self._render_mapa(), names='value')

        self.w_done_rows = widgets.VBox()
        self.tab_done = widgets.VBox()
        self.f_done_model = widgets.Dropdown(description='Modelo:', options=['Todos'], layout=L(width='250px'))
        self.f_done_region = widgets.Dropdown(description='Region:', options=['Todas'], layout=L(width='250px'))
        self.f_done_year = widgets.Dropdown(description='Anio:', options=['Todos'], layout=L(width='200px'))
        for f in [self.f_done_model, self.f_done_region, self.f_done_year]:
            f.observe(lambda _: self._render_done(), names='value')

        self.out_msg = widgets.Output()

        self.tabs = widgets.Tab()
        self._build_guide()
        self._populate_dropdowns()

    # --- PERIODOS ---

    def _get_all_periods(self):
        """Retorna dict {year: [month_str, ...]} com todos periodos disponiveis."""
        import datetime
        now = datetime.datetime.now()
        periods_by_year = {}
        for y in self.years:
            months = []
            if "yearly" in self.peridiocity_active and y < now.year:
                months.append('')
            if "monthly" in self.peridiocity_active:
                max_m = (now.month - 1) if y == now.year else (12 if y < now.year else 0)
                for m in range(1, max_m + 1):
                    months.append(f"{m:02d}")
            if months:
                periods_by_year[y] = months
        return periods_by_year

    # --- THUMBNAIL (GEE) ---

    def _generate_thumb(self, model, size=128):
        """Gera thumbnail GEE das cells de um modelo. Cache em memoria."""
        cache_key = f"{model}_{size}"
        if cache_key in self._thumb_cache:
            return self._thumb_cache[cache_key]
        try:
            import ee
            import requests
            if not getattr(ee.data, '_credentials', None):
                from M0_auth_config import authenticate
                authenticate()
            peru = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
            grid = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")

            regions_names = sorted(set(j['region'] for j in self.queue if j['model'] == model))
            all_regions = ee.FeatureCollection(CONFIG['asset_regions'])

            bg = peru.style(**{'fillColor': 'f0f0f0', 'color': 'cccccc', 'width': 1})
            region_lines = all_regions.style(**{'color': '2980b9', 'width': 1, 'fillColor': '00000000'})
            grid_lines = grid.style(**{'color': 'e0e0e0', 'width': 0.3, 'fillColor': '00000000'})

            layers = [bg, region_lines, grid_lines]
            overlay = ee.ImageCollection(layers).mosaic()
            bounds = peru.geometry().bounds(1, 'EPSG:4326')
            url = overlay.getThumbURL({'region': bounds, 'dimensions': size, 'format': 'png'})
            resp = requests.get(url, timeout=60)
            b64 = base64.b64encode(resp.content).decode('ascii')
            self._thumb_cache[cache_key] = b64
            return b64
        except Exception:
            return None

    # --- TIMELINE (HTML) ---

    def _build_year_line(self, year, months, jobs_for_model_region):
        """Retorna HTML de uma linha de timeline: label ano + 12 bolinhas mes."""
        dots = []
        for m in months:
            period = f"{year}_{m}" if m else str(year)
            status = 'none'
            for j in jobs_for_model_region:
                if j['period'] == period:
                    if j['status'] in ('COMPLETED', 'FINISHED'):
                        status = 'done'
                    elif j['status'] in ('PENDING', 'RUNNING'):
                        status = 'running'
                    break
            colors = {'none': '#ddd', 'running': '#e67e22', 'done': '#27ae60'}
            title = period if m else str(year)
            dots.append(f'<span title="{title}" style="display:inline-block;width:14px;height:14px;'
                        f'border-radius:50%;background:{colors[status]};margin:0 2px;'
                        f'border:1px solid #999;"></span>')
        label = str(year) if months and months != [''] else ''
        return f'<div style="display:flex;align-items:center;margin:2px 0;">' \
               f'<span style="width:50px;font-size:11px;color:#555;">{label}</span>' \
               f'<div style="display:flex;flex-wrap:wrap;">{"".join(dots)}</div></div>'

    # --- GUIA ---

    def _build_guide(self):
        html = """
        <div style='padding:20px; font-family:sans-serif;'>
            <h3 style='color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:5px;'>M5 - Clasificacion Regional de Gran Escala</h3>
            <p>Clasifica multiples regiones (cartas <b>cim-world-1-250000</b>) usando modelos del M4.</p>
            <h4>Flujo:</h4>
            <ol style='line-height:1.6;'>
                <li><b>Registrar</b> — seleccione modelo + regiones + periodos.</li>
                <li><b>Pendientes</b> — siga la clasificacion tile a tile.</li>
                <li><b>Para Publicar</b> — trabajos COMPLETED con gestion de tiles.</li>
                <li><b>Mapa</b> — visibilidad general del progreso.</li>
                <li><b>Finalizadas</b> — trabajos FINISHED con timeline de cobertura.</li>
                <li>Ejecute <code>run_m5_queue()</code> en el notebook para procesar.</li>
            </ol>
            <h4>Eliminacion granular:</h4>
            <ul>
                <li><b>Pendientes</b> — elimine trabajos individuales de la cola.</li>
                <li><b>Para Publicar</b> — elimine tiles individuales o todos de un trabajo.</li>
                <li><b>Finalizadas</b> — elimine por region o modelo completo.</li>
                <li>Despues de eliminar, registre nuevamente el trabajo en <b>Registrar</b>.</li>
            </ul>
        </div>
        """
        self.w_guide = widgets.HTML(value=html)

    # --- CHECKBOX GRID ---

    def _create_checkbox_grid(self, options, description, single_select=False, bg_color='#fafafa', columns=None):
        title = widgets.HTML(f"<div style='margin-bottom:5px; color:#2c3e50;'><b>{description}</b></div>")
        checkboxes = []
        for opt in options:
            chk = widgets.Checkbox(value=False, description=str(opt), indent=False, style={'description_width': 'initial'}, layout=L(width='auto', margin='0 5px 5px 0'))
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
        grid = widgets.GridBox(checkboxes, layout=L(grid_template_columns=gtc, width='100%'))
        container = widgets.VBox([title, grid], layout=L(margin='0 0 15px 0', padding='10px', border='1px solid #ccc', border_radius='5px', background_color=bg_color))
        return container, checkboxes

    def _populate_dropdowns(self):
        try:
            from M4_model_trainer import list_trained_models
            models = list_trained_models()
        except Exception:
            models = []
        box, self.chk_models = self._create_checkbox_grid(models, "1. Seleccione Modelo (unico):", single_select=True, bg_color='#e8f4fd')
        self.w_model_box.children = box.children
        regions = ['Peru', 'Amazonia', 'Cerrado']
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
        except Exception:
            pass
        box, self.chk_regions = self._create_checkbox_grid(regions, "2. Seleccione Regiones:", bg_color='#fdf7e8')
        self.w_region_box.children = box.children
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
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Periodos (Anio / Anio_Mes):", bg_color='#ebf5eb', columns=4)
        self.w_period_box.children = box.children

    # --- REGISTRAR ---

    def _on_add_click(self, b):
        self.queue = load_queue()
        model = next((c.description for c in self.chk_models if c.value), None)
        regions = [c.description for c in self.chk_regions if c.value]
        periods = [c.description for c in self.chk_periods if c.value]
        if not model or not regions or not periods:
            with self.out_msg:
                clear_output()
                display(HTML("<b style='color:red;'>Atencion: Seleccione 1 Modelo y al menos una Region y un Periodo.</b>"))
            return
        added = 0
        skipped = 0
        for r in regions:
            for period in periods:
                job_id = make_job_id(model, r, period)
                if any(job['id'] == job_id for job in self.queue):
                    skipped += 1
                    continue
                self.queue.append(new_job(model, r, period))
                added += 1
        save_queue(self.queue)
        for c in self.chk_regions + self.chk_periods:
            c.value = False
        with self.out_msg:
            clear_output()
            if added > 0:
                msg = f"<b style='color:green;'>Exito: {added} tareas agregadas a la cola.</b>"
                if skipped > 0:
                    msg += f"<br><span style='color:orange;'>Atencion: {skipped} omitidas (ya en la cola).</span>"
                display(HTML(msg))
            else:
                display(HTML(f"<b style='color:orange;'>Atencion: {skipped} tareas ya estaban en la cola.</b>"))
        self._refresh_ui()

    # --- DELECAO ---

    def _delete_tiles(self, tile_fqpaths, fs):
        for fp in tile_fqpaths:
            try:
                if fs.exists(fp):
                    fs.rm(fp)
            except Exception:
                pass
        return len(tile_fqpaths)

    def _delete_job_tiles_region(self, job):
        from M5_queue import region_path
        fs = _get_fs()
        r, p, m = job['region'], job['period'], job['model']
        reg_full = gcs_full(region_path(m, r, p))
        try:
            if fs.exists(reg_full):
                fs.rm(reg_full)
        except Exception:
            pass
        t_dir = gcs_full(classified_tiles_dir(m))
        tile_list = []
        try:
            tile_list = [t for t in fs.glob(f"{t_dir}/tile_{r}_{p}.tif") if not t.endswith('.aux.xml')]
        except Exception:
            pass
        try:
            tile_list += [t for t in fs.glob(f"{t_dir}/tile_{r}_*.tif") if not t.endswith('.aux.xml')]
        except Exception:
            pass
        tile_list = list(set(tile_list))
        n = self._delete_tiles(tile_list, fs)
        return n

    def _delete_job_complete(self, job):
        from M5_queue import region_path, stats_dir
        fs = _get_fs()
        r, p, m = job['region'], job['period'], job['model']
        n_tiles = self._delete_job_tiles_region(job)
        s_dir = gcs_full(stats_dir(m))
        for csv_name in ['stats_tile.csv', 'stats_region.csv']:
            csv_path = f"{s_dir}/{csv_name}"
            try:
                if fs.exists(csv_path):
                    fs.rm(csv_path)
            except Exception:
                pass
        return n_tiles

    def _delete_model_region(self, model, region):
        """Elimina todos jobs + tiles + mosaico + stats de (model, region)."""
        fs = _get_fs()
        self.queue = load_queue()
        jobs = [j for j in self.queue if j['model'] == model and j['region'] == region]
        total_tiles = 0
        for job in jobs:
            if job['status'] in ('COMPLETED', 'FINISHED'):
                total_tiles += self._delete_job_tiles_region(job)
        from M5_queue import stats_dir
        for job in jobs:
            s_dir = gcs_full(stats_dir(model))
            for csv_name in ['stats_tile.csv', 'stats_region.csv']:
                try:
                    p = f"{s_dir}/{csv_name}"
                    if fs.exists(p):
                        fs.rm(p)
                except Exception:
                    pass
            break
        self.queue = [j for j in self.queue if not (j['model'] == model and j['region'] == region)]
        save_queue(self.queue)
        return total_tiles, len(jobs)

    def _delete_model_all(self, model):
        """Elimina todo de um modelo (todas regioes)."""
        self.queue = load_queue()
        regions = set(j['region'] for j in self.queue if j['model'] == model)
        total = 0
        total_jobs = 0
        for region in regions:
            n_tiles, n_jobs = self._delete_model_region(model, region)
            total += n_tiles
            total_jobs += n_jobs
        return total, total_jobs

    def _remove_from_queue(self, job_id):
        self.queue = load_queue()
        self.queue = [j for j in self.queue if j['id'] != job_id]
        save_queue(self.queue)
        self._refresh_ui()

    # --- TAREAS ---

    def _tarea_section(self):
        """Retorna widget com a secao de tareas GCS para Pendientes."""
        fs = _get_fs()
        tareas = list_tareas(fs=fs)
        if not tareas:
            return widgets.HTML("")

        cards = []
        header = widgets.HTML(f"<div style='margin:10px 0 5px; padding:8px; background:#fef9e7; border:1px solid #f9e79f; border-radius:4px;'><b>Tareas en GCS ({len(tareas)} disponibles)</b></div>")
        cards.append(header)

        for t in tareas:
            model = t.get('model', '?')
            regions = t.get('regions', [])
            periods = t.get('periods', [])
            years = sorted(set(p.split('_')[0] for p in periods))
            label = f" Modelo: {model} | Regiones: {', '.join(regions)} | Periodos: {', '.join(years)}"

            btn_cargar = widgets.Button(description='Cargar a la Cola', button_style='success', layout=L(width='150px', height='28px'))
            def _make_cargar(m, regs, pers):
                def _h(_):
                    self.queue = load_queue()
                    added = 0
                    skipped = 0
                    for r in regs:
                        for p in pers:
                            jid = make_job_id(m, r, p)
                            if any(job['id'] == jid for job in self.queue):
                                skipped += 1
                                continue
                            self.queue.append(new_job(m, r, p))
                            added += 1
                    save_queue(self.queue)
                    with self.out_msg:
                        clear_output()
                        display(HTML(f"<span style='color:green;'>{added} cargadas, {skipped} omitidas.</span>"))
                    self._refresh_ui()
                return _h
            btn_cargar.on_click(_make_cargar(model, regions, periods))

            row = widgets.HBox([
                widgets.HTML(label, layout=L(width='auto')),
                btn_cargar
            ], layout=L(align_items='center', margin='2px 0', padding='5px', border='1px solid #eee'))
            cards.append(row)

        return widgets.VBox(cards, layout=L(margin='0 0 15px 0'))

    # --- GRID COUNTS ---

    def _get_grid_count(self, region_name):
        """Retorna numero de celulas cim-world em uma regiao. Cache em memoria."""
        if region_name in self._grid_count_cache:
            return self._grid_count_cache[region_name]
        try:
            import ee
            if not getattr(ee.data, '_credentials', None):
                from M0_auth_config import authenticate
                authenticate()
            cim = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")
            if region_name.lower() == 'peru':
                fc = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
            else:
                fc = ee.FeatureCollection(CONFIG['asset_regions']).filter(ee.Filter.eq('region_nam', region_name))
            n = cim.filterBounds(fc.geometry()).size().getInfo()
            self._grid_count_cache[region_name] = n
            return n
        except Exception:
            return None

    # --- SCALE BAR ---

    def _nice_scale(self, width_km):
        """Escolhe um valor 'bonito' para a barra de escala (1, 2, 5, 10, 20, 50...)."""
        if width_km <= 0:
            return 1
        mag = 10 ** int(width_km ** 0.5 - 1) if width_km < 1 else 10 ** int(width_km // 10)
        mag = max(1, 10 ** (len(str(int(width_km))) - 1))
        candidates = [mag, mag * 2, mag * 5, mag * 10]
        for c in candidates:
            if c >= width_km * 0.25 and c <= width_km * 0.5:
                return c
        return candidates[0]

    def _build_scale_bar(self, img_width_px, bounds_info):
        """Retorna HTML de barra de escala baseada nos bounds."""
        w, s, e, n = bounds_info
        center_lat = (s + n) / 2
        width_km = (e - w) * 111.32
        scale_km = self._nice_scale(width_km)
        scale_px = int(img_width_px * (scale_km / width_km))
        bar = ('<div style="margin:8px 0;font-size:11px;color:#555;">'
               f'<div style="display:flex;align-items:center;gap:4px;">'
               f'<span style="border-top:2px solid #333;width:{scale_px}px;height:0;"></span>'
               f'<span>{scale_km} km</span>'
               f'<span style="margin-left:auto;">~{width_km:.0f} km de ancho</span>'
               '</div></div>')
        return bar

    # --- RENDER PENDIENTES ---

    def _render_pending(self):
        self.queue = load_queue()
        jobs = [j for j in self.queue if j['status'] in ('PENDING', 'RUNNING')]

        filter_box = widgets.HBox([self.f_pend_model, self.f_pend_region, self.f_pend_year], layout=L(margin='0 0 10px 0'))
        filtered = self._apply_filters(jobs, self.f_pend_model, self.f_pend_region, self.f_pend_year)

        btn_clear = widgets.Button(description='Limpiar Cola', button_style='danger', icon='trash', layout=L(width='150px'))
        btn_clear.on_click(lambda _: self._on_clear_click())

        tarea_section = self._tarea_section()

        if not filtered:
            pend_vbox = widgets.VBox([tarea_section, filter_box, btn_clear,
                widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No hay tareas pendientes.</i></div>")])
        else:
            grouped = {}
            for j in filtered:
                grouped.setdefault(j['model'], []).append(j)
            cards = []
            for model_name, jobs_list in grouped.items():
                total_cells = {}
                done_cells = {}
                region_jobs = {}
                for j in jobs_list:
                    r = j['region']
                    region_jobs.setdefault(r, []).append(j)
                    if r not in total_cells:
                        total_cells[r] = 0
                        done_cells[r] = 0

                # contar tiles processados
                fs = _get_fs()
                t_dir = gcs_full(classified_tiles_dir(model_name))
                for j in jobs_list:
                    if j['status'] == 'RUNNING' and j.get('progress', '0%') != '0%':
                        try:
                            prog = j['progress']
                            if '/' in prog:
                                parts = prog.split('/')
                                done_cells[j['region']] = int(parts[0])
                                total_cells[j['region']] = int(parts[1].split(' ')[0])
                        except Exception:
                            pass

                # thumb
                thumb_b64 = self._generate_thumb(model_name, size=64)

                # card header
                thumb_html = f'<img src="data:image/png;base64,{thumb_b64}" style="width:64px;height:64px;object-fit:cover;border-radius:4px;border:1px solid #ccc;">' if thumb_b64 else '<div style="width:64px;height:64px;background:#f0f0f0;border-radius:4px;border:1px solid #ccc;"></div>'

                # botoes tarea
                tareas = list_tareas(fs=_get_fs())
                tarea_exists = any(t.get('model') == model_name for t in tareas)
                if tarea_exists:
                    btn_tarea = widgets.Button(description='Excluir Tarea del GCS', button_style='warning', layout=L(width='200px', height='28px'))
                    btn_tarea.on_click(lambda _, m=model_name: self._tarea_delete_click(m))
                else:
                    btn_tarea = widgets.Button(description='Guardar Tarea en GCS', button_style='info', layout=L(width='200px', height='28px'))
                    btn_tarea.on_click(lambda _, m=model_name: self._tarea_save_click(m))

                region_lines = []
                for r, jbs in sorted(region_jobs.items()):
                    running = any(j['status'] == 'RUNNING' for j in jbs)
                    status_color = '#e67e22' if running else '#3498db'
                    status_label = 'RUNNING' if running else 'PENDING'
                    tc = total_cells.get(r, 0)
                    dc = done_cells.get(r, 0)
                    prog_str = f"{dc}/{tc}" if tc else jbs[0].get('progress', '0%')
                    grid_n = self._get_grid_count(r)
                    grid_str = f"({grid_n} celdas)" if grid_n else ""

                    btn_del = widgets.Button(description='Eliminar', button_style='danger', layout=L(width='80px', height='26px'))
                    btn_del.on_click(lambda _, m=model_name, rg=r: self._delete_model_region(m, rg))

                    line = widgets.HBox([
                        widgets.HTML(f"<span style='color:{status_color};font-weight:bold;width:90px;'>{status_label}</span>", layout=L(margin='0')),
                        widgets.HTML(f"<b style='width:130px;'>{r}</b>", layout=L(margin='0')),
                        widgets.HTML(f"<span style='color:#555;font-size:12px;'>{prog_str}</span>", layout=L(width='80px')),
                        widgets.HTML(f"<span style='color:#999;font-size:11px;'>{grid_str}</span>", layout=L(width='120px')),
                        btn_del
                    ], layout=L(align_items='center', margin='2px 0', padding='3px'))
                    region_lines.append(line)

                body = widgets.VBox([
                    widgets.HBox([
                        widgets.HTML(thumb_html, layout=L(margin='0 10px 0 0')),
                        widgets.VBox([widgets.HTML(f"<b style='font-size:14px;'>{model_name}</b>"), btn_tarea], layout=L(margin='0'))
                    ], layout=L(align_items='flex-start', margin='0 0 8px 0')),
                    widgets.VBox(region_lines)
                ], layout=L(padding='10px', border='1px solid #ddd', border_radius='5px', margin='5px 0'))
                cards.append(body)

            pend_vbox = widgets.VBox([tarea_section, filter_box, btn_clear] + cards)

        self.tab_pending.children = [pend_vbox]

    def _tarea_save_click(self, model):
        self.queue = load_queue()
        regions = sorted(set(j['region'] for j in self.queue if j['model'] == model))
        periods = sorted(set(j['period'] for j in self.queue if j['model'] == model))
        save_tarea(model, regions, periods)
        with self.out_msg:
            clear_output()
            display(HTML(f"<span style='color:green;'>Tarea guardada en GCS para {model}.</span>"))
        self._refresh_ui()

    def _tarea_delete_click(self, model):
        delete_tarea(model)
        with self.out_msg:
            clear_output()
            display(HTML(f"<span style='color:red;'>Tarea eliminada del GCS: {model}.</span>"))
        self._refresh_ui()

    def _on_clear_click(self):
        self.queue = []
        save_queue(self.queue)
        with self.out_msg:
            clear_output()
            display(HTML("<b style='color:red;'>Cola vaciada.</b>"))
        self._refresh_ui()

    # --- RENDER PUBLISH ---

    def _render_publish(self):
        self.queue = load_queue()
        jobs = [j for j in self.queue if j['status'] == 'COMPLETED']
        filter_box = widgets.HBox([self.f_pub_model, self.f_pub_region, self.f_pub_year], layout=L(margin='0 0 15px 0'))
        filtered = self._apply_filters(jobs, self.f_pub_model, self.f_pub_region, self.f_pub_year)

        if not filtered:
            self.w_pub_rows.children = [widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>Ninguna tarea lista para publicar.</i></div>")]
        else:
            grouped = {}
            for j in filtered:
                grouped.setdefault(j['model'], []).append(j)
            cards = []
            for model_name, jobs_list in grouped.items():
                title = widgets.HTML(f"<h4 style='margin:0; color:#2c3e50; padding:10px; background-color:#ecf0f1; border-radius:5px 5px 0 0;'>Modelo: {model_name}</h4>")
                rows = []
                for job in jobs_list:
                    tile_out = widgets.VBox([])
                    btn_tiles = self._build_tile_expander(job, tile_out)
                    chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f"{job['region']} | {job['period']}", style={'description_width': 'initial'}, layout=L(width='auto', max_width='100%'))
                    chk_gee.observe(lambda change, jid=job['id']: self._toggle_gee(change, jid), names='value')
                    lbl_status = widgets.HTML(f"<span style='color:#27ae60; font-weight:bold; width:80px; display:inline-block;'>{job['status']}</span>")
                    btn_del_all = widgets.Button(description='Eliminar Todo', button_style='danger', layout=L(width='120px', height='28px'))
                    btn_del_all.on_click(lambda _, jb=job: self._confirm_delete_job(jb))
                    top = widgets.HBox([chk_gee, lbl_status, btn_tiles, btn_del_all], layout=L(align_items='center', border_bottom='1px solid #eee', padding='5px'))
                    rows.append(widgets.VBox([top, tile_out]))
                body = widgets.VBox(rows, layout=L(padding='10px', border='1px solid #ecf0f1', border_top='none', border_radius='0 0 5px 5px'))
                cards.append(widgets.VBox([title, body], layout=L(margin='0 0 20px 0')))
            self.w_pub_rows.children = cards
        self.tab_publish.children = [filter_box, self.w_pub_rows]

    def _build_tile_expander(self, job, tiles_container):
        btn = widgets.Button(description='Ver Tiles', icon='list', layout=L(width='110px', height='28px'), button_style='info')
        expanded = [False]
        def _toggle(_):
            if not expanded[0]:
                expanded[0] = True
                btn.description = 'Ocultar'
                btn.button_style = ''
                tiles_container.children = [widgets.HTML("<i>Cargando tiles...</i>")]
                self._refresh_tile_list(job, tiles_container)
            else:
                expanded[0] = False
                btn.description = 'Ver Tiles'
                btn.button_style = 'info'
                tiles_container.children = []
        btn.on_click(_toggle)
        return btn

    def _refresh_tile_list(self, job, container):
        fs = _get_fs()
        r, p, m = job['region'], job['period'], job['model']
        t_dir = gcs_full(classified_tiles_dir(m))
        tile_fqpaths = []
        try:
            tile_fqpaths = sorted([t for t in fs.glob(f"{t_dir}/tile_{r}_{p}.tif") if not t.endswith('.aux.xml')])
        except Exception:
            pass
        if not tile_fqpaths:
            tile_fqpaths = []
            try:
                tile_fqpaths = sorted([t for t in fs.glob(f"{t_dir}/tile_{r}_*.tif") if not t.endswith('.aux.xml')])
            except Exception:
                pass
        if not tile_fqpaths:
            container.children = [widgets.HTML("<span style='color:#999; font-size:11px;'>Ningun tile en GCS.</span>")]
            return
        tile_chks = []
        for fp in tile_fqpaths:
            tname = os.path.basename(fp)
            chk = widgets.Checkbox(value=False, description=tname, indent=False, style={'description_width': 'initial'}, layout=L(width='auto', margin='0'))
            tile_chks.append(chk)
        chk_box = widgets.VBox(tile_chks, layout=L(margin='5px 0 5px 20px'))
        btn_del_sel = widgets.Button(description='Eliminar Seleccionados', button_style='danger', layout=L(width='180px', height='26px'))
        def _del_sel(_):
            to_rm = [fp for fp, chk in zip(tile_fqpaths, tile_chks) if chk.value]
            if to_rm:
                n = self._delete_tiles(to_rm, fs)
                with self.out_msg:
                    clear_output()
                    display(HTML(f"<span style='color:red;'>{n} tiles eliminados.</span>"))
                self._refresh_tile_list(job, container)
            else:
                with self.out_msg:
                    clear_output()
                    display(HTML("<span style='color:orange;'>Seleccione tiles para eliminar.</span>"))
        btn_del_sel.on_click(_del_sel)
        btn_del_all = widgets.Button(description='Eliminar Todos', button_style='warning', layout=L(width='130px', height='26px'))
        def _del_all(_):
            n = self._delete_tiles(tile_fqpaths, fs)
            with self.out_msg:
                clear_output()
                display(HTML(f"<span style='color:red;'>{n} tiles eliminados.</span>"))
            self._refresh_tile_list(job, container)
        btn_del_all.on_click(_del_all)
        actions = widgets.HBox([btn_del_sel, btn_del_all], layout=L(margin='3px 0 0 20px'))
        container.children = [chk_box, actions]

    def _confirm_delete_job(self, job):
        out_c = widgets.Output()
        btn_conf = widgets.Button(description='Confirmar Eliminacion', button_style='danger', layout=L(width='180px'))
        btn_canc = widgets.Button(description='Cancelar', button_style='info', layout=L(width='100px'))
        def _do_confirm(_):
            with out_c:
                clear_output()
                print("Eliminando tiles y mosaico de GCS...")
            n = self._delete_job_tiles_region(job)
            self._remove_from_queue(job['id'])
            with out_c:
                clear_output()
                display(HTML(f"<span style='color:green;'>{n} tiles + mosaico eliminados. Trabajo removido de la cola.</span>"))
        def _cancel(_):
            with out_c:
                clear_output()
                display(HTML("<span style='color:#999;'>Cancelado.</span>"))
        btn_conf.on_click(_do_confirm)
        btn_canc.on_click(_cancel)
        with out_c:
            clear_output()
            display(widgets.HBox([btn_conf, btn_canc]))
        display(out_c)

    # --- RENDER MAPA ---

    def _render_mapa(self):
        self.queue = load_queue()
        filter_box = widgets.HBox([self.f_mapa_model, self.f_mapa_region, self.f_mapa_year, self.btn_mapa_refresh], layout=L(margin='0 0 15px 0'))

        try:
            import ee
            import requests
            if not getattr(ee.data, '_credentials', None):
                from M0_auth_config import authenticate
                authenticate()

            peru = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
            all_regions = ee.FeatureCollection(CONFIG['asset_regions'])
            grid = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")

            bg = peru.style(**{'fillColor': 'f0f0f0', 'color': '2c3e50', 'width': 2})
            region_lines = all_regions.style(**{'color': '2980b9', 'width': 1, 'fillColor': '00000000'})
            grid_lines = grid.style(**{'color': 'bdc3c7', 'width': 0.3, 'fillColor': '00000000'})

            overlay = ee.ImageCollection([bg, region_lines, grid_lines]).mosaic()

            region_val = self.f_mapa_region.value
            if region_val and region_val != 'Todas':
                sel = all_regions.filter(ee.Filter.eq('region_nam', region_val))
                sel_style = sel.style(**{'color': 'e74c3c', 'width': 2, 'fillColor': 'e74c3c20'})
                overlay = ee.ImageCollection([overlay, sel_style]).mosaic()

            # bounds para scale bar
            peru_bounds = peru.geometry().bounds(1, 'EPSG:4326')
            bounds_coords = peru_bounds.getInfo()['coordinates'][0]
            xs = [c[0] for c in bounds_coords]
            ys = [c[1] for c in bounds_coords]
            bounds_info = (min(xs), min(ys), max(xs), max(ys))

            img_w = 600
            url = overlay.getThumbURL({'region': peru_bounds, 'dimensions': img_w, 'format': 'png'})
            resp = requests.get(url, timeout=60)
            b64 = base64.b64encode(resp.content).decode('ascii')
            scale_html = self._build_scale_bar(img_w, bounds_info)

            # grid counts table
            region_names = sorted(set(j['region'] for j in self.queue))
            if not region_names:
                try:
                    region_names = all_regions.aggregate_array('region_nam').distinct().getInfo()
                    region_names = sorted([n for n in region_names if n])
                except Exception:
                    region_names = []
            count_rows = ""
            for rn in region_names:
                n = self._get_grid_count(rn)
                if n is not None:
                    count_rows += f"<tr><td style='padding:2px 8px;'>{rn}</td><td style='padding:2px 8px;text-align:right;'>{n}</td></tr>"
            grid_table = ""
            if count_rows:
                grid_table = ('<div style="margin:8px 0;"><table style="font-size:12px;color:#555;border-collapse:collapse;">'
                              '<tr><th style="padding:2px 8px;border-bottom:1px solid #ccc;text-align:left;">Region</th>'
                              f'<th style="padding:2px 8px;border-bottom:1px solid #ccc;text-align:right;">Celdas cim-world</th></tr>'
                              f'{count_rows}</table></div>')

            legenda = """
            <div style="display:flex;gap:15px;margin:10px 0;font-size:12px;color:#555;">
                <span><span style="display:inline-block;width:12px;height:12px;background:#2c3e50;border-radius:2px;"></span> Peru</span>
                <span><span style="display:inline-block;width:12px;height:12px;background:#2980b9;border-radius:2px;"></span> Regiones</span>
                <span><span style="display:inline-block;width:12px;height:12px;background:#bdc3c7;border-radius:2px;"></span> Grid cim-world</span>
            </div>
            """
            img_html = f'<img src="data:image/png;base64,{b64}" style="max-width:100%; border:1px solid #ccc; border-radius:4px;">'
            self.w_mapa_rows.children = [widgets.HTML(img_html + scale_html + legenda + grid_table)]
        except Exception:
            self.w_mapa_rows.children = [widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>No se pudo generar el mapa. Verifique conexion GEE.</i></div>")]

        self.tab_mapa.children = [filter_box, self.w_mapa_rows]

    # --- RENDER DONE ---

    def _render_done(self):
        self.queue = load_queue()
        jobs = [j for j in self.queue if j['status'] == 'FINISHED']
        filter_box = widgets.HBox([self.f_done_model, self.f_done_region, self.f_done_year], layout=L(margin='0 0 15px 0'))
        filtered = self._apply_filters(jobs, self.f_done_model, self.f_done_region, self.f_done_year)

        if not filtered:
            self.w_done_rows.children = [widgets.HTML("<div style='padding:20px; text-align:center; color:#999; border:1px dashed #ccc;'><i>Ninguna tarea finalizada aun.</i></div>")]
        else:
            grouped = {}
            for j in filtered:
                grouped.setdefault(j['model'], []).append(j)
            cards = []
            all_periods = self._get_all_periods()

            for model_name, jobs_list in grouped.items():
                region_jobs = {}
                for j in jobs_list:
                    region_jobs.setdefault(j['region'], []).append(j)

                thumb_b64 = self._generate_thumb(model_name, size=128)
                thumb_html = f'<img src="data:image/png;base64,{thumb_b64}" style="width:128px;height:128px;object-fit:cover;border-radius:4px;border:1px solid #ccc;">' if thumb_b64 else '<div style="width:128px;height:128px;background:#f0f0f0;border-radius:4px;border:1px solid #ccc;"></div>'

                region_lines = []
                for r, jbs in sorted(region_jobs.items()):
                    timelines = []
                    for year, months in sorted(all_periods.items()):
                        tl = self._build_year_line(year, months, jbs)
                        if tl.strip():
                            timelines.append(tl)
                    tl_html = "<div style='overflow-x:auto;'>" + "".join(timelines) + "</div>"

                    btn_del_region = widgets.Button(description='Eliminar Region', button_style='danger', layout=L(width='140px', height='28px'))
                    btn_del_region.on_click(lambda _, m=model_name, rg=r: self._confirm_delete_model_region(m, rg))

                    line = widgets.HBox([
                        widgets.HTML(f"<b style='width:110px;'>{r}</b>", layout=L(margin='0 5px 0 0')),
                        widgets.HTML(tl_html, layout=L(margin='0 5px 0 0')),
                        btn_del_region
                    ], layout=L(align_items='center', margin='4px 0', padding='5px', border_bottom='1px solid #f0f0f0'))
                    region_lines.append(line)

                btn_del_model = widgets.Button(description='Eliminar Modelo Completo', button_style='danger', layout=L(width='220px', height='28px'))
                btn_del_model.on_click(lambda _, m=model_name: self._confirm_delete_model_all(m))

                card = widgets.VBox([
                    widgets.HBox([
                        widgets.HTML(thumb_html, layout=L(margin='0 10px 0 0')),
                        widgets.VBox([
                            widgets.HTML(f"<b style='font-size:15px;'>{model_name}</b>"),
                            widgets.VBox(region_lines),
                            btn_del_model
                        ], layout=L(width='100%'))
                    ], layout=L(align_items='flex-start'))
                ], layout=L(padding='12px', border='1px solid #27ae60', border_radius='6px', margin='8px 0', background='#f0faf0'))
                cards.append(card)

            self.w_done_rows.children = cards
        self.tab_done.children = [filter_box, self.w_done_rows]

    def _confirm_delete_model_region(self, model, region):
        out_c = widgets.Output()
        btn_conf = widgets.Button(description='Confirmar Eliminacion', button_style='danger', layout=L(width='200px'))
        btn_canc = widgets.Button(description='Cancelar', button_style='info', layout=L(width='100px'))
        def _do(_):
            with out_c:
                clear_output()
                print(f"Eliminando {model} / {region} de GCS...")
            n_tiles, n_jobs = self._delete_model_region(model, region)
            with out_c:
                clear_output()
                display(HTML(f"<span style='color:green;'>{n_tiles} tiles + mosaico + stats eliminados. {n_jobs} trabajos removidos.</span>"))
            self._refresh_ui()
        def _cancel(_):
            with out_c:
                clear_output()
                display(HTML("<span style='color:#999;'>Cancelado.</span>"))
        btn_conf.on_click(_do)
        btn_canc.on_click(_cancel)
        with out_c:
            clear_output()
            display(widgets.HBox([btn_conf, btn_canc]))
        display(out_c)

    def _confirm_delete_model_all(self, model):
        out_c = widgets.Output()
        btn_conf = widgets.Button(description='Confirmar Eliminacion Total', button_style='danger', layout=L(width='220px'))
        btn_canc = widgets.Button(description='Cancelar', button_style='info', layout=L(width='100px'))
        def _do(_):
            with out_c:
                clear_output()
                print(f"Eliminando todo el modelo {model} de GCS...")
            n_tiles, n_jobs = self._delete_model_all(model)
            with out_c:
                clear_output()
                display(HTML(f"<span style='color:green;'>{n_tiles} tiles + mosaicos + stats eliminados. {n_jobs} trabajos removidos.</span>"))
            self._refresh_ui()
        def _cancel(_):
            with out_c:
                clear_output()
                display(HTML("<span style='color:#999;'>Cancelado.</span>"))
        btn_conf.on_click(_do)
        btn_canc.on_click(_cancel)
        with out_c:
            clear_output()
            display(widgets.HBox([btn_conf, btn_canc]))
        display(out_c)

    # --- MANIPULADORES ---

    def _toggle_gee(self, change, job_id):
        if 'new' in change:
            self.queue = load_queue()
            for j in self.queue:
                if j['id'] == job_id:
                    j['upload_gee'] = change['new']
            save_queue(self.queue)

    def _apply_filters(self, jobs, f_model, f_region, f_year):
        if f_model.value != 'Todos':
            jobs = [j for j in jobs if j['model'] == f_model.value]
        if f_region.value != 'Todas':
            jobs = [j for j in jobs if j['region'] == f_region.value]
        if f_year.value != 'Todos':
            jobs = [j for j in jobs if j['period'].split('_')[0] == f_year.value]
        return jobs

    # --- REFRESH ---

    def _refresh_ui(self):
        self.queue = load_queue()

        def _safe_update(f, new_ops):
            old = f.value
            f.options = new_ops
            if old in new_ops:
                f.value = old
            else:
                f.value = new_ops[0]

        for status, f_m, f_r, f_y in [
            (['PENDING', 'RUNNING'], self.f_pend_model, self.f_pend_region, self.f_pend_year),
            (['COMPLETED'], self.f_pub_model, self.f_pub_region, self.f_pub_year),
            (['FINISHED'], self.f_done_model, self.f_done_region, self.f_done_year),
        ]:
            subset = [j for j in self.queue if j['status'] in status]
            _safe_update(f_m, ['Todos'] + sorted(set(j['model'] for j in subset)))
            _safe_update(f_r, ['Todas'] + sorted(set(j['region'] for j in subset)))
            _safe_update(f_y, ['Todos'] + sorted(set(j['period'].split('_')[0] for j in subset), reverse=True))

        # Mapa filters
        all_models = sorted(set(j['model'] for j in self.queue))
        all_regions = sorted(set(j['region'] for j in self.queue))
        all_years = sorted(set(j['period'].split('_')[0] for j in self.queue), reverse=True)
        for f_m, f_r, f_y in [(self.f_mapa_model, self.f_mapa_region, self.f_mapa_year)]:
            _safe_update(f_m, ['Todos'] + all_models)
            _safe_update(f_r, ['Todas'] + all_regions)
            _safe_update(f_y, ['Todos'] + all_years)

        self._render_pending()
        self._render_publish()
        self._render_mapa()
        self._render_done()

    def display(self):
        self._build_guide()
        self._refresh_ui()

        form = widgets.VBox([
            self.w_model_box, self.w_region_box, self.w_period_box,
            widgets.HBox([self.btn_add], layout=L(margin='15px 0 10px 0', align_items='center')),
            self.out_msg
        ], layout=L(padding='20px'))

        self.tabs.children = [self.w_guide, form, self.tab_pending, self.tab_publish, self.tab_mapa, self.tab_done]
        self.tabs.set_title(0, 'Guia')
        self.tabs.set_title(1, 'Registrar')

        n_pend = len([j for j in self.queue if j['status'] in ('PENDING', 'RUNNING')])
        self.tabs.set_title(2, f'Pendientes ({n_pend})')
        self.tabs.set_title(3, 'Para Publicar')
        self.tabs.set_title(4, 'Mapa')

        n_done = len([j for j in self.queue if j['status'] == 'FINISHED'])
        self.tabs.set_title(5, f'Finalizadas ({n_done})')

        header_actions = widgets.HBox([
            widgets.HTML("<b style='color:#2c3e50; font-size:14px; margin-right:15px;'>Acciones Globales:</b>"),
            self.btn_refresh
        ], layout=L(margin='0 0 15px 0', align_items='center', padding='10px', border='1px solid #e0e0e0', background_color='#fcfcfc', border_radius='5px'))

        display(widgets.VBox([header_actions, self.tabs]))


def run_m5_ui(years=None, peridiocity_active=None):
    ui = M5QueueUI(years=years, peridiocity_active=peridiocity_active)
    ui.display()
    return ui