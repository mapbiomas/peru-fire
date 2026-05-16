import ast
import os

path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core\M4_model_trainer.py'
with open(path, 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

# Extrair Top level imports e constantes
imports = []
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign)):
        imports.append(ast.get_source_segment(source, node))
        
import_str = "\n".join(imports) + "\n\n"

# Injetar dependências cruzadas locais 
data_imports = import_str
hub_imports = import_str
algo_imports = import_str + "from M4_data_extractor import compute_normalizer, normalize\nfrom M4_hub_manager import list_trained_models\n"
analytics_imports = import_str
ui_imports = import_str + "from M4_data_extractor import extract_pixels_from_gcs, list_sample_collections_gcs\nfrom M4_algorithms_dnn import ModelTrainer\nfrom M4_analytics import view_analytics, render_diagnostic_dashboard\nfrom M4_hub_manager import list_trained_models, _load_m4_cache, _save_m4_cache\n"

def get_node_source(name):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            return ast.get_source_segment(source, node) + "\n\n"
    return ""

out_dir = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core'

# 1. M4_data_extractor
data_code = data_imports
data_code += get_node_source('list_sample_collections_gcs')
data_code += get_node_source('list_campaigns_gcs')
data_code += get_node_source('extract_pixels_from_gcs')
data_code += get_node_source('compute_normalizer')
data_code += get_node_source('normalize')
with open(os.path.join(out_dir, 'M4_data_extractor.py'), 'w', encoding='utf-8') as f: f.write(data_code)

# 2. M4_hub_manager
hub_code = hub_imports
hub_code += get_node_source('_load_m4_cache')
hub_code += get_node_source('_save_m4_cache')
hub_code += get_node_source('list_trained_models')
with open(os.path.join(out_dir, 'M4_hub_manager.py'), 'w', encoding='utf-8') as f: f.write(hub_code)

# 3. M4_algorithms_dnn
algo_code = algo_imports
algo_code += get_node_source('_get_tf')
algo_code += get_node_source('ModelTrainer')
with open(os.path.join(out_dir, 'M4_algorithms_dnn.py'), 'w', encoding='utf-8') as f: f.write(algo_code)

# 4. M4_analytics
analytics_code = analytics_imports
analytics_code += get_node_source('render_diagnostic_dashboard')
analytics_code += get_node_source('render_model_card_html')
analytics_code += get_node_source('view_analytics')
with open(os.path.join(out_dir, 'M4_analytics.py'), 'w', encoding='utf-8') as f: f.write(analytics_code)

# 5. M4_ui
ui_code = ui_imports
ui_code += get_node_source('ModelTrainerUI')
ui_code += get_node_source('start_training')
ui_code += get_node_source('run_ui')
with open(os.path.join(out_dir, 'M4_ui.py'), 'w', encoding='utf-8') as f: f.write(ui_code)

# 6. Facade for M4_model_trainer.py
facade = '"""\nFachada de compatibilidade para cadernos legados.\nOs modulos foram divididos em M4_data_extractor, M4_hub_manager, M4_algorithms_dnn, M4_analytics, M4_ui.\n"""\n\n'
facade += 'from M4_ui import run_ui, start_training, ModelTrainerUI\n'
facade += 'from M4_hub_manager import list_trained_models\n'
facade += 'from M4_data_extractor import extract_pixels_from_gcs, list_sample_collections_gcs\n'
facade += 'from M4_algorithms_dnn import ModelTrainer\n'

with open(path, 'w', encoding='utf-8') as f:
    f.write(facade)

print('Refatoração de M4 concluída!')
