"""
M3 - Gateway para el GEE Toolkit de Recolección de Muestras
"""

def show_toolkit_links():
    """
    Función simplificada para la etapa M3.
    La recolección de muestras se ha migrado para realizarse exclusivamente a través del GEE JavaScript Toolkit.
    """
    github_link = "https://github.com/mapbiomas/peru-fire/blob/main/mapbiomas_fire_monitor/version_01/src/core/M3_toolkit.js"
    gee_link = "https://code.earthengine.google.com/?scriptPath=users%2Fmapbiomasworkspace1%2Fmapbiomas-fire%3A5-Monitor-Fuego%2FToolkit_Monitor_Fuego"
    doc_link = "https://github.com/mapbiomas/peru-fire/blob/main/mapbiomas_fire_monitor/version_01/FIRE_MONITOR_STANDARDS.md"
    
    print("\n" + "="*70)
    print(" 🖍️  M3 - COLECTA DE MUESTRAS (GEE TOOLKIT GATEWAY)")
    print("="*70)
    print("\n  La etapa de recolección de muestras se lleva a cabo exclusivamente")
    print("  a través de la interfaz de JavaScript en Google Earth Engine.\n")
    print("  🔗 1.1. Acceso al código fuente (GitHub):")
    print(f"     {github_link}\n")
    print("  🔗 1.2. Acceso directo (Editor GEE):")
    print(f"     {gee_link}\n")
    print("  🔗 2. Documentación y normas de uso:")
    print(f"     {doc_link}")
    print("\n" + "="*70 + "\n")
    return True

# Mantemos compatibilidade com notebooks antigos
def run_collection_toolkit():
    return show_toolkit_links()

def start_sample_extraction(ui_toolkit=None):
    pass
