print("\n>>> M1_export_ui inicializando (v6.0 ASCII) <<<")
import ee
import traceback
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name, is_edit_mode
import M0_auth_config as config_module
from M_cache import CacheManager
from M_ui_components import PipelineStepUI
from M1_export_logic import get_quality_mosaic, export_to_asset, export_to_gcs

class ExportDispatcherUI(PipelineStepUI):
    RELEASE_DAY = 2
    TASK_LIMIT  = 50

    def __init__(self, years=None):
        super().__init__(
            title="M1 - Despachador de Mosaicos", 
            description="Interface multi-sensor para despachar composicoes (Assets/GCS) para a nuvem."
        )
        self.chk_dict = {}
        self.requested_years = years
        
        try:
            print("M1: [1/3] Iniciando dados...")
            self._init_data()
            print("M1: [2/3] Construindo interface...")
            self._build_ui()
            print("M1: [3/3] Renderizacao concluida.")
        except Exception as e:
            print(f"ERRO CRITICO NA INTERFACE: {e}")
            traceback.print_exc()

    def _init_data(self):
        self.sensor = GLOBAL_OPTS['SENSOR']
        self.period = GLOBAL_OPTS['PERIODICITY']
        import datetime
        self.now = datetime.datetime.now()
        curr_year = self.now.year
        if self.requested_years:
            self.years = sorted(self.requested_years, reverse=True)
        else:
            self.years = list(range(curr_year, 2018, -1))
        self.bands = CONFIG['bands_all']
        self.log("Carregando cache...", "info")
        self.state = CacheManager.load() or {}
        self.gcs_chunks = self.state.get('gcs_chunks', {})

    def _get_active_tasks(self):
        try:
            tasks = ee.data.getTaskList() 
            return [t.get('description', '') for t in tasks[:self.TASK_LIMIT] if t.get('state') in ['RUNNING', 'PENDING', 'READY']]
        except: return []

    _DATE_W  = '100px'
    _TYPE_W  = '60px'
    _SEL_W   = '40px'
    _CELL_W  = '80px'
    _CELL_PX = 80

    def _on_select_all(self, _):
        rw = is_edit_mode()
        for chk in self.chk_dict.values():
            if not chk.disabled and (rw or not chk._meta.get('exists')): chk.value = True

    def _on_select_none(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = False

    def _on_select_row(self, btn):
        name, row_type = btn._row_name, btn._row_type
        prefix = f"{name}_{row_type}_"
        
        # Filtrar checkboxes desta linha que podem ser clicados (não desabilitados)
        row_chks = [chk for key, chk in self.chk_dict.items() if key.startswith(prefix) and not chk.disabled]
        if not row_chks: return
        
        # Toggle: Se algum estiver ligado, desliga todos. Se todos desligados, liga todos.
        any_on = any(chk.value for chk in row_chks)
        target_val = not any_on
        
        for chk in row_chks:
            chk.value = target_val

    def _build_ui(self):
        active_tasks = self._get_active_tasks()
        css = PipelineStepUI.get_status_css()

        self.btn_all = widgets.Button(description="Selecionar Todos", button_style='info', layout=widgets.Layout(width='155px'))
        self.btn_none = widgets.Button(description="Limpar Selecao", button_style='info', layout=widgets.Layout(width='145px'))
        self.btn_refresh = widgets.Button(description="Atualizar GCS", button_style='success', layout=widgets.Layout(width='150px'))
        self.btn_all.on_click(self._on_select_all)
        self.btn_none.on_click(self._on_select_none)
        self.btn_refresh.on_click(lambda _: self._refresh_cache())
        toolbar = widgets.HBox([self.btn_all, self.btn_none, self.btn_refresh], layout=widgets.Layout(margin='0 0 10px 0'))

        L = widgets.Layout
        hdr = [widgets.HTML('<span class="mfm-hdr">Data</span>', layout=L(width=self._DATE_W)), 
               widgets.HTML('<span class="mfm-hdr">Tipo</span>', layout=L(width=self._TYPE_W)), 
               widgets.HTML('<span class="mfm-hdr">[S]</span>', layout=L(width=self._SEL_W, text_align='center'))]
        for b in self.bands: hdr.append(widgets.HTML(f'<span class="mfm-hdr">{b}</span>', layout=L(width=self._CELL_W, text_align='center')))
        
        matrix_rows = [widgets.HBox(hdr, layout=L(border_bottom='2px solid #343a40', padding='8px 0'))]
        
        asset_key = 'assets_monthly' if self.period == 'monthly' else 'assets_annually'
        asset_status = self.state.get(asset_key, [])

        for yr in self.years:
            periods = [(yr, m) for m in range(12, 0, -1) if (yr*12+m) < (self.now.year*12+self.now.month)] if self.period == 'monthly' else [(yr, None)]
            for (y, mo) in periods:
                name = mosaic_name(y, mo, self.period)
                date_str = f'{y}-{mo:02d}' if mo else f'{y}'
                
                # GCS Row
                gcs_cells = [widgets.HTML(f'<b>{date_str}</b>', layout=L(width=self._DATE_W)),
                             widgets.HTML('<span style="font-size:11px;color:#6c757d">GCS</span>', layout=L(width=self._TYPE_W)),
                             self._make_row_sel_btn(name, 'gcs')]
                for b in self.bands:
                    exists = b in self.gcs_chunks.get(name, [])
                    gcs_cells.append(self._create_matrix_cell(name, y, mo, self.period, f'gcs_{b}', exists, any(name in tn for tn in active_tasks if b in tn or "all" in tn)))
                matrix_rows.append(widgets.HBox(gcs_cells, layout=L(align_items='center', margin='2px 0')))
                
                # ASSET Row
                asset_cells = [widgets.HTML('', layout=L(width=self._DATE_W)),
                               widgets.HTML('<span style="font-size:11px;color:#6c757d">ASSET</span>', layout=L(width=self._TYPE_W)),
                               self._make_row_sel_btn(name, 'asset')]
                for b in self.bands:
                    exists = f"{name}_{b}" in asset_status or name in asset_status # Checagem dupla
                    asset_cells.append(self._create_matrix_cell(name, y, mo, self.period, f'asset_{b}', exists, any(name in tn for tn in active_tasks if b in tn or "all" in tn)))
                matrix_rows.append(widgets.HBox(asset_cells, layout=L(align_items='center', margin='2px 0')))
                
                matrix_rows.append(widgets.HTML('<div style="border-bottom:1px solid #dee2e6;margin:5px 0"></div>'))

        matrix = widgets.VBox(matrix_rows, layout=L(border='1px solid #dee2e6', padding='10px'))
        
        # Usar a area principal do componente base
        self.clear_main()
        self.main_area.children = [css, toolbar, matrix]

    def _create_matrix_cell(self, name, y, m, period, type_str, exists, is_active):
        chk = widgets.Checkbox(value=False, indent=False, layout=widgets.Layout(width='18px', height='18px', margin='0'))
        chk._meta = {'year': y, 'month': m, 'period': period, 'name': name, 'type': type_str, 'exists': exists}
        
        if exists:
            status, css_cls = 'OK', 'mfm-ok'
            if not is_edit_mode(): chk.disabled = True
        elif is_active: 
            status, css_cls = 'RUN', 'mfm-run'
            chk.disabled = True
        else: 
            status, css_cls = '[miss]', 'mfm-null'
        
        cell = PipelineStepUI.make_status_cell(chk, status, css_cls, width=self._CELL_W)
        self.chk_dict[f"{name}_{type_str}"] = chk
        return cell

    def _make_row_sel_btn(self, name, row_type):
        btn = widgets.Button(description='[S]', layout=widgets.Layout(width=self._SEL_W, height='28px', padding='0'))
        btn._row_name, btn._row_type = name, row_type
        btn.on_click(self._on_select_row)
        return btn

    def _refresh_cache(self):
        self.state = CacheManager.build_full_cache(logger=self.log, years=self.years)
        self.gcs_chunks = self.state.get('gcs_chunks', {})
        self._build_ui()

    def get_selected(self): return [chk._meta for chk in self.chk_dict.values() if chk.value and (is_edit_mode() or not chk._meta.get('exists'))]

def run_ui(years=None):
    ui = ExportDispatcherUI(years=years)
    ui.display() # Chamada explicita de display fora do __init__ costuma ser mais estavel
    return ui

def start_export(ui_obj):
    import time
    from datetime import timedelta
    if ui_obj is None: return
    selected = ui_obj.get_selected()
    if not selected: return
    
    total_tasks = len(selected)
    geom = config_module.get_country_geometry()
    ui_obj.log(f"Despachando {total_tasks} tarefas para o Google Earth Engine...", "info")
    
    start_time = time.time()
    
    for i, item in enumerate(selected):
        current_idx = i + 1
        y, m, p, name = item['year'], item['month'], item['period'], item['name']
        t_start = ee.Date(f'{y}-{m:02d}-01') if p == 'monthly' else ee.Date(f'{y}-01-01')
        t_end = t_start.advance(1, 'month') if p == 'monthly' else ee.Date(f'{y+1}-01-01')
        
        # Log de progresso e ETA
        eta_str = ""
        if i > 0:
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (total_tasks - i) * avg_time
            eta_str = f" | ⏳ ETA: ~{str(timedelta(seconds=int(remaining)))}"
        
        ui_obj.log(f"[{current_idx}/{total_tasks}] Despachando {name} ({item['type']}){eta_str}", "info")
        
        mosaic = get_quality_mosaic(ui_obj.sensor, y, t_start, t_end, geom, month=m if p == 'monthly' else None)
        if item['type'].startswith('asset_'):
            band = item['type'].split('_', 1)[1]
            export_to_asset(mosaic.select(band), f"{name}_{band}", y, m, p, config=config_module, band=band)
        elif item['type'].startswith('gcs_'):
            band = item['type'].split('_', 1)[1]
            export_to_gcs(mosaic, name, y, m, p, bands=[band], config_module=config_module)
            
    ui_obj.log(f"Sucesso: {total_tasks} tarefas enviadas à fila do GEE.", "success")
