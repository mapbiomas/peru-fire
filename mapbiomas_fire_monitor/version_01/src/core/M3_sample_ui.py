"""
M3 - Gateway for the GEE Sample Collection Toolkit
"""

def show_toolkit_links():
    """
    Simplified function for the M3 stage.
    Sample collection has been migrated to be carried out exclusively through the GEE JavaScript Toolkit.
    """
    github_link = "https://github.com/mapbiomas/peru-fire/blob/main/mapbiomas_fire_monitor/version_01/src/core/M3_toolkit.js"
    gee_link = "https://code.earthengine.google.com/?scriptPath=users%2Fmapbiomasworkspace1%2Fmapbiomas-fire%3A5-Monitor-Fuego%2FToolkit_Monitor_Fuego"
    doc_link = "https://github.com/mapbiomas/peru-fire/blob/main/mapbiomas_fire_monitor/version_01/FIRE_MONITOR_STANDARDS.md"

    print("\n" + "="*70)
    print("   M3 - SAMPLE COLLECTION (GEE TOOLKIT GATEWAY)")
    print("="*70)
    print("\n  The sample collection stage is carried out exclusively")
    print("  through the JavaScript interface in Google Earth Engine.\n")
    print("   1.1. Source code access (GitHub):")
    print(f"     {github_link}\n")
    print("   1.2. Direct access (GEE Editor):")
    print(f"     {gee_link}\n")
    print("   2. Documentation and usage standards:")
    print(f"     {doc_link}")
    print("\n" + "="*70 + "\n")
    return True

# Maintain compatibility with legacy notebooks
def run_collection_toolkit():
    return show_toolkit_links()

def start_sample_extraction(ui_toolkit=None):
    pass
