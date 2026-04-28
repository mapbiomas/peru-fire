"""
M3 - Gateway para o GEE Toolkit de Coleta de Amostras
"""

def show_toolkit_links():
    """
    Função simplificada para a etapa M3.
    A coleta de amostras foi migrada para ser exclusivamente via GEE JavaScript Toolkit.
    """
    github_link = "https://github.com/mapbiomas/mapbiomas-fire/tree/main/peru/src/gee/src/core/M3_toolkit.js"
    doc_link = "https://github.com/mapbiomas/mapbiomas-fire/blob/main/peru/FIRE_MONITOR_STANDARDS.md#mockup-ascii-m32-gee-toolkit-gateway"
    
    print("\n" + "="*70)
    print(" 🖍️  M3 - COLETA DE AMOSTRAS (GEE TOOLKIT GATEWAY)")
    print("="*70)
    print("\n  A etapa de coleta de amostras é realizada exclusivamente")
    print("  através da interface JavaScript no Google Earth Engine.\n")
    print("  🔗 1. Acesso Rápido ao Código-Fonte do Toolkit (GitHub):")
    print(f"     {github_link}\n")
    print("  🔗 2. Documentação e Padrões de Uso:")
    print(f"     {doc_link}")
    print("\n" + "="*70 + "\n")
    return True

# Mantemos compatibilidade com notebooks antigos
def run_collection_toolkit():
    return show_toolkit_links()

def start_sample_extraction(ui_toolkit=None):
    pass
