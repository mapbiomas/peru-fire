"""
M3.3 — Gestor de Muestras (UI)
MapBiomas Fuego Sentinel Monitor — Piloto Perú
"""
import ipywidgets as widgets
from IPython.display import display, clear_output
from M3_sample_logic import list_sample_collections, ALL_BANDS, load_sample_fc, export_samples_to_gcs

# ─── INTERFACES DE IPYWIDGETS ───────────────────────────────────────────────────


class CollectionToolkitUI:
    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        title = HTML("""
            <div style="background:linear-gradient(135deg,#0d1b2a,#1b263b); color:#e0fbfc;padding:14px 18px;border-radius:10px; font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                🎨 <b>Toolkit de Recolección de Muestras</b><br>
                <span style="color:#8892b0;font-size:11px;">Visualiza mosaicos y envía polígonos al Bucket/Asset</span>
            </div>
        """)
        
        collections = list_sample_collections()
        self.w_collections = widgets.SelectMultiple(
            options=collections or ['(no se han encontrado activos)'],
            description='Assets de Base:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='480px')
        )
        self.w_output_name = widgets.Text(
            value='nueva_coleccion',
            description='Nombre Salida:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='480px')
        )
        self.w_sensor = widgets.SelectMultiple(
            options=['sentinel2', 'landsat'],
            value=['sentinel2'],
            description='Sensor Ref:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='480px')
        )
        self.ui = widgets.VBox([title, self.w_collections, self.w_sensor, self.w_output_name])

    def get_collection_name(self):
        return self.w_output_name.value
        
    def get_sensor_ref(self):
        return list(self.w_sensor.value)

    def show(self):
        display(self.ui)


class SampleGroupUI:
    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        title = HTML("""
            <div style="background:linear-gradient(135deg,#0d1b2a,#1b263b); color:#e0fbfc;padding:14px 18px;border-radius:10px; font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                📦 <b>Gestor y Agrupador de Muestras</b><br>
                <span style="color:#8892b0;font-size:11px;">Fusiona colecciones pasadas y prepáralas para el modelo</span>
            </div>
        """)
        
        collections = list_sample_collections()
        self.w_collections = widgets.SelectMultiple(
            options=collections or ['(nada encontrado)'],
            description='Colecciones:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='480px', height='150px')
        )
        
        band_items = []
        for band, info in ALL_BANDS.items():
            chk = widgets.Checkbox(value=info['default'], description=f"{band} ({info['desc']})")
            band_items.append((band, chk))
        self.band_checkboxes = dict(band_items)
        
        band_box = widgets.VBox(
            [widgets.Label('📡 Bandas a extraer para entrenamiento:')] + [chk for _, chk in band_items],
            layout=widgets.Layout(border='1px solid #333', padding='8px', border_radius='6px')
        )
        
        self.ui = widgets.VBox([title, widgets.HBox([self.w_collections, band_box])])

    def get_selection(self):
        selected_cols = list(self.w_collections.value)
        selected_bands = [b for b, chk in self.band_checkboxes.items() if chk.value]
        return selected_cols, selected_bands

    def show(self):
        display(self.ui)


def run_collection_toolkit():
    """Iniciar la interfaz del Toolkit interactivo."""
    ui = CollectionToolkitUI()
    ui.show()
    return ui

def run_grouping_ui():
    """Iniciar la interfaz del Gestor de Agrupamiento."""
    ui = SampleGroupUI()
    ui.show()
    return ui

def start_sample_extraction(ui):
    """Ejecutar la extracción basada en la configuración de la UI de agrupamiento."""
    if not isinstance(ui, SampleGroupUI):
        print("⚠️ Esta función requiere el objeto devuelto por run_grouping_ui()")
        return
        
    collections, bands = ui.get_selection()
    
    if not collections:
        print("⚠️ No hay colecciones seleccionadas.")
        return
        
    if not bands:
        print("⚠️ Seleccione al menos una banda.")
        return
        
    print(f"🚀 Iniciando acopio temporal para {len(collections)} colecciones. Extrayendo las bandas: {bands}")
    
    for col_name in collections:
        print(f"  > Evaluando y extrayendo '{col_name}'...")
        fc = load_sample_fc(col_name)
        
        # En una versión madura, extraeríamos también version y region mediante UI.
        # Por ahora extraemos as-is para el nombre de la colección
        export_samples_to_gcs(fc, bands, 'v1', 'agrupado', col_name)
        
    print("✅ Disparo completado. Revisa tus Tasks en GEE.")
