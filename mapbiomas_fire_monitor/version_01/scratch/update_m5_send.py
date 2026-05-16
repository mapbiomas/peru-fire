import os
import re

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M5_classifier.py'
with open(path, 'r', encoding='utf-8') as f:
    txt = f.read()

old_func_def = """def run_m5_queue():
    \"\"\"
    Motor de Processamento (Fase 1: Classificacao, Fase 2: Upload GEE)
    \"\"\"
    from M5_classifier_ui import load_queue, save_queue
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets
    
    out = widgets.Output()
    display(out)
    
    queue = load_queue()"""

new_func_def = """def run_m5_queue(send=None):
    \"\"\"
    Motor de Processamento (Fase 1: Classificacao, Fase 2: Upload GEE)
    \"\"\"
    if send is None:
        send = ['classification', 'upload']
        
    from M5_classifier_ui import load_queue, save_queue
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets
    
    out = widgets.Output()
    display(out)
    
    valid_commands = ['classification', 'upload']
    if not isinstance(send, list) or not any(s in valid_commands for s in send):
        with out:
            print("Atencion: Argumento 'send' invalido. Use send=['classification'], send=['upload'] o send=['classification', 'upload'].")
        return
        
    queue = load_queue()"""

if old_func_def in txt:
    txt = txt.replace(old_func_def, new_func_def)
    
# Adjust IF statements to respect 'send' parameter
txt = txt.replace("if pending_jobs:", "if pending_jobs and 'classification' in send:")
txt = txt.replace("if upload_jobs:", "if upload_jobs and 'upload' in send:")

with open(path, 'w', encoding='utf-8') as f:
    f.write(txt)
print("Filtros de execução (send) adicionados!")
