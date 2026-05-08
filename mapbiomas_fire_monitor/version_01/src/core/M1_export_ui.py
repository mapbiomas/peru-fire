print("\n>>> M1_export_ui inicializando (v7.0 Tabs) <<<")
import ee
import traceback
import threading
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name, is_edit_mode
import M0_auth_config as config_module
from M_cache import CacheManager
from M_ui_components import PipelineStepUI
from M1_export_logic import get_quality_mosaic, export_to_asset, export_to_gcs, clear_gcs_chunks, delete_gcs_band, delete_asset_band

class ExportDispatcherUI(PipelineStepUI):
    RELEASE_DAY = 2
    TASK_LIMIT  = 50

    def __init__(self, years=None):
        super().__init__(
            title="M1 - Despachador de Mosaicos", 
            description="Interface multi-sensor para despachar composições (Assets/GCS) para a nuvem."
        )
        self.chk_dict = {}
        self.requested_years = years
        self.btn_refresh = None
        self.is_refreshing = False
        
        try:
            self.main_area.children = [widgets.HTML("<i>Cargando interfaz...</i>")]
        except Exception as e:
            print(f"ERRO CRITICO NA INTERFACE: {e}")
            traceback.print_exc()

    def _init_data(self):
        import datetime
        self.now = datetime.datetime.now()
        curr_year = self.now.year
        if self.requested_years:
            self.years = sorted(self.requested_years, reverse=True)
        else:
            self.years = list(range(curr_year, 2018, -1))
        self.bands = CONFIG['bands_all']
        self.update_status("Cargando cache...")
        self.state = CacheManager.load() or {}
        self.gcs_chunks = self.state.get('gcs_chunks', {})

    def _get_active_tasks(self):
        try:
            tasks = ee.data.getTaskList() 
            active = [t.get('description', '') for t in tasks[:1000] if t.get('state') in ['RUNNING', 'PENDING', 'READY']]
            return active
        except Exception:
            return []

    _DATE_W  = '100px'
    _TYPE_W  = '60px'
    _SEL_W   = '40px'
    _CELL_W  = '80px'

    def _on_select_all(self, _):
        rw = is_edit_mode()
        for chk in self.chk_dict.values():
            if not chk.disabled and (rw or not chk._meta.get('exists')): chk.value = True

    def _on_select_none(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = False

    def _on_select_row(self, btn):
        prefix = f"{btn._sensor}_{btn._period}_{btn._mosaic}_{btn._date}_"
        row_chks = [chk for key, chk in self.chk_dict.items() if key.startswith(prefix) and not chk.disabled]
        if not row_chks: return
        any_on = any(chk.value for chk in row_chks)
        target_val = not any_on
        for chk in row_chks: chk.value = target_val

    def _build_mosaic_grid(self, sensor, period, mosaic_method, active_tasks):
        L = widgets.Layout
        
        hdr = [
            widgets.HTML('<div style="width:100px;">Data</div>'),
            widgets.HTML('<div style="width:60px;">Tipo</div>'),
            widgets.HTML('<div style="width:40px; text-align:center; font-weight:bold;">[S]</div>')
        ]
        for b in self.bands:
            h_widget = widgets.HTML(f'<div style="text-align:center; font-weight:bold; font-size:11px;">{b}</div>')
            h_widget.layout.flex = '1'
            hdr.append(h_widget)

        matrix_row_layout = L(
            align_items='center', 
            min_height='35px', 
            border_bottom='1px solid #eee',
            padding='2px 0',
            overflow='visible',
            width='100%'
        )
        
        matrix_rows = [widgets.HBox(hdr, layout=L(
            border_bottom='2px solid #343a40', 
            padding='5px 0',
            min_height='35px',
            overflow='visible'
        ))]
        
        for y in self.years:
            import datetime
            now = datetime.datetime.now()
            
            if period == 'monthly':
                # Se for o ano atual, limita até o mês passado. Caso contrário, todos os 12 meses.
                limit_month = now.month - 1 if y == now.year else 12
                months = range(limit_month, 0, -1)
            else:
                months = [None]
                
            for m in months:
                date_str = f"{y}_{m:02d}" if m else f"{y}"
                name = mosaic_name(y, m, period)
                
                for row_type in ['GCS', 'ASSET']:
                    cells = [
                        widgets.HTML(f'<div style="width:100px;font-family:monospace;">{date_str if row_type=="GCS" else ""}</div>'),
                        widgets.HTML(f'<div style="width:60px;font-weight:bold;color:#666;">{row_type}</div>'),
                    ]
                    
                    btn_s = widgets.Button(description='[S]', layout=L(width='40px', height='28px', padding='0'))
                    btn_s._sensor, btn_s._period, btn_s._mosaic, btn_s._date = sensor, period, mosaic_method, date_str
                    btn_s.on_click(self._on_select_row)
                    cells.append(btn_s)

                    for b in self.bands:
                        # Lógica de existência (COG) vs disponibilidade (Chunks)
                        m_name = mosaic_name(y, m, period, band=b, mosaic=mosaic_method, sensor=sensor)
                        m_base_name = mosaic_name(y, m, period, mosaic=mosaic_method, sensor=sensor)
                        
                        # 1. Verifica no GCS (Chunks)
                        # Cache salva chaves em lowercase; normalizar para garantir compatibilidade
                        chunks_dict = self.state.get('gcs_chunks', {})
                        exists_gcs = b in chunks_dict.get(m_base_name.lower(), [])
                        
                        # 2. Verifica no GEE (Assets)
                        # Cache normaliza para lowercase; comparar com .lower() para evitar mismatch
                        assets_key = 'assets_monthly' if period == 'monthly' else 'assets_annually'
                        assets_list = self.state.get(assets_key, [])
                        exists_gee = m_name.lower() in assets_list
                        
                        # 3. Verifica se está rodando no GEE
                        # A descrição contém o nome da imagem (m_name)
                        m_name_lower = m_name.lower()
                        # Busca apenas se o nome base da imagem está presente na descrição da tarefa
                        # Isso funciona mesmo se o prefixo da tarefa for MONITOR_01 ou outro.
                        is_active = any(m_name_lower in t.lower() for t in active_tasks)
                        
                        chk = widgets.Checkbox(value=False, indent=False, layout=L(width='18px', height='18px', margin='0'))
                        chk._meta = {'sensor': sensor, 'period': period, 'mosaic': mosaic_method, 'year': y, 'month': m, 'band': b, 'type': row_type}
                        
                        exists = exists_gcs if row_type == 'GCS' else exists_gee
                        chk._meta['exists'] = exists
                        
                        if is_active:
                            status, css = 'RUN', 'mfm-run'
                        elif exists:
                            status, css = 'OK', 'mfm-ok'
                        else:
                            status, css = 'MISS', 'mfm-null'
                        
                        # Se já existe ou está rodando, desabilita a seleção, A MENOS que seja edit_mode
                        if not is_edit_mode():
                            if exists or is_active: chk.disabled = True
                        
                        cell = PipelineStepUI.make_status_cell(chk, status, css, width='auto')
                        cell.layout.flex = '1'
                        self.chk_dict[f"{sensor}_{period}_{mosaic_method}_{date_str}_{row_type}_{b}"] = chk
                        cells.append(cell)
                        
                    matrix_rows.append(widgets.HBox(cells, layout=matrix_row_layout))
        
        return widgets.VBox(matrix_rows, layout=L(
            max_height='450px', 
            width='100%',
            overflow_y='auto', 
            overflow_x='hidden',
            padding='10px', 
            border='1px solid #ddd',
            background_color='#fff'
        ))

    def _build_ui(self):
        self._init_data()
        # Limpa widgets de título da classe base para usar o novo header compacto
        self.header_title.value = ""
        self.header_desc.value = ""
        # Remove loader do topo para não ficar duplicado (já estará no footer)
        self.header_box.children = [self.header_title]
        
        L = widgets.Layout
        self.chk_dict = {}

        # --- HEADER COMPACTO (LINHA ÚNICA) ---
        header_html = f'''
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 5px 10px; background: #fff; border-bottom: 2px solid #333; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-weight: bold; font-size: 16px; color: #333;">M1 - Despachador</span>
                <span style="color: #888; font-size: 11px; font-style: italic;">Interface multi-sensor para exportação</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; padding: 3px 12px; background: #fff1f0; border: 1px solid #ffa39e; border-radius: 4px;">
                <span style="color: #cf1322; font-size: 10px; font-weight: bold; text-transform: uppercase;">Project</span>
                <span style="color: #cf1322; font-weight: bold; font-size: 12px;">MapBiomas Fire Monitor</span>
            </div>
        </div>
        '''
        
        # --- FOOTER DE CONTROLE ---
        self.btn_refresh = widgets.Button(description="Sincronizar Datos", button_style='success', icon='refresh', layout=L(width='180px'))
        self.btn_refresh.on_click(lambda _: self._refresh_cache())
        
        btn_all = widgets.Button(description="Seleccionar Pendientes", button_style='info', layout=L(width='180px'))
        btn_none = widgets.Button(description="Limpiar Selección", button_style='warning', layout=L(width='150px'))
        btn_all.on_click(self._on_select_all)
        btn_none.on_click(self._on_select_none)
        
        # Loader integrado ao lado do botão de sincronizar
        footer = widgets.VBox([
            widgets.HBox([btn_all, btn_none, self.btn_refresh, self.loader_html], layout=L(margin='15px 0', gap='10px', align_items='center'))
        ])

        # --- SISTEMA DE ABAS (TABS) ---
        sensors = ['SENTINEL2'] #, 'LANDSAT', 'HLS', 'MODIS']
        periods = ['monthly'] #, 'yearly']
        methods = ['minnbr', 'minnbr_buffer'] #, 'median', 'minndvi']
        
        self.update_status("Sincronizando tarefas GEE...")
        active_tasks = self._get_active_tasks()
        
        self.sensor_tabs = widgets.Tab()
        self.sensor_children = []
        self.tab_map = {} # (s_idx, p_idx, m_idx) -> (sensor, period, method)

        for i, s in enumerate(sensors):
            period_tabs = widgets.Tab()
            period_children = []
            for j, p in enumerate(periods):
                method_tabs = widgets.Tab()
                method_children = []
                for k, m in enumerate(methods):
                    # Placeholder para cada método
                    placeholder = widgets.VBox([widgets.HTML(f"<i>Clique para cargar {s} {p} ({m})...</i>")], layout=L(padding='20px'))
                    method_children.append(placeholder)
                    self.tab_map[(i, j, k)] = (s.lower(), p, m)
                
                method_tabs.children = method_children
                for k, m in enumerate(methods):
                    method_tabs.set_title(k, m.upper())
                
                # Monitorar mudança de método
                method_tabs.observe(lambda change, si=i, pi=j: self._on_method_change(change, si, pi), names='selected_index')
                period_children.append(method_tabs)
            
            period_tabs.children = period_children
            for j, p in enumerate(periods):
                period_tabs.set_title(j, p.capitalize())
            
            period_tabs.observe(lambda change, si=i: self._on_period_change(change, si), names='selected_index')
            self.sensor_children.append(period_tabs)
        
        self.sensor_tabs.children = self.sensor_children
        for i, s in enumerate(sensors):
            self.sensor_tabs.set_title(i, s)
            
        self.sensor_tabs.observe(self._on_sensor_change, names='selected_index')

        # Gatilho inicial: Carrega S2 Monthly minnbr
        self._load_tab(0, 0, 0, active_tasks)

        # --- FOOTER ---
        btn_all = widgets.Button(description="Seleccionar Pendientes", button_style='info', layout=L(width='180px'))
        btn_none = widgets.Button(description="Limpiar Selección", button_style='warning', layout=L(width='150px'))
        btn_all.on_click(self._on_select_all)
        btn_none.on_click(self._on_select_none)
        
        btn_exp_asset = widgets.Button(description="Exportar a GEE (Asset)", button_style='primary', icon='cloud-upload', layout=L(width='220px'))
        btn_exp_gcs = widgets.Button(description="Exportar a GCS (Chunks)", button_style='primary', icon='database', layout=L(width='220px'))
        btn_exp_asset.on_click(lambda _: start_export(self, 'ASSET'))
        btn_exp_gcs.on_click(lambda _: start_export(self, 'GCS'))

        # --- RESTAURAÇÃO DE ESTADO ---
        if hasattr(self, '_last_sensor_idx'):
            try:
                self.sensor_tabs.selected_index = self._last_sensor_idx
                s_tab = self.sensor_children[self._last_sensor_idx]
                s_tab.selected_index = self._last_period_idx
                m_tab = s_tab.children[self._last_period_idx]
                m_tab.selected_index = self._last_method_idx
                # Força o carregamento da aba restaurada
                self._load_tab(self._last_sensor_idx, self._last_period_idx, self._last_method_idx, active_tasks)
            except: pass

        self.clear_main()
        self.main_area.children = [PipelineStepUI.get_status_css(), widgets.HTML(header_html), self.sensor_tabs, footer]

    def _on_sensor_change(self, change):
        s_idx = change['new']
        p_tabs = self.sensor_children[s_idx]
        p_idx = p_tabs.selected_index
        m_idx = p_tabs.children[p_idx].selected_index
        self._load_tab(s_idx, p_idx, m_idx)

    def _on_period_change(self, change, s_idx):
        p_idx = change['new']
        p_tabs = self.sensor_children[s_idx]
        m_idx = p_tabs.children[p_idx].selected_index
        self._load_tab(s_idx, p_idx, m_idx)

    def _on_method_change(self, change, s_idx, p_idx):
        m_idx = change['new']
        self._load_tab(s_idx, p_idx, m_idx)

    def _load_tab(self, s_idx, p_idx, m_idx, active_tasks=None):
        if active_tasks is None:
            active_tasks = self._get_active_tasks()
            
        sensor, period, method = self.tab_map[(s_idx, p_idx, m_idx)]
        p_tabs = self.sensor_children[s_idx]
        method_tabs = p_tabs.children[p_idx]
        
        # Se já foi carregado (não é mais o placeholder), ignora
        target_container = method_tabs.children[m_idx]
        if not isinstance(target_container.children[0], widgets.HTML) or "Clique para cargar" not in target_container.children[0].value:
            return

        # Build grid for this specific mosaic method
        grid = self._build_mosaic_grid(sensor, period, method, active_tasks)
        
        # Atualiza a aba com o conteúdo real
        new_children = list(method_tabs.children)
        new_children[m_idx] = grid
        method_tabs.children = new_children

    def _refresh_cache(self):
        if self.is_refreshing: return
        try:
            self.is_refreshing = True
            
            # Salva o estado atual das abas aninhadas
            if hasattr(self, 'sensor_tabs'):
                self._last_sensor_idx = self.sensor_tabs.selected_index
                s_tab = self.sensor_children[self._last_sensor_idx]
                self._last_period_idx = s_tab.selected_index
                m_tab = s_tab.children[self._last_period_idx]
                self._last_method_idx = m_tab.selected_index
                
            self.show_loader("Sincronizando...")
            self.state = CacheManager.build_full_cache(logger=self.update_status, years=self.years)
            self._build_ui()
        finally:
            self.is_refreshing = False
            self.hide_loader()

def run_ui(years=None):
    ui = ExportDispatcherUI(years=years)
    ui.display() 
    ui.show_loader("Cargando...")
    ui._build_ui()
    ui.hide_loader()
    return ui

def start_export(ui_obj, mode=None):
    """
    Dispara exportações selecionadas. 
    Se mode for None, dispara tanto ASSET quanto GCS conforme a seleção na UI.
    """
    selected = []
    for chk in ui_obj.chk_dict.values():
        if chk.value:
            meta = chk._meta
            if mode is None or meta['type'] == mode:
                selected.append(meta)
    
    if not selected:
        print("⚠️ Nenhuma opção selecionada para exportação.")
        return

    from M1_export_logic import export_to_asset, export_to_gcs
    from M0_auth_config import mosaic_name

    # Agrupa por tipo para log
    asset_count = len([m for m in selected if m['type'] == 'ASSET'])
    gcs_count = len([m for m in selected if m['type'] == 'GCS'])
    
    print(f"🚀 Iniciando {len(selected)} exportações ({asset_count} Assets, {gcs_count} GCS)...")

    import M1_export_logic as logic
    from M0_auth_config import CONFIG, mosaic_name
    
    # Obtém a geometria simplificada (Bounding Box) apenas uma vez
    # Usar .bounds() evita que o GEE processe o contorno detalhado do país no momento do envio
    country_geom = ee.FeatureCollection(CONFIG['asset_regions']).geometry().bounds()

    for i, meta in enumerate(selected, 1):
        y, m, p, band, mosaic_m, sensor = meta['year'], meta['month'], meta['period'], meta['band'], meta['mosaic'], meta['sensor']
        
        # Nome BASE (sem data): image_peru_fire_sentinel2_minnbr
        name_base = mosaic_name(y, m, p, mosaic=mosaic_m, sensor=sensor, band=None).replace(f"_{y}_{m:02d}", "").replace(f"_{y}", "")
        # Nome COMPLETO (para Asset): image_peru_fire_sentinel2_minnbr_blue_2026_03
        name_full = mosaic_name(y, m, p, mosaic=mosaic_m, sensor=sensor, band=band)
        
        print(f"  [{i}/{len(selected)}] Enviando {sensor} {mosaic_m} ({band}) {y}-{m:02d} para {meta['type']}...")

        # Calcula intervalo de datas simplificado
        start_date = f"{y}-{m:02d}-01" if p == 'monthly' else f"{y}-01-01"
        end_date = (f"{y}-{m+1:02d}-01" if p == 'monthly' and m < 12 
                    else f"{y+1}-01-01" if p == 'monthly' or p == 'yearly'
                    else f"{y}-{m:02d}-28") # fallback seguro

        # 1. Gera o mosaico
        mosaic_obj = logic.get_quality_mosaic(sensor, y, start_date, end_date, country_geom, month=m, method=mosaic_m)
        
        if meta['type'] == 'ASSET':
            # Passar a banda como string simples para evitar paths com ['band']
            logic.export_to_asset(mosaic_obj, name_full, y, m, p, band=band)
        else:
            # GCS usa o nome base, pois a função logic.export_to_gcs monta o nome final
            logic.export_to_gcs(mosaic_obj, name_base, y, m, p, bands=[band])
            
    print(f"\n✅ Concluído! {len(selected)} tarefas enviadas.")
