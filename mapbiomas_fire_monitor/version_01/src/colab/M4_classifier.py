"""
M4 — Clasificador
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Cargar modelo de GCS (hyperparameters.json + pesos)
  2. Fragmentos de cuadrícula dinámica por región (~1/4 de escena Landsat)
  3. Descargar fragmentos COG de GCS
  4. Inferencia DNN por fragmento
  5. Salida: los píxeles quemados obtienen el valor dayOfYear (no 1 binario)
  6. Filtros morfológicos (apertura/cierre)
  7. Subir fragmentos clasificados de nuevo a GCS + GEE Asset
  8. Enmascarar el perímetro del fragmento (límite de la región)
  9. Interfaz de ipywidgets para el flujo de trabajo de la campaña de Colab
"""

import ee
import os
import json
import math
import subprocess
import tempfile
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output

try:
    import rasterio
    from rasterio.features import sieve
    from scipy.ndimage import binary_opening, binary_closing
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

from M0_auth_config import CONFIG, gcs_path, classification_name, \
    monthly_chunk_path, get_country_geometry, get_region_geometry, list_regions
from M3_model_trainer import ModelTrainer, normalize


# ─── AYUDAS DE CUADRÍCULA ─────────────────────────────────────────────────────

def generate_dynamic_grid(geometry, tile_size_deg=None):
    """
    Generar cuadrícula de fragmentos (~1/4 de escena Landsat ≈ 0.83° × 0.83°).
    geometría: Geometría de EE del área objetivo.
    Devuelve una lista de diccionarios: {tile_id, geometry_ee, bounds}
    """
    tile_size = tile_size_deg or CONFIG['tile_size_deg']
    coords = geometry.bounds().coordinates().getInfo()[0]
    xmin, ymin = coords[0][0], coords[0][1]
    xmax, ymax = coords[2][0], coords[2][1]

    ncols = math.ceil((xmax - xmin) / tile_size)
    nrows = math.ceil((ymax - ymin) / tile_size)

    tiles = []
    for col in range(ncols):
        for row in range(nrows):
            x0 = xmin + col * tile_size
            y0 = ymin + row * tile_size
            x1 = min(x0 + tile_size, xmax)
            y1 = min(y0 + tile_size, ymax)

            tile_bbox = ee.Geometry.Rectangle([x0, y0, x1, y1])
            intersection = tile_bbox.intersection(geometry, ee.ErrorMargin(1))

            # Saltar fragmentos sin intersección
            area = intersection.area(1).getInfo()
            if area < 1000:
                continue

            tile_id = f"c{col:02d}r{row:02d}"
            tiles.append({
                'tile_id':      tile_id,
                'geometry_ee':  tile_bbox,
                'intersection': intersection,
                'bounds':       [x0, y0, x1, y1],
                'col': col, 'row': row,
            })
    return tiles


# ─── DESCARGA DE MOSAICO ──────────────────────────────────────────────────────

def download_mosaic_tile(year, month, tile_id, period='monthly',
                          tmp_dir=None, region_name=None):
    """
    Descargar un fragmento COG de GCS para un fragmento/período determinado.
    Devuelve: ruta local .tif o None si no se encuentra.
    """
    if period == 'monthly':
        country = CONFIG['country']
        fname = f"s2_fire_{country}_{year}_{month:02d}_{tile_id}.tif"
        prefix = monthly_chunk_path(year, month)
    else:
        country = CONFIG['country']
        fname = f"s2_fire_{country}_{year}_{tile_id}.tif"
        prefix = f"{CONFIG['gcs_yearly_chunks']}/{year}"

    src = gcs_path(f"{prefix}/{fname}")
    dst = os.path.join(tmp_dir or '/tmp', fname)

    result = subprocess.run(
        ['gsutil', 'cp', src, dst],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return dst


def read_tif_as_array(tif_path, selected_bands_idx):
    """
    Leer un COG .tif y devolver (data_array, profile, transform, nodata).
    forma de data_array: (H, W, len(selected_bands_idx))
    """
    if not HAS_RASTERIO:
        raise ImportError("Se requiere rasterio para leer archivos .tif.")

    with rasterio.open(tif_path) as src:
        profile   = src.profile.copy()
        transform = src.transform
        nodata    = src.nodata

        bands = []
        for b_idx in selected_bands_idx:
            bands.append(src.read(b_idx + 1).astype(np.float32))

        # banda dayOfYear (siempre la última banda = índice 6 en el mosaico de 7 bandas)
        doy_band = src.read(7)  # int16, día juliano 1–366

        data = np.stack(bands, axis=-1)  # (H, W, C)

    return data, doy_band, profile, transform, nodata


# ─── FILTROS MORFOLÓGICOS ─────────────────────────────────────────────────────

def apply_morphological_filters(classification, min_size=4):
    """
    Aplicar apertura (eliminar ruido) y luego cierre (rellenar huecos pequeños).
    min_size: mínimo de píxeles conectados a mantener.
    """
    # Apertura: elimina pequeñas islas de verdaderos positivos
    opened = binary_opening(classification > 0, structure=np.ones((3, 3)))
    # Cierre: rellena pequeños huecos dentro de los parches quemados
    closed = binary_closing(opened, structure=np.ones((3, 3)))

    result = closed.astype(np.uint8)

    # Eliminar píxeles aislados (equivalente a connectedPixelCount)
    if HAS_RASTERIO:
        result = sieve(result, size=min_size)

    return result


# ─── PIPELINE DE CLASIFICACIÓN ───────────────────────────────────────────────

def classify_tile(tif_path, trainer, selected_bands, region_mask_ee=None,
                   morph_filter=True):
    """
    Ejecutar la clasificación DNN en un único fragmento .tif.
    Valores de salida:
      - píxel quemado → valor dayOfYear (día juliano del mosaico)
      - no quemado    → 0
      - enmascarado (LULC/límite de región) → nodata

    Devuelve: (classified_array, profile) listo para exportar.
    """
    # Índices de banda en el .tif (indexado en 0)
    all_bands = CONFIG['bands_all']  # ['blue','green','red','nir','swir1','swir2','dayOfYear']
    band_indices = [all_bands.index(b) for b in selected_bands if b in all_bands]

    data, doy_band, profile, transform, nodata = read_tif_as_array(tif_path, band_indices)
    H, W, C = data.shape

    # Aplanar para inferencia
    X_flat = data.reshape(-1, C)
    valid_mask = ~np.any(np.isnan(X_flat), axis=1)

    preds = np.zeros(H * W, dtype=np.uint8)
    if valid_mask.sum() > 0:
        predictions = trainer.predict_array(X_flat[valid_mask])
        preds[valid_mask] = predictions

    # Volver a dar forma
    pred_2d = preds.reshape(H, W)

    # Aplicar filtros morfológicos
    if morph_filter:
        pred_2d = apply_morphological_filters(pred_2d)

    # ── DISEÑO CLAVE: los píxeles quemados obtienen el valor dayOfYear
    # Los no quemados permanecen en 0, nodata donde doy no es válido
    doy_clipped = np.clip(doy_band, 1, 366).astype(np.uint16)
    classified = np.where(pred_2d > 0, doy_clipped, 0).astype(np.uint16)

    # Aplicar máscara de límite de región (cero fuera de la región)
    # Nota: Máscara LULC aplicada en M5 (post-clasificación)

    # Actualizar perfil para salida
    out_profile = profile.copy()
    out_profile.update(
        dtype    = rasterio.uint16,
        count    = 1,
        nodata   = 0,
        compress = 'deflate',
    )

    return classified, out_profile


def save_classification_tile(classified, profile, output_path):
    """Escribir la matriz clasificada en un .tif local."""
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(classified[np.newaxis, :, :])
    return output_path


# ─── SUBIR ────────────────────────────────────────────────────────────────────

def upload_classified_tile(local_path, year, month, tile_id,
                            regions, version, period='monthly'):
    """Subir fragmento clasificado a la carpeta de fragmentos de GCS."""
    name = classification_name(regions, version, year, month)
    r_str = '_'.join(regions)

    if period == 'monthly':
        folder = (f"{CONFIG['base_path']}/classifications/monthly/"
                  f"{year}/{month:02d}")
    else:
        folder = f"{CONFIG['base_path']}/classifications/yearly/{year}"

    fname = f"{name}_{tile_id}_cog.tif"
    dest  = gcs_path(f"{folder}/{fname}")

    subprocess.run(['gsutil', 'cp', local_path, dest], check=True)
    return dest


def upload_to_gee_asset(classified_ee, name, year, month, regions, version):
    """
    Subir la clasificación ensamblada a GEE Asset.
    classified_ee: ee.Image donde quemado = dayOfYear, no quemado = 0.
    """
    import calendar
    t_start = int(ee.Date(f'{year}-{month:02d}-01').getInfo()['value'])
    last    = calendar.monthrange(year, month)[1]
    t_end   = int(ee.Date(f'{year}-{month:02d}-{last:02d}').getInfo()['value'])

    img = classified_ee.set({
        'system:time_start': t_start,
        'system:time_end':   t_end,
        'country':    CONFIG['country'],
        'year':       year,
        'month':      month,
        'period':     'monthly',
        'sensor':     'sentinel2',
        'version':    version,
        'regions':    regions,
        'bands_input': CONFIG['bands_model_default'],
        'pixel_unit': 'day_of_year',
        'description': (
            f"MapBiomas Fuego — {CONFIG['country'].upper()} Área Quemada Mensual\n"
            f"Sensor: Sentinel-2 | Versión: {version}\n"
            f"Regiones: {', '.join(regions)}\n"
            f"Valor del píxel: día del año en el que se detectó la quemadura (0 = no quemado)"
        ),
    })

    asset_id = f"{CONFIG['asset_classification']}/{name}"
    task = ee.batch.Export.image.toAsset(
        image       = img,
        description = f'CLASS_{name}',
        assetId     = asset_id,
        scale       = 10,
        maxPixels   = 1e13,
        pyramidingPolicy = {'.default': 'mode'},
    )
    task.start()
    return task


# ─── EJECUTOR DE CAMPAÑA COMPLETA ─────────────────────────────────────────────

def run_classification_campaign(year, months, regions, version,
                                 period='monthly', out_widget=None):
    """
    Ejecutar un pipeline de clasificación completo para una campaña.
    Carga el modelo de GCS, genera la cuadrícula, clasifica todos los mosaicos, sube los resultados.
    """
    def _print(msg):
        if out_widget:
            with out_widget:
                print(msg)
        else:
            print(msg)

    _print(f"🔥 Iniciando campaña de clasificación")
    _print(f"   Año      : {year}")
    _print(f"   Meses    : {months}")
    _print(f"   Regiones : {regions}")
    _print(f"   Versión  : {version}\n")

    # Carga el modelo
    trainer = ModelTrainer(num_input=len(CONFIG['bands_model_default']))
    trainer.load(version, regions[0])  # cargar el modelo de la primera región
    selected_bands = trainer._bands_input or CONFIG['bands_model_default']
    _print(f"   Modelo   : {version}/{regions[0]}")
    _print(f"   Bandas   : {selected_bands}  (NUM_INPUT={len(selected_bands)})\n")

    # Construir la geometría combinada de todas las regiones seleccionadas
    region_geoms = [get_region_geometry(r) for r in regions]
    combined_geom = ee.Geometry.MultiPolygon(
        [g.coordinates().getInfo() for g in region_geoms]
    )

    # Generar cuadrícula para la región combinada
    tiles = generate_dynamic_grid(combined_geom)
    _print(f"   Cuadrícula: {len(tiles)} fragmentos × {CONFIG['tile_size_deg']}°\n")

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for month in months:
            _print(f"\n  📅  {year}-{month:02d}")
            tile_results = []

            for tile in tiles:
                tile_id = tile['tile_id']
                _print(f"      ↳ fragmento {tile_id}", end='  ')

                # Descargar fragmento de mosaico
                tif_path = download_mosaic_tile(
                    year, month, tile_id, period, tmpdir
                )
                if tif_path is None:
                    _print("⚠️  no se ha encontrado el fragmento, omitiendo")
                    continue

                # Clasificar
                try:
                    classified, profile = classify_tile(
                        tif_path, trainer, selected_bands
                    )

                    # Guardar local
                    name = classification_name(regions, version, year, month)
                    out_path = os.path.join(tmpdir, f"{name}_{tile_id}_cls.tif")
                    save_classification_tile(classified, profile, out_path)

                    # Subir a GCS
                    dest = upload_classified_tile(
                        out_path, year, month, tile_id, regions, version
                    )
                    _print(f"✅  → {dest.split('/')[-1]}")
                    tile_results.append({'tile_id': tile_id, 'gcs': dest})

                except Exception as e:
                    _print(f"❌  error: {e}")

            results.append({
                'year': year, 'month': month,
                'tiles_done': len(tile_results),
                'tiles_total': len(tiles),
            })

    _print(f"\n✅ Campaña completada.")
    for r in results:
        _print(f"   {r['year']}-{r['month']:02d}:  {r['tiles_done']}/{r['tiles_total']} fragmentos")

    return results


# ─── INTERFAZ DE IPYWIDGETS ───────────────────────────────────────────────────

class ClassifierUI:
    """Interfaz del clasificador orientada a la campaña."""

    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        import calendar as cal

        title = HTML("""
            <div style="
                background:linear-gradient(135deg,#1a0a00,#2d1500);
                color:#f38ba8;padding:14px 18px;border-radius:10px;
                font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                🔥 <b>Clasificador</b> — Área Quemada Mensual (Sentinel-2)<br>
                <span style="color:#8892b0;font-size:11px;">
                Salida: píxeles quemados = dayOfYear | no quemados = 0
                </span>
            </div>
        """)

        available_regions = list_regions()
        self.w_regions = widgets.SelectMultiple(
            options     = available_regions,
            value       = available_regions[:1] if available_regions else [],
            description = 'Regiones:',
            style       = {'description_width': '100px'},
            layout      = widgets.Layout(height='120px', width='420px')
        )
        self.w_version = widgets.Text(value='v1', description='Versión del modelo:',
                                       style={'description_width': '120px'},
                                       layout=widgets.Layout(width='250px'))
        self.w_year = widgets.IntSlider(
            value=2024, min=2017, max=2026, step=1,
            description='Año:', style={'description_width': '80px'},
            layout=widgets.Layout(width='350px')
        )
        self.w_months = widgets.SelectMultiple(
            options=[(f'{m:02d} — {cal.month_name[m]}', m) for m in range(1, 13)],
            value=[1], description='Meses:',
            style={'description_width': '80px'},
            layout=widgets.Layout(height='100px', width='350px')
        )
        self.w_morph = widgets.Checkbox(value=True,
                                         description='Aplicar filtros morfológicos')
        self.w_upload_gee = widgets.Checkbox(value=False,
                                              description='Subir a GEE Asset (post M5)')

        self.btn_run  = widgets.Button(description='🚀 Ejecutar Clasificación',
                                        button_style='danger',
                                        layout=widgets.Layout(width='220px'))
        self.btn_status = widgets.Button(description='🔍 Verificar Estado Fragmento',
                                          button_style='info',
                                          layout=widgets.Layout(width='220px'))
        self.out = widgets.Output()

        self.ui = widgets.VBox([
            title,
            widgets.HBox([
                widgets.VBox([self.w_regions, self.w_version]),
                widgets.VBox([self.w_year, self.w_months,
                               self.w_morph, self.w_upload_gee]),
            ]),
            widgets.HBox([self.btn_run, self.btn_status]),
            self.out,
        ])

        self.btn_run.on_click(self._on_run)
        self.btn_status.on_click(self._on_status)

    def _on_run(self, _):
        with self.out:
            clear_output()
            regions = list(self.w_regions.value)
            months  = list(self.w_months.value)
            year    = self.w_year.value
            version = self.w_version.value

            if not regions:
                print("  ⚠️  Seleccione al menos una región.")
                return

            run_classification_campaign(
                year=year, months=months, regions=regions,
                version=version, out_widget=self.out
            )

    def _on_status(self, _):
        with self.out:
            clear_output()
            year    = self.w_year.value
            months  = list(self.w_months.value)
            regions = list(self.w_regions.value)
            version = self.w_version.value

            print(f"🔍 Comprobando el estado de la clasificación — {year}")
            for month in months:
                name   = classification_name(regions, version, year, month)
                folder = (f"{CONFIG['base_path']}/classifications/monthly/"
                          f"{year}/{month:02d}")
                result = subprocess.run(
                    ['gsutil', 'ls', f"gs://{CONFIG['bucket']}/{folder}/"],
                    capture_output=True, text=True
                )
                files = [l.strip() for l in result.stdout.splitlines() if l.strip()]
                icon  = '✅' if files else '❌'
                print(f"  {icon}  {year}-{month:02d}  |  {len(files)} fragmentos")

    def show(self):
        display(self.ui)


def run_ui():
    """Iniciar la interfaz del clasificador en Colab."""
    ui = ClassifierUI()
    ui.show()
    return ui
