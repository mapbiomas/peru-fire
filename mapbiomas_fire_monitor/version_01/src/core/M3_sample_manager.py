"""
M3 — Gestor de Muestras
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Consultar muestras vectoriales de GEE FeatureCollections
  2. Filtrar por versión, región, período, campaña
  3. Convertir muestras vectoriales → parches .tif mediante búsqueda en mosaico
  4. Interfaz de usuario para la selección de bandas (4 predeterminadas + blue/green/dayOfYear opcionales)
  5. Previsualización de la distribución de las muestras (equilibrio de clases)
  6. Exportar archivos de muestra .tif a GCS para el entrenamiento
"""

import ee
import os
import json
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, gcs_path, model_path

# ─── ESQUEMA DE MUESTRA ───────────────────────────────────────────────────────
# Propiedades esperadas en la FeatureCollection de GEE (exportadas por el Toolkit):
#   label      : int   — 0=no-quemado, 1=quemado
#   year       : int   — año de observación
#   month      : int   — mes (nulo si es anual)
#   period     : str   — 'mensual' | 'anual'
#   region     : str   — p. ej. 'peru_r1_amazonia'
#   version    : str   — versión de la colección de muestras, p. ej. 'v1'
#   campaign   : str   — id de la campaña de recolección, p. ej. '2024-01'
#   source     : str   — 'interpretacion_visual' | 'referencia_modis' | ...

SAMPLE_ASSET_ROOT = f"projects/{CONFIG['ee_project']}/assets/FIRE/SAMPLES"

# Todas las bandas de entrada del modelo posibles (almacenadas en el mosaico)
ALL_BANDS = {
    'red':       {'byte': True,  'default': True,  'desc': 'Rojo (S2 B4)'},
    'nir':       {'byte': True,  'default': True,  'desc': 'NIR (S2 B8)'},
    'swir1':     {'byte': True,  'default': True,  'desc': 'SWIR1 (S2 B11)'},
    'swir2':     {'byte': True,  'default': True,  'desc': 'SWIR2 (S2 B12)'},
    'blue':      {'byte': True,  'default': False, 'desc': 'Azul (S2 B2)'},
    'green':     {'byte': True,  'default': False, 'desc': 'Verde (S2 B3)'},
    'dayOfYear': {'byte': False, 'default': False, 'desc': 'Día del Año (1–366)'},
}


# ─── CONSULTAS DE MUESTRAS DE GEE ─────────────────────────────────────────────

def list_sample_collections():
    """Enumerar todas las FeatureCollections de muestras disponibles en la carpeta de activos SAMPLES."""
    try:
        assets = ee.data.listAssets({'parent': SAMPLE_ASSET_ROOT})['assets']
        return [a['name'].split('/')[-1] for a in assets if a['type'] == 'TABLE']
    except Exception as e:
        print(f"  ⚠️  No se pudieron enumerar los activos de muestra: {e}")
        return []


def load_sample_fc(collection_name):
    """Cargar una FeatureCollection de muestras por nombre."""
    return ee.FeatureCollection(f"{SAMPLE_ASSET_ROOT}/{collection_name}")


def filter_samples(fc, version=None, regions=None, period=None,
                   campaigns=None, years=None):
    """Aplicar filtros a una FeatureCollection de muestras."""
    if version:
        fc = fc.filter(ee.Filter.eq('version', version))
    if regions:
        fc = fc.filter(ee.Filter.inList('region', regions))
    if period:
        fc = fc.filter(ee.Filter.eq('period', period))
    if campaigns:
        fc = fc.filter(ee.Filter.inList('campaign', campaigns))
    if years:
        fc = fc.filter(ee.Filter.inList('year', years))
    return fc


def get_sample_stats(fc):
    """Devolver diccionario con recuentos de quemados/no quemados."""
    burned     = fc.filter(ee.Filter.eq('label', 1)).size().getInfo()
    not_burned = fc.filter(ee.Filter.eq('label', 0)).size().getInfo()
    return {'burned': burned, 'not_burned': not_burned, 'total': burned + not_burned}


# ─── CONVERSIÓN DE MUESTRA → TIF ──────────────────────────────────────────────

def get_multiband_mosaic(year, month=None, period='monthly', selected_bands=None):
    """
    Reconstrói uma imagem multibanda a partir das coleções de bandas individuais no GEE.
    """
    from M0_auth_config import get_asset_mosaic_collection
    
    if not selected_bands:
        from M0_auth_config import CONFIG
        selected_bands = CONFIG['bands_all']
    
    m_name = mosaic_name(year, month, period)
    
    # Criar imagem base vazia
    img = ee.Image()
    
    for band in selected_bands:
        col_id = get_asset_mosaic_collection(period, band)
        # Tenta carregar a imagem da coleção da banda
        band_img = ee.Image(f"{col_id}/{m_name}").rename(band)
        img = img.addBands(band_img)
        
    return img.select(selected_bands)

def samples_to_array(fc, selected_bands, max_samples=None):
    """
    Para cada ponto de muestra, extraer los valores de las bandas del mosaico correspondiente.
    Devuelve matrices numpy (X, y).

    selected_bands: lista de nombres de bandas a extraer
    """
    import math

    if max_samples:
        fc = fc.limit(max_samples)

    label_band = 'label'
    
    # Lista de bandas que queremos no mosaico final
    bands_to_sample = selected_bands + [label_band]

    def sample_point(feature):
        year  = ee.Number(feature.get('year')).int()
        month = ee.Number(feature.get('month')).int() # fix: use get instead of getNumber for simplicity
        period = feature.getString('period')

        # No GEE client-side (dentro do map), não podemos usar loops python complexos 
        # se as coleções mudam dinamicamente. No entanto, o sensor é global.
        # Vamos assumir que o sensor está definido no GLOBAL_OPTS.
        
        # Como o get_asset_mosaic_collection usa GLOBAL_OPTS, e estamos no lado do servidor,
        # vamos reconstruir o mosaico para este ponto.
        
        # Nota: no M3 piloto, o sensor é fixo por sessão (S2). 
        # Se precisarmos de multi-sensor dinâmico no mesmo FC, precisaríamos de mais lógica.
        
        # Para simplificar e manter performance, vamos reconstruir a imagem:
        mosaic = get_multiband_mosaic(year, month, period, selected_bands)

        sampled = mosaic.reduceRegion(
            reducer  = ee.Reducer.first(),
            geometry = feature.geometry(),
            scale    = 10
        )

        return feature.set(sampled)

    sampled_fc = fc.map(sample_point)

    # Extraer a Python
    features = sampled_fc.select(selected_bands + ['label']).getInfo()['features']

    X_rows, y_rows = [], []
    for feat in features:
        props = feat['properties']
        values = [props.get(b) for b in selected_bands]
        lbl    = props.get('label')
        if None not in values and lbl is not None:
            X_rows.append(values)
            y_rows.append(lbl)

    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.int32)
    return X, y


def export_samples_to_gcs(fc, selected_bands, version, region, output_prefix):
    """
    Exportar .tif de muestra a GCS para el entrenamiento.
    Utiliza sampleRegions en el mosaico para exportar una tabla plana.
    """
    def build_mosaic_for_sample(year, month, period):
        return get_multiband_mosaic(year, month, period, selected_bands)

    # Agrupar muestras por año+mes+período
    years   = fc.aggregate_array('year').distinct().getInfo()
    periods = fc.aggregate_array('period').distinct().getInfo()

    tasks = []
    for year in years:
        for period in periods:
            fc_sub = fc.filter(ee.Filter.eq('year', year)) \
                       .filter(ee.Filter.eq('period', period))

            months = fc_sub.aggregate_array('month').distinct().getInfo()
            months = months if months else [None]

            for month in months:
                if month:
                    fc_m = fc_sub.filter(ee.Filter.eq('month', int(month)))
                else:
                    fc_m = fc_sub

                if fc_m.size().getInfo() == 0:
                    continue

                mosaic = build_mosaic_for_sample(year, month, period)

                desc = f"{version}_{region}_{year}"
                if month:
                    desc += f"_{int(month):02d}"

                task = ee.batch.Export.table.toCloudStorage(
                    collection     = mosaic.select(selected_bands).sampleRegions(
                        collection = fc_m,
                        scale      = 10,
                        properties = ['label', 'year', 'month', 'region', 'period']
                    ),
                    description    = f'samples_{desc}',
                    bucket         = CONFIG['bucket'],
                    fileNamePrefix = f"{CONFIG['gcs_samples']}/{version}/{region}/{desc}",
                    fileFormat     = 'TFRecord',
                )
                task.start()
                tasks.append((desc, task))
                print(f"  📤  Exportación de muestras: {desc} [{task.status()['state']}]")

    return tasks


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
