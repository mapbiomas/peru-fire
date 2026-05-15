"""
Componentes de UI Base (Ipywidgets)
MapBiomas Fire Monitor Pipeline - ASCII Version
"""
import ipywidgets as widgets
from IPython.display import display, clear_output

class PipelineStepUI:
    """
    Componente base para englobar visualmente as etapas do pipeline.
    """
    
    def __init__(self, title, description=""):
        self.title = title
        self.description = description
        
        # Loader CSS
        self.loader_html = widgets.HTML(
            value='''
            <div id="mfm-loader" style="display:none; align-items:center; margin-left:15px;">
                <div class="spinner"></div>
                <span style="margin-left:8px; font-size:11px; color:#666;">Processando...</span>
            </div>
            <style>
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3498db;
                border-radius: 50%;
                width: 16px;
                height: 16px;
                animation: mfm-spin 1s linear infinite;
                display: inline-block;
                vertical-align: middle;
            }
            @keyframes mfm-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
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
        
    def show_loader(self, message="Processando..."):
        """Mostra o spinner de carregamento."""
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
