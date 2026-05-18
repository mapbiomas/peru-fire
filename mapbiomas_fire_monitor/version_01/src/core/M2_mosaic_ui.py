print("\n>>> M2_mosaic_ui initializing (v7.0 Tabs) <<<")
import ee
import traceback
import threading
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, GLOBAL_OPTS, mosaic_name, is_edit_mode
import M0_auth_config as config_module
from M_cache import CacheManager
from M_ui_components import PipelineStepUI
from M_lang import L as Lang
from M2_mosaic_logic import assemble_country_mosaic

class MosaicAssemblerUI(PipelineStepUI):
    def __init__(self, years=None):
        super().__init__(
            title="M2 - Montador de Mosaicos (COG)", 
            description="Interfaz para convertir chunks GCS en mosaicos COG nacionales."
        )
        self.chk_dict = {}
        self.requested_years = years
        self.btn_refresh = None
        self.is_refreshing = False
        # Persistência de abas
        self.last_tabs = (0, 0, 0)
        self.search_query = ""
        
        try:
            self.main_area.children = [widgets.HTML(f"<i>{Lang.LOADING_INTERFACE}</i>")]
        except Exception as e:
            print(f"CRITICAL ERROR IN M2 INTERFACE: {e}")
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
        self.state = CacheManager.load() or {}
        self.gcs_chunks = self.state.get('gcs_chunks', {})

    _CELL_W  = '80px'

    def _on_select_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = True

    def _on_select_none(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = False

    def _build_mosaic_grid(self, sensor, period, mosaic_method):
        L = widgets.Layout
        hdr = [
            widgets.HTML('<div style="width:100px;">Data</div>'),
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
        
        # Limite de data: até o mês passado
        last_month_year = self.now.year
        last_month = self.now.month - 1
        if last_month == 0:
            last_month = 12
            last_month_year -= 1

        for y in self.years:
            months = range(12, 0, -1) if period == 'monthly' else [None]
            for m in months:
                # Pula meses futuros
                if y > last_month_year: continue
                if y == last_month_year and m is not None and m > last_month: continue

                date_str = f"{y}_{m:02d}" if m else f"{y}"
                
                # Filtro de busca
                if self.search_query and self.search_query.lower() not in date_str.lower():
                    continue
                
                cells = [widgets.HTML(f'<div style="width:100px;font-family:monospace;">{date_str}</div>')]
                
                btn_s = widgets.Button(description='[S]', layout=L(width='40px', height='28px', padding='0'))
                btn_s._sensor, btn_s._period, btn_s._mosaic, btn_s._date = sensor, period, mosaic_method, date_str
                btn_s.on_click(self._on_select_row)
                cells.append(btn_s)

                for b in self.bands:
                    # Lógica de existência (COG) vs disponibilidade (Chunks)
                    # Sincronizado com CacheManager
                    m_name = mosaic_name(y, m, period, band=b, mosaic=mosaic_method, sensor=sensor)
                    
                    # 1. Verifica se o COG final existe
                    cogs_list = self.state.get('cogs_monthly' if period=='monthly' else 'cogs_annually', [])
                    exists_cog = m_name.lower() in [c.lower() for c in cogs_list]
                    
                    # 2. Verifica se existem chunks para montar
                    # No CacheManager, a chave dos chunks é o nome base sem a banda
                    m_base_name = mosaic_name(y, m, period, mosaic=mosaic_method, sensor=sensor)
                    has_chunks = b in self.state.get('gcs_chunks', {}).get(m_base_name, [])
                    
                    chk = widgets.Checkbox(value=False, indent=False, layout=L(width='18px', height='18px', margin='0'))
                    chk._meta = {'sensor': sensor, 'period': period, 'mosaic': mosaic_method, 'year': y, 'month': m, 'band': b}
                    
                    if exists_cog:
                        status, css = 'OK', 'mfm-ok'
                        if not is_edit_mode(): chk.disabled = True
                    elif has_chunks:
                        status, css = 'READY', 'mfm-run' 
                    else:
                        status, css = 'MISS', 'mfm-null'
                        chk.disabled = True
                    
                    cell = PipelineStepUI.make_status_cell(chk, status, css, width='auto')
                    cell.layout.flex = '1'
                    self.chk_dict[f"{sensor}_{period}_{mosaic_method}_{date_str}_{b}"] = chk
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

    def _on_select_row(self, btn):
        prefix = f"{btn._sensor}_{btn._period}_{btn._mosaic}_{btn._date}_"
        row_chks = [chk for key, chk in self.chk_dict.items() if key.startswith(prefix) and not chk.disabled]
        if not row_chks: return
        any_on = any(chk.value for chk in row_chks)
        target_val = not any_on
        for chk in row_chks: chk.value = target_val
    
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
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 5px 10px; background: #fff; border-bottom: 2px solid #333; margin-bottom: 5px;">
            <div style="display: flex; align-items: center; gap: 15px;">
                <span style="font-weight: bold; font-size: 16px; color: #333;">M2 - Montador</span>
                <span style="color: #888; font-size: 11px; font-style: italic;">Interfaz para montaje de mosaicos nacionales (COG)</span>
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
        
        # Loader integrado ao rodapé
        footer = widgets.VBox([
            widgets.HBox([btn_all, btn_none, self.btn_refresh, self.loader_html], layout=L(margin='15px 0', gap='10px', align_items='center'))
        ])

        # --- SISTEMA DE ABAS (TABS) ---
        sensors = ['SENTINEL2'] #, 'LANDSAT', 'HLS', 'MODIS']
        periods = ['monthly'] #, 'yearly']
        methods = CONFIG['mosaic_methods']
        
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
                    placeholder = widgets.VBox([widgets.HTML(f"<i>{Lang.CLICK_TO_LOAD.format(sensor=s, period=p, mosaic=m)}</i>")], layout=L(padding='20px'))
                    method_children.append(placeholder)
                    self.tab_map[(i, j, k)] = (s.lower(), p, m)
                
                method_tabs.children = method_children
                for k, m in enumerate(methods):
                    method_tabs.set_title(k, m.upper())
                
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

        # Restaurar abas anteriores
        s_idx, p_idx, m_idx = self.last_tabs
        self.sensor_tabs.selected_index = s_idx
        self.sensor_children[s_idx].selected_index = p_idx
        self.sensor_children[s_idx].children[p_idx].selected_index = m_idx
        
        # Gatilho inicial
        self._load_tab(s_idx, p_idx, m_idx)

        self.clear_main()
        self.main_area.children = [
            PipelineStepUI.get_status_css(), 
            widgets.HTML(header_html), 
            self.sensor_tabs, 
            footer
        ]

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

    def _load_tab(self, s_idx, p_idx, m_idx):
        sensor, period, method = self.tab_map[(s_idx, p_idx, m_idx)]
        p_tabs = self.sensor_children[s_idx]
        method_tabs = p_tabs.children[p_idx]
        
        target_container = method_tabs.children[m_idx]
        if not isinstance(target_container.children[0], widgets.HTML) or "<i>" not in target_container.children[0].value:
            return

        grid = self._build_mosaic_grid(sensor, period, method)
        
        new_children = list(method_tabs.children)
        new_children[m_idx] = grid
        method_tabs.children = new_children

    def _on_search_change(self, change):
        self.search_query = change['new']
        # Força recarregamento da aba atual com o filtro
        s_idx = self.sensor_tabs.selected_index
        p_idx = self.sensor_children[s_idx].selected_index
        m_idx = self.sensor_children[s_idx].children[p_idx].selected_index
        
        # Limpa o "cache" visual da aba para forçar rebuild
        target_container = self.sensor_children[s_idx].children[p_idx].children[m_idx]
        target_container.children = [widgets.HTML("<i>Filtrando...</i>")]
        self._load_tab(s_idx, p_idx, m_idx)

    def _refresh_cache(self):
        if self.is_refreshing: return
        try:
            self.is_refreshing = True
            # Salva abas atuais antes do rebuild
            s_idx = self.sensor_tabs.selected_index
            p_idx = self.sensor_children[s_idx].selected_index
            m_idx = self.sensor_children[s_idx].children[p_idx].selected_index
            self.last_tabs = (s_idx, p_idx, m_idx)
            
            self.show_loader("Sincronizando...")
            self.state = CacheManager.build_full_cache(logger=self.update_status, years=self.years)
            self._build_ui()
        finally:
            self.is_refreshing = False
            self.hide_loader()

def run_ui(years=None):
    ui = MosaicAssemblerUI(years=years)
    ui.display() 
    ui.show_loader(Lang.LOADING)
    ui._build_ui()
    ui.hide_loader()
    return ui

def start_mosaic_assembly(ui_obj):
    selected = [chk._meta for chk in ui_obj.chk_dict.values() if chk.value]
    if not selected:
        print("[WARNING] No mosaic selected.")
        return
    
    print(f"[INFO] Starting assembly of {len(selected)} COG bands...")
    
    from M2_mosaic_logic import assemble_country_mosaic
    
    try:
        for item in selected:
            d_label = f"{item['year']}_{item['month']:02d}" if item['month'] else f"{item['year']}"
            print(f"\n--- Processing: {item['sensor']} {d_label} {item['band']} ---")
            
            assemble_country_mosaic(
                year=item['year'],
                month=item['month'],
                period=item['period'],
                sensor=item['sensor'],
                mosaic_method=item['mosaic'],
                bands=[item['band']],
                logger=print
            )
        print("\n[SUCCESS] Assembly completed successfully!")
    except Exception as e:
        print(f"\n[ERROR] Error in assembly: {e}")
        traceback.print_exc()
