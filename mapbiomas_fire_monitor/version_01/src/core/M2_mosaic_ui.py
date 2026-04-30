print("\n>>> M2_mosaic_ui inicializando (v6.0 ASCII) <<<")
import traceback
import threading
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name, is_edit_mode
from M_cache import CacheManager
from M_ui_components import PipelineStepUI
from M2_mosaic_logic import assemble_country_mosaic, delete_cogs

class MosaicAssemblerUI(PipelineStepUI):
    def __init__(self, years=None):
        super().__init__(
            title="M2 - Montador de Mosaicos", 
            description="Agrupa fragmentos GCS e constroi o Cloud Optimized GeoTIFF (COG)."
        )
        self.chk_dict = {}
        self.requested_years = years
        self.is_refreshing = False
        
        try:
            print("M2: [1/3] Iniciando dados do GCS...")
            self._init_data()
            print("M2: [2/3] Construindo interface...")
            self._build_ui()
            print("M2: [3/3] Renderizacao concluida.")
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
        self.log("Lendo fragmentos do cache GCS...", "info")
        self.state = CacheManager.load() or {}
        
        # gcs_chunks is a dict: {mosaic_name: [band1, band2, ...], ...}
        self.gcs_chunks = self.state.get('gcs_chunks', {})
        
        # cogs is a dict or list? Let's check typical usage.
        # It should represent which cogs exist. Let's assume a structure similar to gcs_chunks:
        # {mosaic_name: [band1, band2...]}
        # Or a list of strings like M1 uses for assets.
        self.cogs = self.state.get('cogs_monthly' if self.period == 'monthly' else 'cogs_annually', [])

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
        name = btn._row_name
        prefix = f"{name}_cog_"
        
        # Filtrar checkboxes desta linha que podem ser clicados (não desabilitados)
        row_chks = [chk for key, chk in self.chk_dict.items() if key.startswith(prefix) and not chk.disabled]
        if not row_chks: return
        
        # Toggle: Se algum estiver ligado, desliga todos. Se todos desligados, liga todos.
        any_on = any(chk.value for chk in row_chks)
        target_val = not any_on
        
        for chk in row_chks:
            chk.value = target_val

    def _build_ui(self):
        # Evitar reconstruir se já houver itens marcados (proteção contra race condition do refresh)
        if self.chk_dict and any(c.value for c in self.chk_dict.values()):
            return 
            
        self.chk_dict = {} # Limpar referencias antigas
        css = PipelineStepUI.get_status_css()

        self.btn_all = widgets.Button(description="Selecionar Todos", button_style='info', layout=widgets.Layout(width='155px'))
        self.btn_none = widgets.Button(description="Limpar Selecao", button_style='info', layout=widgets.Layout(width='145px'))
        self.btn_refresh = widgets.Button(description="Atualizar GCS", button_style='success', layout=widgets.Layout(width='150px'))
        self.btn_all.on_click(self._on_select_all)
        self.btn_none.on_click(self._on_select_none)
        self.btn_refresh.on_click(lambda _: self._refresh_cache())
        
        btns = [self.btn_all, self.btn_none, self.btn_refresh]
        
        if is_edit_mode():
            self.btn_delete = widgets.Button(description="Eliminar Seleção", button_style='danger', icon='trash', layout=widgets.Layout(width='160px'))
            self.btn_delete.on_click(self._on_delete_selection)
            btns.append(self.btn_delete)
            
        toolbar = widgets.HBox(btns, layout=widgets.Layout(margin='0 0 10px 0'))

        L = widgets.Layout
        hdr = [widgets.HTML('<span class="mfm-hdr">Data</span>', layout=L(width=self._DATE_W)), 
               widgets.HTML('<span class="mfm-hdr">Tipo</span>', layout=L(width=self._TYPE_W)), 
               widgets.HTML('<span class="mfm-hdr">[S]</span>', layout=L(width=self._SEL_W, text_align='center'))]
        for b in self.bands: hdr.append(widgets.HTML(f'<span class="mfm-hdr">{b}</span>', layout=L(width=self._CELL_W, text_align='center')))
        
        matrix_rows = [widgets.HBox(hdr, layout=L(border_bottom='2px solid #343a40', padding='8px 0'))]
        
        for yr in self.years:
            periods = [(yr, m) for m in range(12, 0, -1) if (yr*12+m) < (self.now.year*12+self.now.month)] if self.period == 'monthly' else [(yr, None)]
            for (y, mo) in periods:
                name = mosaic_name(y, mo, self.period)
                date_str = f'{y}-{mo:02d}' if mo else f'{y}'
                
                # Check what chunks we have ready
                ready_chunks = self.gcs_chunks.get(name, [])
                
                # Check what COGs we have ready
                has_any_cog = name in self.cogs or any(f"{name}_{b}" in self.cogs for b in self.bands)
                
                # >>> FILTER: Show if has input chunks (ready to start) OR has existing COGs (completed/in-progress) <<<
                if not ready_chunks and not has_any_cog:
                    continue  

                cells = [
                    widgets.HTML(f'<b>{date_str}</b>', layout=L(width=self._DATE_W)),
                    widgets.HTML('<span style="font-size:11px;color:#6c757d">COG</span>', layout=L(width=self._TYPE_W)),
                    self._make_row_sel_btn(name)
                ]
                
                for b in self.bands:
                    # Do we have the COG ready in GCS?
                    has_cog = f"{name}_{b}" in self.cogs or name in self.cogs
                    has_chunk = b in ready_chunks
                    cells.append(self._create_matrix_cell(name, y, mo, self.period, b, has_cog, has_chunk))
                    
                matrix_rows.append(widgets.HBox(cells, layout=L(align_items='center', margin='2px 0')))
                matrix_rows.append(widgets.HTML('<div style="border-bottom:1px solid #dee2e6;margin:5px 0"></div>'))

        matrix = widgets.VBox(matrix_rows, layout=L(border='1px solid #dee2e6', padding='10px'))
        
        # Usar a area principal do componente base
        self.clear_main()
        self.main_area.children = [css, toolbar, matrix]

    def _create_matrix_cell(self, name, y, m, period, band, has_cog, has_chunk):
        chk = widgets.Checkbox(value=False, indent=False, layout=widgets.Layout(width='18px', height='18px', margin='0'))
        chk._meta = {'year': y, 'month': m, 'period': period, 'name': name, 'band': band, 'exists': has_cog}
        
        if has_cog:
            status, css_cls = 'OK', 'mfm-ok'
            if not is_edit_mode(): chk.disabled = True
        elif not has_chunk:
            status, css_cls = '[miss]', 'mfm-null'
            chk.disabled = True # Cannot assemble if chunk is missing!
        else:
            status, css_cls = '[miss]', 'mfm-run'
            
        cell = PipelineStepUI.make_status_cell(chk, status, css_cls, width=self._CELL_W)
        self.chk_dict[f"{name}_cog_{band}"] = chk
        return cell

    def _make_row_sel_btn(self, name):
        btn = widgets.Button(description='[S]', layout=widgets.Layout(width=self._SEL_W, height='28px', padding='0'))
        btn._row_name = name
        btn.on_click(self._on_select_row)
        return btn

    def _refresh_cache(self):
        if self.is_refreshing: return
        
        try:
            self.is_refreshing = True
            self.btn_refresh.disabled = True
            self.btn_refresh.description = "Atualizando..."
            
            self.state = CacheManager.build_full_cache(logger=self.log, years=self.years)
            self.gcs_chunks = self.state.get('gcs_chunks', {})
            self.cogs = self.state.get('cogs_monthly' if self.period == 'monthly' else 'cogs_annually', [])
            self._build_ui()
            
        except Exception as e:
            self.log(f"Erro ao atualizar GCS: {e}", "error")
        finally:
            self.is_refreshing = False
            self.btn_refresh.disabled = False
            self.btn_refresh.description = "Atualizar GCS"

    def get_selected(self): 
        return [chk._meta for chk in self.chk_dict.values() if chk.value]

    def _on_delete_selection(self, _):
        self.log("Iniciando remoção de COGs selecionados...", "warning")
        start_delete(self)
        self._refresh_cache()

def run_ui(years=None):
    ui = MosaicAssemblerUI(years=years)
    ui.display() 
    
    # Auto-refresh em background para simular o clique no botão e atualizar o cache
    threading.Thread(target=ui._refresh_cache, daemon=True).start()
    
    return ui

def start_assemble(ui_obj):
    """Lida com a estrutura retornada pela matrix."""
    import time
    if ui_obj is None:
        print("❌ Erro: Objeto UI não inicializado. Execute a célula anterior.")
        return
        
    selected = ui_obj.get_selected()
    if not selected:
        msg = "⚠️ Nenhum mosaico/banda selecionado. Marque as caixas [miss] amarelas na interface."
        print(msg)
        ui_obj.log(msg, "warning")
        return
    
    # Agrupar as bandas selecionadas por Mês/Ano
    by_key = {}
    total_tasks = 0
    for item in selected:
        k = (item['year'], item['month'], item['period'])
        if k not in by_key: by_key[k] = []
        by_key[k].append(item['band'])
        total_tasks += 1
    
    ui_obj.log(f"Iniciando montagem de {total_tasks} COGs em {len(by_key)} períodos...", "info")
    
    start_time = time.time()
    completed_tasks = 0
    
    for (y, m, p), str_bands in by_key.items():
        # A lógica interna do assemble_country_mosaic agora lida com o contador por banda
        results = assemble_country_mosaic(
            year=y, month=m, period=p, bands=str_bands, 
            logger=ui_obj.log, 
            progress_idx=completed_tasks, 
            progress_total=total_tasks,
            start_time=start_time
        )
        completed_tasks += len(str_bands)
    
    ui_obj.log(f"Processamento de lote finalizado. Total: {total_tasks} COGs.", "success")

def start_delete(ui_obj):
    """Executa a deleção para os itens selecionados."""
    if ui_obj is None: return
    selected = ui_obj.get_selected()
    if not selected: return
    
    by_key = {}
    for item in selected:
        k = (item['year'], item['month'], item['period'])
        if k not in by_key: by_key[k] = []
        by_key[k].append(item['band'])
    
    for (y, m, p), str_bands in by_key.items():
        ui_obj.log(f"Deletando COGs de {y}-{m or ''} nas bandas: {str_bands}", "warning")
        delete_cogs(year=y, month=m, period=p, bands=str_bands, logger=ui_obj.log)
