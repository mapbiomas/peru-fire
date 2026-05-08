import os

notebook_path = r"c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\notebooks\mapbiomas_fire_sentinel_peru.ipynb"

if os.path.exists(notebook_path):
    with open(notebook_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substituição global de texto (funciona para células de código e markdown)
    new_content = content.replace("M3_toolkit_ui", "M3_sample_ui")
    
    with open(notebook_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ M3_toolkit_ui substituído por M3_sample_ui em todo o notebook.")
else:
    print("❌ Notebook não encontrado.")
