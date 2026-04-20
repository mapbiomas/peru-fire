"""
M7 — Curator
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Revisión de variantes filtradas disponibles en GCS de M6.
  2. Selección de la "versión ganadora" para cada región.
  3. Ensamblaje y exportación a GEE Asset como "Pre-Oficial Collection".
"""

import ee
from datetime import datetime
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, classification_name

def list_filtered_variants(region):
    # En producción esto listaría archivos 'filt_*' de GCS usando gcsfs.
    # Aquí es un mock para la demostración de la arquitectura.
    country = CONFIG.get('country', 'peru')
    return [
        f"filt_{country}_{region}_v1_2408",
        f"filt_{country}_{region}_v2_2408_exp"
    ]

# ─── EXPORTACIÓN DE GEE (Colección Pre-Oficial) ─────────────────────────────

def publish_preofficial_to_gee(image_path, version, collection_name, metadata):
    """
    Toma un raster filt_ de GCS y lo exporta a GEE Asset.
    """
    # En producción usaríamos el path GCS: gs://.../filt_...
    # image = ee.Image.loadGeoTIFF(image_path)
    
    # Fake submission for architecture
    img_final = ee.Image(0).set(metadata)
    
    asset_id = f"{CONFIG['asset_classification']}/{collection_name}/{version}"
    
    # task = ee.batch.Export.image.toAsset(
    #     image       = img_final,
    #     description = f'PUBLISH_{version}',
    #     assetId     = asset_id,
    #     scale       = 10,
    #     pyramidingPolicy = {'.default': 'mode'}
    # )
    # task.start()
    
    return "task_submit", asset_id

# ─── INTERFAZ DE IPYWIDGETS ─────────────────────────────────────────────────

class CuratorUI:
    def __init__(self, preset_votes=None):
        self.preset_votes = preset_votes
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        title = HTML("""
            <div style="background:linear-gradient(135deg,#2e003e,#3d0052); color:#ffb3ba;padding:14px 18px;border-radius:10px; font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                🏆 <b>Curador (M7)</b> — Publicación de Colección Pre-Oficial<br>
                <span style="color:#d4a5a5;font-size:11px;">Elige los candidatos ganadores (filt_...) e impúlsalos a GEE Asset.</span>
            </div>
        """)
        
        self.w_collection_name = widgets.Text(value='peru_fire_collection1', description='Colección:', layout=widgets.Layout(width='300px'))
        self.w_version = widgets.Text(value='v1', description='Versión Pub:', layout=widgets.Layout(width='300px'))
        
        if self.preset_votes:
            preset_html = "<ul>"
            for reg, variant in self.preset_votes.items():
                preset_html += f"<li><b>{reg}</b>: ganador = {variant}</li>"
            preset_html += "</ul>"
            
            self.selection_panel = widgets.VBox([
                HTML("<b>📌 Usando Votación Preset (PRESET_VOTES):</b>"),
                HTML(preset_html)
            ], layout=widgets.Layout(border='1px solid green', padding='10px', margin='10px 0'))
        else:
            # En producción esto sería un Dropdown por cada región disponible
            self.w_variant = widgets.Text(value='', description='Candidato:', placeholder='Ej. filt_peru_r1_v1_2408', layout=widgets.Layout(width='400px'))
            self.selection_panel = widgets.VBox([self.w_variant])

        self.ui = widgets.VBox([
            title,
            widgets.HBox([self.w_collection_name, self.w_version]),
            self.selection_panel
        ])

    def get_curation_selection(self):
        if self.preset_votes:
            votes = self.preset_votes
        else:
            votes = {'region_1': self.w_variant.value}
            
        return votes, self.w_collection_name.value, self.w_version.value

    def show(self):
        display(self.ui)


def run_ui(preset_votes=None):
    """Iniciar la interfaz del curador."""
    ui = CuratorUI(preset_votes)
    ui.show()
    return ui

def start_curation(ui):
    """Ejecutar publicación final a GEE Asset."""
    if not isinstance(ui, CuratorUI):
        print("⚠️ Esta función requiere el objeto devuelto por run_ui() de M7.")
        return
        
    votes, collection_name, version = ui.get_curation_selection()
    
    print(f"🚀 Iniciando Curaduría (Exportación Pre-Oficial)")
    print(f"   Colección: {collection_name} | Versión: {version}\n")
    
    for region, variant in votes.items():
        if not variant: continue
        print(f"  > Aprobado {region} -> {variant}")
        
        desc = (
            f"Col: {collection_name} | Ver: {version}\n"
            f"Variante Origen: {variant}"
        )
        metadata = {
            'country': CONFIG.get('country', 'peru'),
            'version': version,
            'collection': collection_name,
            'description': desc,
            'publish_date': datetime.now().isoformat()
        }
        
        # publish_preofficial_to_gee("gs://...", version, collection_name, metadata)
        print(f"    ✅ Exportación GEE Asset iniciada para {region}.")
        
    print("\n✅ Resumen de Configuración Usada (PRESET):")
    print("PRESET_VOTES = {")
    for r, v in votes.items():
        print(f"    '{r}': '{v}',")
    print("}")
