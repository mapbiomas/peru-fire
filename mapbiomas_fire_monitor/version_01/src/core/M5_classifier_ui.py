import os
import base64
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from M0_auth_config import CONFIG, GLOBAL_OPTS, _get_fs
from M5_queue import load_queue, save_queue, make_job_id, new_job, gcs_full, classified_tiles_dir, \
    tarea_path, save_tarea, delete_tarea, list_tareas
from M4_data_extractor import list_campaigns_gcs
from M_ui_components import inline_confirm, make_spinner, make_empty_state, build_thumbnail_column, make_task_badges, make_card_body, flash_output
from M_lang import L as Lang
from M_regions import REGION_NAME_PROPERTY

L = widgets.Layout

class M5QueueUI:
    def __init__(self, years=None, periodicity_active=None):
        self.years = years or [2025, 2026]
        self.periodicity_active = periodicity_active or ['monthly']
        self.queue = load_queue()

        self._thumb_cache = {}
        self._grid_count_cache = {}
        self._processing_state = {}
        self._card_checkboxes = {}
        self._live_status_out = widgets.Output()

        self.w_model_box = widgets.VBox()
        self.w_region_box = widgets.VBox()
        self.w_period_box = widgets.VBox()

        self.chk_models = []
        self.chk_regions = []
        self.chk_periods = []

        self.btn_add = widgets.Button(description=Lang.ADD_BATCH, button_style='primary', icon='plus', layout=L(width='200px'))
        self.btn_add.on_click(self._on_add_click)

        self.btn_refresh = widgets.Button(description=Lang.REFRESH_VIEW, icon='refresh', layout=L(width='150px'))
        self.btn_refresh.on_click(lambda _: self._refresh_ui())

        self.w_task_name = widgets.Text(
            value='',
            placeholder=Lang.TASK_NAME_PLACEHOLDER,
            description=Lang.DROP_TASK_NAME,
            disabled=False,
            layout=L(width='600px')
        )

        self.w_campaign = widgets.Dropdown(
            options=['carregando...'],
            value='carregando...',
            description='Campanha:',
            layout=L(width='400px')
        )
        self.w_campaign.observe(self._on_campaign_change, names='value')

        self.f_pend_task = widgets.Dropdown(description=Lang.DROP_TASK, options=[Lang.ALL_F], layout=L(width='300px'))
        self.f_pend_task.observe(lambda _: self._render_pending(), names='value')

        self.f_pub_task = widgets.Dropdown(description=Lang.DROP_TASK, options=[Lang.ALL_F], layout=L(width='300px'))
        self.f_pub_task.observe(lambda _: self._render_publish(), names='value')

        self.f_done_task = widgets.Dropdown(description=Lang.DROP_TASK, options=[Lang.ALL_F], layout=L(width='300px'))
        self.f_done_task.observe(lambda _: self._render_done(), names='value')

        self.w_guide = widgets.HTML()

        self.w_pend_rows = widgets.VBox()
        self.tab_pending = widgets.VBox()
        self.f_pend_model = widgets.Dropdown(description=Lang.DROP_MODEL, options=[Lang.ALL], layout=L(width='250px'))
        self.f_pend_region = widgets.Dropdown(description=Lang.DROP_REGION, options=[Lang.ALL_F], layout=L(width='250px'))
        self.f_pend_year = widgets.Dropdown(description=Lang.DROP_YEAR, options=[Lang.ALL], layout=L(width='200px'))
        for f in [self.f_pend_model, self.f_pend_region, self.f_pend_year]:
            f.observe(lambda _: self._render_pending(), names='value')

        self.w_pub_rows = widgets.VBox()
        self.tab_publish = widgets.VBox()
        self.f_pub_model = widgets.Dropdown(description=Lang.DROP_MODEL, options=[Lang.ALL], layout=L(width='250px'))
        self.f_pub_region = widgets.Dropdown(description=Lang.DROP_REGION, options=[Lang.ALL_F], layout=L(width='250px'))
        self.f_pub_year = widgets.Dropdown(description=Lang.DROP_YEAR, options=[Lang.ALL], layout=L(width='200px'))
        for f in [self.f_pub_model, self.f_pub_region, self.f_pub_year]:
            f.observe(lambda _: self._render_publish(), names='value')

        self.w_mapa_rows = widgets.VBox()
        self.tab_mapa = widgets.VBox()
        self.f_mapa_model = widgets.Dropdown(description=Lang.DROP_MODEL, options=[Lang.ALL], layout=L(width='250px'))
        self.f_mapa_region = widgets.Dropdown(description=Lang.DROP_REGION, options=[Lang.ALL_F], layout=L(width='250px'))
        self.f_mapa_year = widgets.Dropdown(description=Lang.DROP_YEAR, options=[Lang.ALL], layout=L(width='200px'))
        self.btn_mapa_refresh = widgets.Button(description=Lang.REFRESH_MAP, icon='refresh', layout=L(width='150px'))
        self.btn_mapa_refresh.on_click(lambda _: self._render_mapa())
        for f in [self.f_mapa_model, self.f_mapa_region, self.f_mapa_year]:
            f.observe(lambda _: self._render_mapa(), names='value')

        self.w_done_rows = widgets.VBox()
        self.tab_done = widgets.VBox()
        self.f_done_model = widgets.Dropdown(description=Lang.DROP_MODEL, options=[Lang.ALL], layout=L(width='250px'))
        self.f_done_region = widgets.Dropdown(description=Lang.DROP_REGION, options=[Lang.ALL_F], layout=L(width='250px'))
        self.f_done_year = widgets.Dropdown(description=Lang.DROP_YEAR, options=[Lang.ALL], layout=L(width='200px'))
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
            if "yearly" in self.periodicity_active and y < now.year:
                months.append('')
            if "monthly" in self.periodicity_active:
                max_m = (now.month - 1) if y == now.year else (12 if y < now.year else 0)
                for m in range(1, max_m + 1):
                    months.append(f"{m:02d}")
            if months:
                periods_by_year[y] = months
        return periods_by_year

    # --- THUMBNAIL (GEE) ---

    def _generate_thumb(self, model, size=128, regions=None):
        """Gera thumbnail GEE das cells de um modelo. Cache em memoria."""
        reg_suffix = '_'.join(sorted(regions or []))
        cache_key = f"{model}_{size}_{reg_suffix}"
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

            if regions is not None:
                all_regions = ee.FeatureCollection(CONFIG['asset_regions']).filter(ee.Filter.inList(REGION_NAME_PROPERTY, regions))
            else:
                all_regions = ee.FeatureCollection(CONFIG['asset_regions'])

            bg = peru.style(**{'fillColor': 'f0f0f0', 'color': 'cccccc', 'width': 1})
            region_lines = all_regions.style(**{'color': '2980b9', 'width': 1, 'fillColor': '00000000'})
            grid_lines = grid.style(**{'color': 'e0e0e0', 'width': 0.3, 'fillColor': '00000000'})

            if regions:
                sel_fill = all_regions.style(**{'color': '2980b9', 'width': 1, 'fillColor': '2980b920'})
                layers = [bg, region_lines, grid_lines, sel_fill]
            else:
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
                <li><b>""" + Lang.TAB_REGISTER + """</b> — seleccione modelo + regiones + periodos.</li>
                <li><b>""" + Lang.TAB_PENDING + """</b> — siga la clasificacion tile a tile.</li>
                <li><b>""" + Lang.TAB_PUBLISH + """</b> — trabajos COMPLETED con gestion de tiles.</li>
                <li><b>""" + Lang.TAB_MAP + """</b> — visibilidad general del progreso.</li>
                <li><b>""" + Lang.TAB_DONE + """</b> — trabajos FINISHED con timeline de cobertura.</li>
                <li>Ejecute <code>run_m5_queue()</code> en el notebook para procesar.</li>
            </ol>
            <h4>Eliminacion granular:</h4>
            <ul>
                <li><b>""" + Lang.TAB_PENDING + """</b> — elimine trabajos individuales de la cola.</li>
                <li><b>""" + Lang.TAB_PUBLISH + """</b> — elimine tiles individuales o todos de un trabajo.</li>
                <li><b>""" + Lang.TAB_DONE + """</b> — elimine por region o modelo completo.</li>
                <li>Despues de eliminar, registre nuevamente el trabajo en <b>""" + Lang.TAB_REGISTER + """</b>.</li>
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
            names = fc.aggregate_array(REGION_NAME_PROPERTY).distinct().getInfo()
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
            if "yearly" in self.periodicity_active:
                if y < now.year:
                    periods.append(str(y))
            if "monthly" in self.periodicity_active:
                max_m = (now.month - 1) if y == now.year else (12 if y < now.year else 0)
                for m in range(1, max_m + 1):
                    periods.append(f"{y}_{m:02d}")
        periods.sort(reverse=True)
        box, self.chk_periods = self._create_checkbox_grid(periods, "3. Seleccione Periodos (Anio / Anio_Mes):", bg_color='#ebf5eb', columns=4)
        self.w_period_box.children = box.children

        # Campaign dropdown
        try:
            campaigns = list_campaigns_gcs()
            current = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
            val = current if current in campaigns else (campaigns[0] if campaigns else '')
            self.w_campaign.options = campaigns
            self.w_campaign.value = val
        except Exception:
            self.w_campaign.options = ['monitor_01']
            self.w_campaign.value = 'monitor_01'

    # --- REGISTRAR ---

    def _on_add_click(self, b):
        self.queue = load_queue()
        model = next((c.description for c in self.chk_models if c.value), None)
        regions = [c.description for c in self.chk_regions if c.value]
        periods = [c.description for c in self.chk_periods if c.value]
        task_name = self.w_task_name.value.strip()
        if not task_name:
            with self.out_msg:
                clear_output()
                display(HTML("<b style='color:red;'>Atencion: Debe asignar un Nombre de Tarea obligatoriamente.</b>"))
            return
        if not model or not regions or not periods:
            with self.out_msg:
                clear_output()
                display(HTML("<b style='color:red;'>Atencion: Seleccione 1 Modelo y al menos una Region y un Periodo.</b>"))
            return
        added = 0
        skipped = 0
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
        for r in regions:
            for period in periods:
                job_id = make_job_id(model, r, period, campaign)
                if any(job['id'] == job_id for job in self.queue):
                    skipped += 1
                    continue
                self.queue.append(new_job(model, r, period, task_name=task_name))
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

    def _on_campaign_change(self, change):
        campaign = change['new']
        if campaign and campaign != 'carregando...':
            GLOBAL_OPTS['SAMPLING_CAMPAIGN'] = campaign
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
        c = job.get('campaign', '')
        reg_full = gcs_full(region_path(m, r, p, c))
        try:
            if fs.exists(reg_full):
                fs.rm(reg_full)
        except Exception:
            pass
        t_dir = gcs_full(classified_tiles_dir(m, c))
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
        c = job.get('campaign', '')
        n_tiles = self._delete_job_tiles_region(job)
        s_dir = gcs_full(stats_dir(m, c))
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
        campaigns = set(j.get('campaign', '') for j in jobs)
        for c in campaigns:
            s_dir = gcs_full(stats_dir(model, c))
            for csv_name in ['stats_tile.csv', 'stats_region.csv']:
                try:
                    p = f"{s_dir}/{csv_name}"
                    if fs.exists(p):
                        fs.rm(p)
                except Exception:
                    pass
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

            btn_cargar = widgets.Button(description=Lang.LOAD_TO_QUEUE, button_style='success', layout=L(width='150px', height='28px'))
            def _make_cargar(m, regs, pers):
                def _h(_):
                    campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
                    self.queue = load_queue()
                    added = 0
                    skipped = 0
                    for r in regs:
                        for p in pers:
                            jid = make_job_id(m, r, p, campaign)
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
                fc = ee.FeatureCollection(CONFIG['asset_regions']).filter(ee.Filter.eq(REGION_NAME_PROPERTY, region_name))
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
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
        jobs = [j for j in self.queue if j['status'] in ('PENDING', 'RUNNING') and (not campaign or j.get('campaign', '') == campaign)]

        filter_box = widgets.HBox([self.f_pend_model, self.f_pend_region, self.f_pend_year, self.f_pend_task], layout=L(margin='0 0 10px 0'))
        filtered = self._apply_filters(jobs, self.f_pend_model, self.f_pend_region, self.f_pend_year, self.f_pend_task)

        btn_clear = widgets.Button(description=Lang.CLEAR_TEMP_TASKS, button_style='warning', icon='trash', layout=L(width='200px'))
        btn_clear.on_click(lambda _: self._on_clear_click())

        tarea_section = self._tarea_section()

        if not filtered:
            pend_vbox = widgets.VBox([tarea_section, filter_box, btn_clear,
                make_empty_state(Lang.NO_TASKS)])
        else:
            grouped = {}
            for j in filtered:
                grouped.setdefault(j['model'], []).append(j)
            cards = []
            for model_name, jobs_list in grouped.items():
                total_cells = {}
                done_cells = {}
                region_jobs = {}
                card_regions = []
                for j in jobs_list:
                    r = j['region']
                    if r not in card_regions:
                        card_regions.append(r)
                    region_jobs.setdefault(r, []).append(j)
                    if r not in total_cells:
                        total_cells[r] = 0
                        done_cells[r] = 0

                # contar tiles processados
                fs = _get_fs()
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

                # -- thumb (128px, lado esquerdo) --
                thumb_b64 = self._generate_thumb(model_name, size=128, regions=card_regions)
                left_col = build_thumbnail_column(thumb_b64)

                # -- checkbox de habilitacion --
                chk = widgets.Checkbox(
                    value=self._card_checkboxes.get(model_name, False).value if isinstance(self._card_checkboxes.get(model_name, False), widgets.Checkbox) else self._card_checkboxes.get(model_name, False),
                    description='',
                    indent=False,
                    layout=L(width='24px', margin='2px 6px 0 0')
                )
                chk.observe(lambda change, m=model_name: self._sync_card_enabled(m, change['new']), names='value')
                self._card_checkboxes[model_name] = chk

                # -- botoes tarea + eliminar modelo --
                tareas = list_tareas(fs=_get_fs())
                tarea_exists = any(t.get('model') == model_name for t in tareas)
                if tarea_exists:
                    btn_tarea = widgets.Button(description=Lang.EXCLUDE_TASK_GCS, button_style='warning', layout=L(width='150px', height='28px', font_size='12px'))
                    btn_tarea.on_click(lambda _, m=model_name: self._tarea_delete_click(m))
                else:
                    btn_tarea = widgets.Button(description=Lang.SAVE_TASK_GCS, button_style='info', layout=L(width='150px', height='28px', font_size='12px'))
                    btn_tarea.on_click(lambda _, m=model_name: self._tarea_save_click(m))
                btn_del_model = widgets.Button(description=Lang.DELETE_MODEL, button_style='danger', layout=L(width='140px', height='28px', font_size='12px'))
                hbox_actions = widgets.HBox([btn_tarea, btn_del_model], layout=L(align_items='center', gap='6px', margin='0 0 6px 28px'))
                btn_del_model.on_click(lambda b, m=model_name, c=hbox_actions: inline_confirm(b, lambda: (self._delete_model_all(m), self._refresh_ui()), container=c))

                # -- tarefas (nomes) em badges --
                tarefas_assinadas = sorted(set(j.get('task_name', '') for j in jobs_list if j.get('task_name', '')))
                task_badges = make_task_badges(tarefas_assinadas)

                # -- cabecalho direito --
                header = widgets.VBox([
                    widgets.HBox([
                        chk,
                        widgets.HTML(f"<b style='font-size:15px;color:#0f172a;'>{model_name}</b>",
                                     layout=L(margin='0 10px 0 0')),
                    ], layout=L(align_items='center', margin='0 0 4px 0')),
                    widgets.HTML(f"<div style='margin:2px 0 6px 28px;'>{task_badges}</div>" if task_badges else ''),
                    hbox_actions,
                ], layout=L(width='auto'))

                # -- linhas de regiao --
                region_lines = []
                for r, jbs in sorted(region_jobs.items()):
                    running = any(j['status'] == 'RUNNING' for j in jbs)
                    dot_color = '#f59e0b' if running else '#3b82f6'
                    tc = total_cells.get(r, 0)
                    dc = done_cells.get(r, 0)
                    if tc:
                        pct = min(dc / tc * 100, 100)
                        prog_str = f"{dc}/{tc}"
                    else:
                        pct = 0
                        prog_str = jbs[0].get('progress', '0%')
                    grid_n = self._get_grid_count(r)
                    grid_str = f"({grid_n} celdas)" if grid_n else ""

                    bar_color = '#22c55e' if running else '#3b82f6'
                    bar = (f'<div style="width:100px;height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">'
                           f'<div style="width:{pct:.0f}%;height:100%;background:{bar_color};border-radius:4px;"></div>'
                           f'</div>')

                    btn_del = widgets.Button(description='', icon='trash', button_style='danger',
                                             layout=L(width='32px', height='26px', padding='0'))

                    row = widgets.HBox([
                        widgets.HTML(f'<span style="display:inline-block;width:10px;height:10px;'
                                     f'background:{dot_color};border-radius:50%;margin:0 6px 0 0;"></span>'),
                        widgets.HTML(f"<span style='font-weight:600;color:#334155;width:140px;display:inline-block;'>{r}</span>"),
                        widgets.HTML(f"<span style='color:#64748b;font-size:12px;width:55px;'>{prog_str}</span>"),
                        widgets.HTML(bar, layout=L(margin='0 6px')),
                        widgets.HTML(f"<span style='color:#94a3b8;font-size:11px;'>{grid_str}</span>",
                                     layout=L(width='110px')),
                        btn_del
                    ], layout=L(align_items='center', padding='5px 8px', margin='2px 0',
                                border_bottom='1px solid #f1f5f9'))
                    btn_del.on_click(lambda b, m=model_name, rg=r, c=row: inline_confirm(b, lambda: (self._delete_model_region(m, rg), self._refresh_ui()), container=c))
                    region_lines.append(row)

                right_col = widgets.VBox([header] + region_lines, layout=L(flex='1', margin='0 0 0 12px'))

                body = make_card_body(left_col, right_col)
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

    # --- HABILITACION DE CARDS ---

    def _sync_card_enabled(self, model_name, checked):
        """Seta enabled=True/False em todos jobs de um modelo."""
        self.queue = load_queue()
        for j in self.queue:
            if j['model'] == model_name:
                j['enabled'] = checked
        save_queue(self.queue)
        self._card_checkboxes[model_name].value = checked

    # --- LIVE MAPA (PROCESSING CALLBACK) ---

    def _on_tile_progress(self, model, region, cell_id, i, total, status):
        """Callback chamado de M5_classifier a cada tile."""
        try:
            self._processing_state = {
                'running': True,
                'model': model,
                'region': region,
                'current': cell_id,
                'total': total,
                'completed': sorted(set(self._processing_state.get('completed', []) + ([cell_id] if status in ('done', 'skipped') else []))),
                'current_i': i,
                'last_status': status,
            }
            self._render_mapa_live()
            self.tabs.selected_index = 4
        except Exception:
            pass

    def _render_mapa_live(self):
        """Renderiza Mapa con estado de procesamiento en vivo."""
        state = self._processing_state
        if not state or not state.get('running'):
            return

        model, region = state.get('model', '?'), state.get('region', '?')
        total = state.get('total', 0)
        done_set = set(state.get('completed', []))
        current = state.get('current', '')
        done_n = len(done_set)
        pct = f"{done_n}/{total} ({done_n/total:.0%})" if total else '0/0'

        lines = [f"<tr><td style='padding:2px 8px;'>{Lang.MODEL}</td><td style='padding:2px 8px;'><b>{model}</b></td></tr>",
                 f"<tr><td style='padding:2px 8px;'>{Lang.REGION}</td><td style='padding:2px 8px;'><b>{region}</b></td></tr>",
                 f"<tr><td style='padding:2px 8px;'>{Lang.PROGRESS}</td><td style='padding:2px 8px;'><b>{pct}</b></td></tr>"]
        if current:
            lines.append(f"<tr><td style='padding:2px 8px;'>{Lang.CURRENT_TILE}</td><td style='padding:2px 8px;'><span style='color:#e67e22;font-weight:bold;'>{current}</span></td></tr>")

        # tiles completados
        if done_set:
            done_cells = sorted(done_set)
            done_html = ', '.join(done_cells[:10])
            if len(done_cells) > 10:
                done_html += f' ... (+{len(done_cells)-10} mas)'
            lines.append(f"<tr><td style='padding:2px 8px;'>{Lang.COMPLETED}</td><td style='padding:2px 8px;color:#27ae60;'>{done_html}</td></tr>")

        html = (f'<div style="margin:8px 0;padding:10px;border:2px solid #e67e22;border-radius:6px;'
                f'background:#fef9e7;">'
                f'<b style="color:#e67e22;">{Lang.LIVE_PROCESSING}</b>'
                f'<table style="font-size:12px;color:#555;border-collapse:collapse;margin-top:6px;">'
                f'{"".join(lines)}</table></div>')

        with self._live_status_out:
            clear_output()
            display(HTML(html))

    # --- RENDER PUBLISH ---

    def _render_publish(self):
        self.queue = load_queue()
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
        jobs = [j for j in self.queue if j['status'] == 'COMPLETED' and (not campaign or j.get('campaign', '') == campaign)]
        filter_box = widgets.HBox([self.f_pub_model, self.f_pub_region, self.f_pub_year, self.f_pub_task], layout=L(margin='0 0 15px 0'))
        filtered = self._apply_filters(jobs, self.f_pub_model, self.f_pub_region, self.f_pub_year, self.f_pub_task)

        if not filtered:
            self.w_pub_rows.children = [make_empty_state(Lang.NO_TASKS_PUBLISH)]
        else:
            grouped = {}
            for j in filtered:
                grouped.setdefault(j['model'], []).append(j)
            cards = []
            for model_name, jobs_list in grouped.items():
                card_regions = sorted(set(j['region'] for j in jobs_list))

                # -- thumb 128px esquerda --
                thumb_b64 = self._generate_thumb(model_name, size=128, regions=card_regions)
                left_col = build_thumbnail_column(thumb_b64)

                # -- tarefas badges --
                tarefas_assinadas = sorted(set(j.get('task_name', '') for j in jobs_list if j.get('task_name', '')))
                task_badges = make_task_badges(tarefas_assinadas)

                # -- cabecalho direito --
                header = widgets.VBox([
                    widgets.HTML(f"<b style='font-size:15px;color:#0f172a;'>{model_name}</b>",
                                 layout=L(margin='0 0 4px 0')),
                    widgets.HTML(f"<div style='margin:0 0 6px 0;'>{task_badges}</div>" if task_badges else ''),
                ], layout=L(width='auto', margin='0 0 8px 0'))

                # -- linhas de trabalho --
                rows = []
                for job in jobs_list:
                    tile_out = widgets.VBox([])
                    btn_tiles = self._build_tile_expander(job, tile_out)
                    chk_gee = widgets.Checkbox(value=job.get('upload_gee', False), description=f"{job['region']} | {job['period']}", style={'description_width': 'initial'}, layout=L(width='auto', max_width='100%'))
                    chk_gee.observe(lambda change, jid=job['id']: self._toggle_gee(change, jid), names='value')
                    lbl_status = widgets.HTML(f"<span style='color:#16a34a;font-weight:700;font-size:12px;'>{job['status']}</span>")
                    btn_del_all = widgets.Button(description='', icon='trash', button_style='danger', layout=L(width='32px', height='26px', padding='0'))
                    top = widgets.HBox([chk_gee, lbl_status, btn_tiles, btn_del_all],
                                       layout=L(align_items='center', padding='5px 8px', margin='2px 0',
                                                border_bottom='1px solid #f1f5f9'))
                    btn_del_all.on_click(lambda b, jb=job, c=top: inline_confirm(b, lambda: (self._delete_job_tiles_region(jb), self._remove_from_queue(jb['id']), self._refresh_ui()), container=c))
                    rows.append(widgets.VBox([top, tile_out]))

                right_col = widgets.VBox([header] + rows, layout=L(flex='1', margin='0 0 0 12px'))
                cards.append(make_card_body(left_col, right_col))
            self.w_pub_rows.children = cards
        self.tab_publish.children = [filter_box, self.w_pub_rows]

    def _build_tile_expander(self, job, tiles_container):
        btn = widgets.Button(description=Lang.VIEW_TILES, icon='list', layout=L(width='110px', height='28px'), button_style='info')
        expanded = [False]
        def _toggle(_):
            if not expanded[0]:
                expanded[0] = True
                btn.description = Lang.HIDE_TILES
                btn.button_style = ''
                tiles_container.children = [widgets.HTML(f"<i>{Lang.LOADING_TILES}</i>")]
                self._refresh_tile_list(job, tiles_container)
            else:
                expanded[0] = False
                btn.description = Lang.VIEW_TILES
                btn.button_style = 'info'
                tiles_container.children = []
        btn.on_click(_toggle)
        return btn

    def _refresh_tile_list(self, job, container):
        fs = _get_fs()
        r, p, m = job['region'], job['period'], job['model']
        c = job.get('campaign', '')
        t_dir = gcs_full(classified_tiles_dir(m, c))
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
        btn_del_sel = widgets.Button(description=Lang.DELETE_SELECTED, button_style='danger', layout=L(width='180px', height='26px'))
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
        btn_del_all = widgets.Button(description=Lang.DELETE_ALL, button_style='warning', layout=L(width='130px', height='26px'))
        def _del_all(_):
            n = self._delete_tiles(tile_fqpaths, fs)
            with self.out_msg:
                clear_output()
                display(HTML(f"<span style='color:red;'>{n} tiles eliminados.</span>"))
            self._refresh_tile_list(job, container)
        btn_del_all.on_click(_del_all)
        actions = widgets.HBox([btn_del_sel, btn_del_all], layout=L(margin='3px 0 0 20px'))
        container.children = [chk_box, actions]

    # --- RENDER MAPA ---

    def _render_mapa(self):
        self.queue = load_queue()
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
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
                sel = all_regions.filter(ee.Filter.eq(REGION_NAME_PROPERTY, region_val))
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
            campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
            region_names = sorted(set(j['region'] for j in self.queue if not campaign or j.get('campaign', '') == campaign))
            if not region_names:
                try:
                    region_names = all_regions.aggregate_array(REGION_NAME_PROPERTY).distinct().getInfo()
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
                              '<tr><th style="padding:2px 8px;border-bottom:1px solid #ccc;text-align:left;">'
                              f'{Lang.GRID_REGION}</th>'
                              f'<th style="padding:2px 8px;border-bottom:1px solid #ccc;text-align:right;">'
                              f'{Lang.GRID_CELLS}</th></tr>'
                              f'{count_rows}</table></div>')

            legenda = """
            <div style="display:flex;gap:15px;margin:10px 0;font-size:12px;color:#555;">
                <span><span style="display:inline-block;width:12px;height:12px;background:#2c3e50;border-radius:2px;"></span> Peru</span>
                <span><span style="display:inline-block;width:12px;height:12px;background:#2980b9;border-radius:2px;"></span> Regiones</span>
                <span><span style="display:inline-block;width:12px;height:12px;background:#bdc3c7;border-radius:2px;"></span> Grid cim-world</span>
            </div>
            """
            img_html = f'<img src="data:image/png;base64,{b64}" style="max-width:100%; border:1px solid #ccc; border-radius:4px;">'
            self.w_mapa_rows.children = [widgets.HTML(img_html + scale_html + legenda + grid_table), self._live_status_out]
        except Exception:
            self.w_mapa_rows.children = [make_empty_state(Lang.NO_MAP), self._live_status_out]

        self.tab_mapa.children = [filter_box, self.w_mapa_rows]

    # --- RENDER DONE ---

    def _render_done(self):
        self.queue = load_queue()
        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
        jobs = [j for j in self.queue if j['status'] == 'FINISHED' and (not campaign or j.get('campaign', '') == campaign)]
        filter_box = widgets.HBox([self.f_done_model, self.f_done_region, self.f_done_year, self.f_done_task], layout=L(margin='0 0 15px 0'))
        filtered = self._apply_filters(jobs, self.f_done_model, self.f_done_region, self.f_done_year, self.f_done_task)

        if not filtered:
            self.w_done_rows.children = [make_empty_state(Lang.NO_TASKS_DONE)]
        else:
            grouped = {}
            for j in filtered:
                grouped.setdefault(j['model'], []).append(j)
            cards = []
            all_periods = self._get_all_periods()

            for model_name, jobs_list in grouped.items():
                region_jobs = {}
                card_regions = []
                for j in jobs_list:
                    r = j['region']
                    if r not in card_regions:
                        card_regions.append(r)
                    region_jobs.setdefault(r, []).append(j)

                # -- thumb 128px esquerda --
                thumb_b64 = self._generate_thumb(model_name, size=128, regions=card_regions)
                left_col = build_thumbnail_column(thumb_b64)

                # -- tarefas badges --
                tarefas_assinadas = sorted(set(j.get('task_name', '') for j in jobs_list if j.get('task_name', '')))
                task_badges = make_task_badges(tarefas_assinadas)

                # -- cabecalho direito --
                region_lines = []
                for r, jbs in sorted(region_jobs.items()):
                    timelines = []
                    for year, months in sorted(all_periods.items()):
                        tl = self._build_year_line(year, months, jbs)
                        if tl.strip():
                            timelines.append(tl)
                    tl_html = "<div style='overflow-x:auto;'>" + "".join(timelines) + "</div>"

                    btn_del_region = widgets.Button(description='', icon='trash', button_style='danger',
                                                    layout=L(width='32px', height='26px', padding='0'))

                    line = widgets.HBox([
                        widgets.HTML(f"<b style='width:120px;color:#334155;'>{r}</b>", layout=L(margin='0 8px 0 0')),
                        widgets.HTML(tl_html, layout=L(margin='0 8px 0 0', flex='1')),
                        btn_del_region
                    ], layout=L(align_items='center', padding='5px 8px', margin='2px 0',
                                border_bottom='1px solid #f1f5f9'))
                    btn_del_region.on_click(lambda b, m=model_name, rg=r, c=line: inline_confirm(b, lambda: (self._delete_model_region(m, rg), self._refresh_ui()), container=c))
                    region_lines.append(line)

                btn_del_model = widgets.Button(description=Lang.DELETE_MODEL, button_style='danger', layout=L(width='150px', height='28px'))

                header = widgets.VBox([
                    widgets.HBox([
                        widgets.HTML(f"<b style='font-size:15px;color:#0f172a;'>{model_name}</b>",
                                     layout=L(margin='0 0 4px 0')),
                    ]),
                    widgets.HTML(f"<div style='margin:0 0 6px 0;'>{task_badges}</div>" if task_badges else ''),
                ], layout=L(width='auto', margin='0 0 8px 0'))

                right_col = widgets.VBox([
                    header,
                    widgets.VBox(region_lines, layout=L(margin='0 0 6px 0')),
                    btn_del_model,
                ], layout=L(flex='1', margin='0 0 0 12px'))
                btn_del_model.on_click(lambda b, m=model_name, c=right_col: inline_confirm(b, lambda: (self._delete_model_all(m), self._refresh_ui()), container=c))

                card = make_card_body(left_col, right_col, border_color='#bbf7d0', background='#f0fdf4')
                cards.append(card)

            self.w_done_rows.children = cards
        self.tab_done.children = [filter_box, self.w_done_rows]

    # --- MANIPULADORES ---

    def _toggle_gee(self, change, job_id):
        if 'new' in change:
            self.queue = load_queue()
            for j in self.queue:
                if j['id'] == job_id:
                    j['upload_gee'] = change['new']
            save_queue(self.queue)

    def _apply_filters(self, jobs, f_model, f_region, f_year, f_task=None):
        if f_model.value != 'Todos':
            jobs = [j for j in jobs if j['model'] == f_model.value]
        if f_region.value != 'Todas':
            jobs = [j for j in jobs if j['region'] == f_region.value]
        if f_year.value != 'Todos':
            jobs = [j for j in jobs if j['period'].split('_')[0] == f_year.value]
        if f_task is not None and f_task.value != 'Todas':
            jobs = [j for j in jobs if j.get('task_name', '') == f_task.value]
        return jobs

    # --- REFRESH ---

    def _refresh_ui(self):
        self.queue = load_queue()

        def _safe_update(f, new_ops):
            if not hasattr(f, 'options') or not new_ops:
                return
            old = f.value
            f.options = new_ops
            if old in new_ops:
                f.value = old
            else:
                f.value = new_ops[0]

        campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
        for status, f_m, f_r, f_y, f_t in [
            (['PENDING', 'RUNNING'], self.f_pend_model, self.f_pend_region, self.f_pend_year, self.f_pend_task),
            (['COMPLETED'], self.f_pub_model, self.f_pub_region, self.f_pub_year, self.f_pub_task),
            (['FINISHED'], self.f_done_model, self.f_done_region, self.f_done_year, self.f_done_task),
        ]:
            subset = [j for j in self.queue if j['status'] in status and (not campaign or j.get('campaign', '') == campaign)]
            _safe_update(f_m, ['Todos'] + sorted(set(j['model'] for j in subset)))
            _safe_update(f_r, ['Todas'] + sorted(set(j['region'] for j in subset)))
            _safe_update(f_y, ['Todos'] + sorted(set(j['period'].split('_')[0] for j in subset), reverse=True))
            _safe_update(f_t, ['Todas'] + sorted(set(j.get('task_name', '') for j in subset if j.get('task_name', ''))))

        # Mapa filters
        filtered_queue = [j for j in self.queue if not campaign or j.get('campaign', '') == campaign]
        all_models = sorted(set(j['model'] for j in filtered_queue))
        all_regions = sorted(set(j['region'] for j in filtered_queue))
        all_years = sorted(set(j['period'].split('_')[0] for j in filtered_queue), reverse=True)
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
            widgets.VBox([self.w_campaign, self.w_task_name], layout=L(margin='15px 0 5px 0')),
            widgets.HBox([self.btn_add], layout=L(margin='5px 0 10px 0', align_items='center')),
            self.out_msg
        ], layout=L(padding='20px'))

        self.tabs.children = [self.w_guide, form, self.tab_pending, self.tab_publish, self.tab_mapa, self.tab_done]
        self.tabs.set_title(0, Lang.TAB_GUIDE)
        self.tabs.set_title(1, Lang.TAB_REGISTER)

        n_pend = len([j for j in self.queue if j['status'] in ('PENDING', 'RUNNING')])
        self.tabs.set_title(2, f"{Lang.TAB_PENDING} ({n_pend})")
        self.tabs.set_title(3, Lang.TAB_PUBLISH)
        self.tabs.set_title(4, Lang.TAB_MAP)

        n_done = len([j for j in self.queue if j['status'] == 'FINISHED'])
        self.tabs.set_title(5, f"{Lang.TAB_DONE} ({n_done})")

        header_actions = widgets.HBox([
            widgets.HTML("<b style='color:#2c3e50; font-size:14px; margin-right:15px;'>Acciones Globales:</b>"),
            self.btn_refresh
        ], layout=L(margin='0 0 15px 0', align_items='center', padding='10px', border='1px solid #e0e0e0', background_color='#fcfcfc', border_radius='5px'))

        display(widgets.VBox([header_actions, self.tabs]))


def run_m5_ui(years=None, periodicity_active=None):
    ui = M5QueueUI(years=years, periodicity_active=periodicity_active)
    ui.display()
    return ui