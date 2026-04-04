"""
M6 — Publicador
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Aplicar máscara LULC (clases 26, 22, 33, 24) a los fragmentos clasificados
  2. Eliminar píxeles aislados (equivalente a connectedPixelCount)
  3. Ensamblar el mosaico nacional (VRT → COG) a partir de los mosaicos clasificados
  4. Control de versiones: borrador → final
  5. Subir la clasificación final enmascarada a GEE como una ImageCollection versionada
  6. Metadatos de la colección de GEE (descripción, bandas, procedencia de la muestra)
  7. Interfaz del publicador de campañas de ipywidgets
"""

import ee
import os
import json
import subprocess
import tempfile
import glob
import numpy as np
import ipywidgets as widgets
from IPython.display import display, clear_output
from datetime import datetime

try:
    import rasterio
    from rasterio.features import sieve
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

from M0_auth_config import CONFIG, gcs_path, classification_name, \
    get_country_geometry, list_regions


# ─── MÁSCARA LULC (aplicada post-clasificación) ────────────────────────────────

# Clases a excluir uniformemente en todo el país
LULC_MASK_CLASSES = [26, 22, 33, 24]
# 26 = Cuerpos de agua
# 22 = Sin vegetación / suelo desnudo
# 33 = Río, lago, océano
# 24 = Infraestructura urbana

LANDCOVER_ASSET = (
    'projects/mapbiomas-public/assets/peru/collection2/'
    'mapbiomas_peru_collection2_integration_v1'
)

def get_lulc_mask_ee(year):
    """
    Construir la máscara de exclusión LULC para un año determinado (Imagen EE).
    Devuelve una imagen binaria: 1 = válida (clase no enmascarada), 0 = excluida.
    Aplicado uniformemente en todo el país — sin distinción de región.
    Proxy: utiliza la banda 2022 para años superiores a 2022 hasta que esté disponible una colección más reciente.
    """
    # Ajustar a las bandas disponibles
    clamped_year = min(year, 2022)
    band_name = f'classification_{clamped_year}'

    lc = ee.Image(LANDCOVER_ASSET).select(band_name)

    excluded = lc.eq(LULC_MASK_CLASSES[0])
    for cls in LULC_MASK_CLASSES[1:]:
        excluded = excluded.Or(lc.eq(cls))

    return excluded.Not()   # 1 = píxel válido


def apply_lulc_mask_ee(classified_image, year):
    """Aplicar la máscara LULC a una imagen clasificada de EE."""
    valid = get_lulc_mask_ee(year)
    return classified_image.updateMask(valid)


def remove_isolated_pixels_ee(classified_image, min_connected=4):
    """
    Eliminar grupos aislados de menos de píxeles min_connected.
    Equivalente al filtro connectedPixelCount en el script de máscaras de referencia.
    """
    connections = classified_image.connectedPixelCount(
        maxSize=100, eightConnected=False
    )
    return classified_image.updateMask(connections.gt(min_connected))


# ─── ENSAMBLAJE DE MOSAICO NACIONAL ──────────────────────────────────────────

def assemble_classified_mosaic(year, month, regions, version,
                                period='monthly', draft=True):
    """
    1. Descargar todos los fragmentos clasificados de GCS
    2. Construir VRT → COG
    3. Subir a la carpeta de mosaicos de GCS
    Devuelve la ruta GCS del COG ensamblado.
    """
    r_str = '_'.join(regions)
    name  = classification_name(regions, version, year, month)

    if period == 'monthly':
        chunk_folder  = (f"{CONFIG['base_path']}/classifications/monthly/"
                         f"{year}/{month:02d}")
        mosaic_folder = (f"{CONFIG['base_path']}/classifications/monthly/"
                         f"{year}/{month:02d}/mosaics")
    else:
        chunk_folder  = f"{CONFIG['base_path']}/classifications/yearly/{year}"
        mosaic_folder = f"{CONFIG['base_path']}/classifications/yearly/{year}/mosaics"

    version_tag = f"{name}_draft" if draft else name

    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"  ⬇️  Descargando fragmentos: gs://{CONFIG['bucket']}/{chunk_folder}/")
        subprocess.run([
            'gsutil', '-m', 'cp',
            f"gs://{CONFIG['bucket']}/{chunk_folder}/*_cls.tif",
            tmpdir
        ], check=True)

        chunk_files = glob.glob(os.path.join(tmpdir, '*_cls.tif'))
        if not chunk_files:
            print(f"  ⚠️  No se han encontrado fragmentos clasificados. Saltando ensamblaje.")
            return None

        print(f"  🔗  Construyendo VRT a partir de {len(chunk_files)} mosaicos...")
        vrt_path = os.path.join(tmpdir, f'{version_tag}.vrt')
        subprocess.run(['gdalbuildvrt', '-resolution', 'highest',
                        vrt_path] + chunk_files, check=True)

        print(f"  🗜️  Convirtiendo a COG...")
        cog_path = os.path.join(tmpdir, f'{version_tag}_cog.tif')
        subprocess.run([
            'gdal_translate', '-of', 'COG',
            '-co', 'COMPRESS=DEFLATE',
            '-co', 'PREDICTOR=2',
            '-co', 'TILED=YES',
            '-co', 'BLOCKXSIZE=512',
            '-co', 'BLOCKYSIZE=512',
            vrt_path, cog_path
        ], check=True)

        dest = gcs_path(f"{mosaic_folder}/{version_tag}_cog.tif")
        subprocess.run(['gsutil', 'cp', cog_path, dest], check=True)
        print(f"  ☁️  Subido: {dest}")

    return dest


# ─── EXPORTACIÓN DE GEE (ACTIVO VERSIONADO FINAL) ───────────────────────────

def publish_to_gee(classified_image, year, month, regions, version,
                    hp_metadata=None, is_final=False):
    """
    Aplicar máscara LULC + eliminación de píxeles aislados, luego exportar a GEE Asset.

    classified_image : ee.Image donde quemado = dayOfYear, no quemado = 0
    hp_metadata      : dict de hyperparameters.json (opcional, para procedencia)
    is_final         : si es True, se exporta como conjunto de datos final (sin sufijo _draft)
    """
    import calendar

    name = classification_name(regions, version, year, month)
    if not is_final:
        name = name + '_draft'

    # ── Procesamiento post-clasificación
    masked = apply_lulc_mask_ee(classified_image, year)
    clean  = remove_isolated_pixels_ee(masked, min_connected=4)

    # ── Metadatos
    t_start = ee.Date(f'{year}-{month:02d}-01').millis()
    t_end   = ee.Date(f'{year}-{month:02d}-01').advance(1, 'month').millis()

    bands_input = (hp_metadata.get('bands_input', CONFIG['bands_model_default'])
                   if hp_metadata else CONFIG['bands_model_default'])
    sample_col  = (hp_metadata.get('sample_collection', 'unknown')
                   if hp_metadata else 'unknown')

    description_str = (
        f"MapBiomas Fuego — {CONFIG['country'].upper()} Área Quemada Mensual\n"
        f"Sensor    : Sentinel-2 (COPERNICUS/S2_SR_HARMONIZED)\n"
        f"Versión   : {version}{'  [BORRADOR]' if not is_final else ''}\n"
        f"Regiones  : {', '.join(regions)}\n"
        f"Período   : {year}-{month:02d}\n"
        f"Bandas    : {bands_input}\n"
        f"Muestras  : {sample_col}\n"
        f"Máscara LULC : clases {LULC_MASK_CLASSES} (Colección 2 de MapBiomas Perú)\n"
        f"Valor px  : día del año en que se detectó la quema (0 = no quemado)\n"
        f"Publicado : {datetime.now().isoformat()}"
    )

    img_final = clean.set({
        'system:time_start':  t_start,
        'system:time_end':    t_end,
        'country':            CONFIG['country'],
        'year':               year,
        'month':              month,
        'period':             'monthly',
        'sensor':             'sentinel2',
        'version':            version,
        'is_final':           is_final,
        'regions':            regions,
        'bands_input':        bands_input,
        'sample_collection':  sample_col,
        'lulc_mask_classes':  LULC_MASK_CLASSES,
        'pixel_unit':         'day_of_year',
        'description':        description_str,
        'publish_date':       datetime.now().isoformat(),
    })

    asset_id = f"{CONFIG['asset_classification']}/{name}"
    task = ee.batch.Export.image.toAsset(
        image       = img_final,
        description = f'PUBLISH_{name}',
        assetId     = asset_id,
        scale       = 10,
        maxPixels   = 1e13,
        pyramidingPolicy = {'.default': 'mode'},
    )
    task.start()

    print(f"  🚀  Exportación de GEE enviada: {asset_id}")
    print(f"      Estado de la tarea: {task.status()['state']}")
    return task, asset_id, description_str


# ─── INTERFAZ DE IPYWIDGETS ───────────────────────────────────────────────────

class PublisherUI:
    """
    Interfaz del publicador de campañas.
    Maneja: ensamblaje → máscara LULC → decisión de versión → exportación de GEE.
    """

    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        import calendar as cal

        title = HTML("""
            <div style="
                background:linear-gradient(135deg,#0a1628,#0d2137);
                color:#89dceb;padding:14px 18px;border-radius:10px;
                font-family:'Courier New',monospace;font-size:13px;margin-bottom:8px;">
                📢 <b>Publicador</b> — Máscara LULC → Control de Versiones → GEE<br>
                <span style="color:#8892b0;font-size:11px;">
                Clases LULC 26/22/33/24 enmascaradas | Exportación final o borrador
                </span>
            </div>
        """)

        available_regions = list_regions()
        self.w_regions = widgets.SelectMultiple(
            options=available_regions, value=available_regions[:1],
            description='Regiones:', style={'description_width': '100px'},
            layout=widgets.Layout(height='100px', width='380px')
        )
        self.w_version = widgets.Text(
            value='v1', description='Versión:',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='220px')
        )
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
        self.w_is_final = widgets.ToggleButton(
            value=False,
            description='🟡 Borrador',
            tooltip='Alternar para marcar como versión publicada final',
            button_style='warning',
            layout=widgets.Layout(width='160px', height='40px')
        )

        def _toggle_final(change):
            if change['new']:
                self.w_is_final.description  = '🟢 Final'
                self.w_is_final.button_style = 'success'
            else:
                self.w_is_final.description  = '🟡 Borrador'
                self.w_is_final.button_style = 'warning'
        self.w_is_final.observe(_toggle_final, names='value')

        self.btn_assemble = widgets.Button(
            description='🗺️ Ensamblar Mosaico',
            button_style='info',
            layout=widgets.Layout(width='200px')
        )
        self.btn_publish = widgets.Button(
            description='📢 Aplicar Máscara + Publicar',
            button_style='danger',
            layout=widgets.Layout(width='220px')
        )
        self.btn_check = widgets.Button(
            description='🔍 Verificar Cobertura',
            button_style='',
            layout=widgets.Layout(width='180px')
        )

        self.out = widgets.Output()

        self.ui = widgets.VBox([
            title,
            widgets.HBox([
                widgets.VBox([self.w_regions, self.w_version, self.w_is_final]),
                widgets.VBox([self.w_year, self.w_months]),
            ]),
            widgets.HBox([self.btn_check, self.btn_assemble, self.btn_publish]),
            self.out,
        ])

        self.btn_assemble.on_click(self._on_assemble)
        self.btn_publish.on_click(self._on_publish)
        self.btn_check.on_click(self._on_check)

    def _on_check(self, _):
        with self.out:
            clear_output()
            regions = list(self.w_regions.value)
            months  = list(self.w_months.value)
            year    = self.w_year.value
            version = self.w_version.value

            print(f"🔍 Verificación de cobertura — {year} | regiones: {regions}\n")
            for month in months:
                name = classification_name(regions, version, year, month)
                folder = (f"{CONFIG['base_path']}/classifications/monthly/"
                          f"{year}/{month:02d}")
                result = subprocess.run(
                    ['gsutil', 'ls', f"gs://{CONFIG['bucket']}/{folder}/*_cls.tif"],
                    capture_output=True, text=True
                )
                tiles = [l.strip() for l in result.stdout.splitlines() if l.strip()]
                pct   = f"  ({len(tiles)} fragmentos)"
                icon  = '✅' if tiles else '❌'
                print(f"  {icon}  {year}-{month:02d}  {pct}")

    def _on_assemble(self, _):
        with self.out:
            clear_output()
            regions = list(self.w_regions.value)
            months  = list(self.w_months.value)
            year    = self.w_year.value
            version = self.w_version.value
            draft   = not self.w_is_final.value

            print(f"🗺️  Ensamblando el mosaico nacional — {'BORRADOR' if draft else 'FINAL'}\n")
            for month in months:
                print(f"  📅  {year}-{month:02d}")
                dest = assemble_classified_mosaic(year, month, regions, version,
                                                   draft=draft)
                if dest:
                    print(f"  ✅  {dest}\n")

    def _on_publish(self, _):
        with self.out:
            clear_output()
            regions   = list(self.w_regions.value)
            months    = list(self.w_months.value)
            year      = self.w_year.value
            version   = self.w_version.value
            is_final  = self.w_is_final.value

            mode = '🟢 FINAL' if is_final else '🟡 BORRADOR'
            print(f"📢 Publicando — {mode}\n")

            for month in months:
                name = classification_name(regions, version, year, month)
                name_tag = name if is_final else f"{name}_draft"
                print(f"  📅  {year}-{month:02d}  →  {name_tag}")

                # Cargar de GEE Asset (el mosaico ensamblado ya debe estar en GEE)
                # Alternativa: reconstruir a partir de fragmentos COG de GCS mediante ee.Image.loadGeoTIFF
                # Usando GCS COG como una imagen temporal de Earth Engine
                base_folder = (f"{CONFIG['base_path']}/classifications/monthly/"
                               f"{year}/{month:02d}/mosaics")
                cog_path = gcs_path(f"{base_folder}/{name_tag}_cog.tif")

                # Cargar como ee.Image desde GCS
                classified_image = ee.Image.loadGeoTIFF(cog_path)

                task, asset_id, desc = publish_to_gee(
                    classified_image, year, month, regions, version,
                    is_final=is_final
                )
                print(f"  ✅  Asset: {asset_id}\n")
                print(f"  📋  Vista previa de la descripción:\n")
                for line in desc.split('\n'):
                    print(f"      {line}")
                print()

    def show(self):
        display(self.ui)


def run_ui():
    """Iniciar la interfaz del publicador en Colab."""
    ui = PublisherUI()
    ui.show()
    return ui
