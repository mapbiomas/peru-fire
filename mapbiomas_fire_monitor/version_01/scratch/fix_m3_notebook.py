import json
import os

notebook_path = r"c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\notebooks\mapbiomas_fire_sentinel_peru.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Procura a célula que tem o M3_sample_ui ou M3_toolkit_ui
for cell in nb['cells']:
    if 'cell_type' in cell and cell['cell_type'] == 'code':
        source = "".join(cell.get('source', []))
        if "from M3_toolkit_ui import show_toolkit_links" in source:
            cell['source'] = ["from M3_sample_ui import show_toolkit_links\n", "show_toolkit_links()"]
            print("✅ Célula M3 atualizada no notebook.")

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
