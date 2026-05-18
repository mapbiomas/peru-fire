"""
Componentes de UI Base (Ipywidgets)
MapBiomas Fire Monitor Pipeline - ASCII Version
"""
import ipywidgets as widgets
from IPython.display import display, clear_output
from M_lang import L

class PipelineStepUI:
    """
    Componente base para englobar visualmente as etapas do pipeline.
    """
    
    def __init__(self, title, description=""):
        self.title = title
        self.description = description
        
        # Loader CSS
        self.loader_html = widgets.HTML(
            value=f'''
            <div id="mfm-loader" style="display:none; align-items:center; margin-left:15px;">
                <div class="spinner"></div>
                <span style="margin-left:8px; font-size:11px; color:#666;">{L.PROCESSING}</span>
            </div>
            <style>
            .spinner {{
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3498db;
                border-radius: 50%;
                width: 16px;
                height: 16px;
                animation: mfm-spin 1s linear infinite;
                display: inline-block;
                vertical-align: middle;
            }}
            @keyframes mfm-spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            </style>
            '''
        )
        
        self.header_title = widgets.HTML(
            value=f"<h3 style='margin-bottom:0; display:inline-block;'>{self.title}</h3>",
            layout=widgets.Layout(margin='0')
        )
        
        self.header_box = widgets.HBox([self.header_title, self.loader_html], layout=widgets.Layout(align_items='center'))
        
        self.header_desc = widgets.HTML(
            value=f"<p style='color:#666; margin-top:5px;'>{self.description}</p>"
        )
        
        self.main_area = widgets.VBox()
        self.log_output = widgets.Output() 
        
        self.container = widgets.VBox([
            self.header_box,
            self.header_desc,
            self.main_area,
            self.log_output
        ], layout=widgets.Layout(
            border='1px solid #ccc',
            padding='10px',
            border_radius='5px',
            margin='10px 0'
        ))
        
    def display(self):
        """Renderiza o componente no notebook."""
        display(self.container)
        
    def show_loader(self, message=None):
        """Mostra o spinner de carregamento."""
        if message is None:
            message = L.PROCESSING
        self.loader_html.value = self.loader_html.value.replace('display:none', 'display:flex')
        if message:
            import re
            self.loader_html.value = re.sub(r'<span.*?>.*?</span>', f'<span style="margin-left:8px; font-size:11px; color:#666;">{message}</span>', self.loader_html.value)

    def hide_loader(self):
        """Esconde o spinner de carregamento."""
        self.loader_html.value = self.loader_html.value.replace('display:flex', 'display:none')

    def update_status(self, message, type=None):
        """Atualiza a mensagem de status secundária no próprio loader."""
        if not message:
            self.hide_loader()
            return
            
        # Garante que o loader está visível
        if 'display:none' in self.loader_html.value:
            self.show_loader(message)
        else:
            # Apenas troca o texto
            import re
            self.loader_html.value = re.sub(r'<span.*?>.*?</span>', f'<span style="margin-left:8px; font-size:11px; color:#666;">{message}</span>', self.loader_html.value)

    def log(self, message, type="info"):
        """Adiciona uma mensagem textualmente formatada no Output de Logs."""
        color = "black"
        if type == "error": color = "red"
        elif type == "success": color = "green"
        elif type == "warning": color = "orange"
        
        with self.log_output:
            display(widgets.HTML(f"<span style='color:{color}'>[{type.upper()}] {message}</span>"))
            
    def clear_logs(self):
        """Limpa apenas o terminal de logs do componente."""
        self.log_output.clear_output()
        
    def clear_main(self):
        """Limpa apenas a area primaria de renderizacao de controles."""
        self.main_area.children = []

    @staticmethod
    def get_status_css():
        """Retorna o CSS padrao para as celulas de status da matriz."""
        return widgets.HTML('''<style>
            .mfm-ok   { background:#d4edda !important; border:1px solid #c3e6cb !important; }
            .mfm-run  { background:#fff3cd !important; border:1px solid #ffeaa8 !important; }
            .mfm-null { background:#f8f9fa !important; border:1px solid #dee2e6 !important; }
            .mfm-hdr  { font-size:11px; font-weight:700; color:#495057; text-align:center; }
        </style>''')

    @staticmethod
    def make_status_cell(chk, status_text, css_class, width='80px'):
        """Cria um HBox formatado para representar uma celula de status."""
        status_html = widgets.HTML(
            f'<span style="font-size:10px;font-weight:700;color:#155724">{status_text}</span>' 
            if css_class == 'mfm-ok' else
            f'<span style="font-size:10px;font-weight:700;color:#856404">{status_text}</span>'
            if css_class == 'mfm-run' else
            f'<span style="font-size:10px;color:#adb5bd">{status_text}</span>',
            layout=widgets.Layout(width='32px')
        )
        
        cell = widgets.HBox(
            [chk, status_html], 
            layout=widgets.Layout(
                width=width, 
                min_height='34px', 
                justify_content='center', 
                align_items='center', 
                padding='0', 
                overflow='hidden', 
                margin='1px'
            )
        )
        cell.add_class(css_class)
        return cell


# ---------------------------------------------------------------------------
# Helpers de confirmacao inline e spinner
# ---------------------------------------------------------------------------

_SPINNER_STYLE = """
<style>
.mfm-loader-mini {
    border: 2px solid #f3f3f3;
    border-top: 2px solid #3498db;
    border-radius: 50%;
    width: 14px;
    height: 14px;
    animation: mfm-spin 0.8s linear infinite;
    display: inline-block;
    vertical-align: middle;
}
@keyframes mfm-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>"""


def make_spinner(msg=None):
    """Retorna um widget HTML com spinner animado e mensagem."""
    if msg is None:
        msg = L.LOADING
    return widgets.HTML(f"""
        <div style="display: flex; align-items: center; gap: 8px;">
            <div class="mfm-loader-mini"></div>
            <span style="color: #666; font-size: 11px; font-weight: bold;">{msg}</span>
        </div>
        {_SPINNER_STYLE}
    """)


def inline_confirm(btn, on_confirm, on_cancel=None):
    """Substitui o botao *btn* por [ Voltar ] [ OK ] no mesmo lugar.
    
    Parametros
    ----------
    btn : widgets.Button
        Botao a ser substituido. Deve estar inserido em um container
        (VBox / HBox) que jah tenha sido exibido.
    on_confirm : callable
        Executada quando o usuario clica OK (sem argumentos).
    on_cancel : callable, opcional
        Executada quando o usuario clica Voltar.
    """
    parent = btn.parent
    if parent is None:
        return
    children = list(parent.children)
    try:
        idx = children.index(btn)
    except ValueError:
        return

    btn_voltar = widgets.Button(
        description=L.BACK,
        button_style='',
        layout=widgets.Layout(width='70px', height='26px', padding='0', font_size='11px'))
    btn_ok = widgets.Button(
        description=L.OK,
        button_style='danger',
        layout=widgets.Layout(width='50px', height='26px', padding='0', font_size='11px'))

    confirm_box = widgets.HBox([btn_voltar, btn_ok],
                                layout=widgets.Layout(align_items='center', gap='3px'))

    spinner = make_spinner(msg=L.DELETING)

    def _restore(_):
        if on_cancel:
            on_cancel()
        parent.children = tuple(children[:idx] + [btn] + children[idx + 1:])

    def _do_confirm(_):
        parent.children = tuple(children[:idx] + [spinner] + children[idx + 1:])
        on_confirm()

    btn_voltar.on_click(_restore)
    btn_ok.on_click(_do_confirm)
    parent.children = tuple(children[:idx] + [confirm_box] + children[idx + 1:])
