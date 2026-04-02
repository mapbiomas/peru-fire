"""
M2 — Gestor de Muestras
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

def samples_to_array(fc, selected_bands, max_samples=None):
    """
    Para cada punto de muestra, extraer los valores de las bandas del mosaico correspondiente.
    Devuelve matrices numpy (X, y).

    selected_bands: lista de nombres de bandas a extraer
    """
    import math

    if max_samples:
        fc = fc.limit(max_samples)

    label_band = 'label'
    bands_to_sample = selected_bands + [label_band]

    def sample_point(feature):
        year  = ee.Number(feature.get('year')).int()
        month = ee.Number(feature.getNumber('month')).int()
        period = feature.getString('period')

        # Construir el nombre del mosaico para esta muestra
        month_str = month.format('%02d')
        
        # Seleccionar la colección correcta según el período
        m_name = ee.String('s2_fire_peru_').cat(year.format('%d'))
        mosaic_path = ee.Algorithms.If(
            period.equals('monthly'),
            ee.String(CONFIG['asset_mosaics_monthly']).cat('/').cat(m_name).cat('_').cat(month_str),
            ee.String(CONFIG['asset_mosaics_yearly']).cat('/').cat(m_name)
        )

        mosaic = ee.Image(mosaic_path)

        sampled = mosaic.select(selected_bands).reduceRegion(
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
        m_name = f"s2_fire_peru_{year}"
        if period == 'monthly':
            asset_root = CONFIG['asset_mosaics_monthly']
            name = f"{m_name}_{month:02d}"
        else:
            asset_root = CONFIG['asset_mosaics_yearly']
            name = m_name
        return ee.Image(f"{asset_root}/{name}")

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


# ─── INTERFAZ DE IPYWIDGETS ───────────────────────────────────────────────────

class SampleManagerUI:
    """
    Interfaz interactiva para:
      - Seleccionar la colección de muestras + filtros
      - Elegir las bandas de entrada del modelo
      - Ver el equilibrio de clases
      - Devolver (fc, selected_bands) para el entrenamiento
    """

    def __init__(self):
        self.selected_fc     = None
        self.selected_bands  = []
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML

        title = HTML("""
            <div style="
                background:linear-gradient(135deg,#0d1b2a,#1b263b);
                color:#e0fbfc;padding:14px 18px;border-radius:10px;
                font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                🧬 <b>Gestor de Muestras</b> — Sentinel-2 Fire Monitor<br>
                <span style="color:#8892b0;font-size:11px;">
                Muestras vectoriales → Selección de bandas → Matrices de entrenamiento
                </span>
            </div>
        """)

        # ── Selector de colecciones
        collections = list_sample_collections()
        self.w_collection = widgets.Dropdown(
            options     = collections or ['(no se han encontrado colecciones)'],
            description = 'Colección:',
            style       = {'description_width': '100px'},
            layout      = widgets.Layout(width='380px')
        )

        # ── Filtros
        self.w_version = widgets.Text(
            value='v1', description='Versión:',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='200px')
        )
        self.w_period = widgets.RadioButtons(
            options=['monthly', 'annual', 'both'], value='monthly',
            description='Período:', style={'description_width': '100px'}
        )
        self.w_regions = widgets.Textarea(
            placeholder='una región por línea\np. ej. peru_r1_amazonia',
            description='Regiones:', rows=3,
            style={'description_width': '100px'},
            layout=widgets.Layout(width='380px')
        )
        self.w_years = widgets.Text(
            placeholder='p. ej. 2022,2023,2024',
            description='Años:', value='',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='300px')
        )

        # ── Selector de bandas
        band_items = []
        for band, info in ALL_BANDS.items():
            chk = widgets.Checkbox(
                value       = info['default'],
                description = f"{band}  —  {info['desc']}",
                layout      = widgets.Layout(width='320px')
            )
            band_items.append((band, chk))
        self.band_checkboxes = dict(band_items)

        band_box = widgets.VBox(
            [widgets.Label('📡 Bandas de entrada del modelo:')] +
            [chk for _, chk in band_items],
            layout=widgets.Layout(
                border='1px solid #333', padding='8px', border_radius='6px'
            )
        )

        # ── Botones
        self.btn_load    = widgets.Button(description='🔍 Cargar y Filtrar Muestras',
                                          button_style='info', layout=widgets.Layout(width='200px'))
        self.btn_confirm = widgets.Button(description='✅ Confirmar Selección',
                                          button_style='success', layout=widgets.Layout(width='200px'))

        self.out = widgets.Output()

        self.ui = widgets.VBox([
            title,
            widgets.HBox([
                widgets.VBox([self.w_collection, self.w_version,
                               self.w_period, self.w_years, self.w_regions]),
                band_box,
            ]),
            widgets.HBox([self.btn_load, self.btn_confirm]),
            self.out,
        ])

        self.btn_load.on_click(self._on_load)
        self.btn_confirm.on_click(self._on_confirm)

    def _get_selected_bands(self):
        return [b for b, chk in self.band_checkboxes.items() if chk.value]

    def _on_load(self, _):
        with self.out:
            clear_output()
            coll_name = self.w_collection.value
            version   = self.w_version.value.strip() or None
            period    = None if self.w_period.value == 'both' else self.w_period.value
            regions   = [r.strip() for r in self.w_regions.value.splitlines() if r.strip()] or None
            years     = [int(y) for y in self.w_years.value.split(',') if y.strip().isdigit()] or None

            print(f"🔍 Cargando colección: {coll_name}")
            fc = load_sample_fc(coll_name)
            fc = filter_samples(fc, version=version, regions=regions,
                                period=period, years=years)

            stats = get_sample_stats(fc)
            self.selected_fc = fc

            print(f"\n  📊 Distribución de las muestras:")
            print(f"     🔥 Quemado     : {stats['burned']:,}")
            print(f"     🌿 No quemado  : {stats['not_burned']:,}")
            print(f"     📦 Total       : {stats['total']:,}")

            if stats['total'] == 0:
                print("\n  ⚠️  No se han encontrado muestras con los filtros seleccionados.")
                return

            balance = stats['burned'] / stats['total'] * 100
            print(f"     ⚖️  Equilibrio     : {balance:.1f}% quemado")

            bands = self._get_selected_bands()
            print(f"\n  📡 Bandas seleccionadas ({len(bands)}): {bands}")
            print(f"     NUM_INPUT = {len(bands)}")

    def _on_confirm(self, _):
        with self.out:
            clear_output()
            if self.selected_fc is None:
                print("  ⚠️  Cargar muestras primero.")
                return
            bands = self._get_selected_bands()
            self.selected_bands = bands
            total = self.selected_fc.size().getInfo()
            print(f"✅ Confirmado:")
            print(f"   Muestras : {total:,}")
            print(f"   Bandas   : {bands}  (NUM_INPUT={len(bands)})")
            print(f"\n  Preparado para M3 — Entrenamiento del modelo.")

    def show(self):
        display(self.ui)

    def get_selection(self):
        """Devolver (fc, selected_bands) para su uso directo por el Entrenador del modelo."""
        if self.selected_fc is None or not self.selected_bands:
            raise ValueError("Ejecute primero confirmar selección.")
        return self.selected_fc, self.selected_bands


def run_ui():
    """Iniciar la interfaz del gestor de muestras en Colab."""
    ui = SampleManagerUI()
    ui.show()
    return ui
