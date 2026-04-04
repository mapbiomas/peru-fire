"""
M1 — Despachador de Exportaciones
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Generación de colecciones Sentinel-2 a través de GEE (mensual + anual)
  2. Exportación a GEE Asset (país completo)
  3. Exportación a GCS (país completo en fragmentos)
  4. Interfaz de usuario para solicitar exportaciones
"""

import ee
import os
import math
import json
import subprocess
from datetime import date, timedelta
import calendar
import ipywidgets as widgets
from IPython.display import display, clear_output

from M0_auth_config import CONFIG, gcs_path, mosaic_name, \
    monthly_chunk_path, monthly_mosaic_path, \
    yearly_chunk_path, yearly_mosaic_path, \
    get_country_geometry


# ─── FUNCIONES DE PROCESAMIENTO DE EE ─────────────────────────────────────────

def mask_and_rename(image):
    """Aplicar la máscara Cloud Score+ y renombrar las bandas de S2."""
    mask = image.select('cs').gte(CONFIG['cs_threshold'])
    return image \
        .updateMask(mask) \
        .select(CONFIG['s2_bands_in'], CONFIG['s2_bands_out'])


def add_nbr(image):
    """Añadir NBR invertido para la selección de mosaicos de calidad.
    Invertido: áreas quemadas (bajo NBR) → valores ALTOS → seleccionado por qualityMosaic().
    """
    nbr = image \
        .expression('(b("nir") - b("swir2")) / (b("nir") + b("swir2"))') \
        .multiply(-1).add(1).multiply(1000) \
        .int16().rename('nbr')
    return image.addBands(nbr)


def add_day_of_year(image):
    """Añadir la banda dayOfYear (1–366, int16) a partir de la fecha de adquisición."""
    doy = ee.Image(
        ee.Number.parse(
            ee.Date(image.get('system:time_start')).format('D')
        )
    ).int16().rename('dayOfYear')
    return image.addBands(doy)


def preprocess(image):
    """Preprocesamiento completo de S2: máscara de nubes → renombrar → NBR → dayOfYear."""
    image = mask_and_rename(image)
    image = add_nbr(image)
    image = add_day_of_year(image)
    return image


def get_focus_mask(year, month):
    """Devolver la máscara del buffer de foco de incendio para un año/mes determinado (Sudamérica)."""
    return ee.ImageCollection(CONFIG['focus_buffer']) \
        .filter(ee.Filter.eq('year', year)) \
        .filter(ee.Filter.eq('month', month)) \
        .mean()


def build_s2_collection(start_date, end_date, geometry, apply_focus_mask=False,
                         year=None, month=None):
    """Construir la ImageCollection S2 preprocesada para una ventana de tiempo."""
    cs_plus_bands = ee.ImageCollection(CONFIG['cs_plus']).first().bandNames()

    col = ee.ImageCollection(CONFIG['sensor']) \
        .filterDate(start_date, end_date) \
        .filterBounds(geometry) \
        .linkCollection(ee.ImageCollection(CONFIG['cs_plus']), cs_plus_bands) \
        .map(preprocess)

    if apply_focus_mask and year is not None and month is not None:
        focus = get_focus_mask(year, month)
        col = col.map(lambda img: img.updateMask(focus.unmask(0).gt(0)))

    return col


def build_mosaic(start_date, end_date, geometry, apply_focus_mask=False,
                  year=None, month=None):
    """
    Construir mosaico de calidad a partir de la colección S2.

    Devuelve una imagen con las bandas:
      - espectral [blue,green,red,nir,swir1,swir2]: dividir(100) → byte (0–100)
      - dayOfYear: int16 (1–366, sin conversión)
    """
    col = build_s2_collection(start_date, end_date, geometry,
                               apply_focus_mask, year, month)
    mosaic = col.qualityMosaic('nbr')

    # Espectral: S2 crudo (0–10000) ÷ 100 → 0–100 → byte
    spectral = mosaic.select(CONFIG['bands_spectral']) \
                     .divide(CONFIG['spectral_scale_factor']) \
                     .byte()

    # dayOfYear: mantener int16
    doy = mosaic.select('dayOfYear').int16()

    return spectral.addBands(doy)


# ─── CUADRÍCULA (Opcional, para referencia/depuración) ───────────────────────

def generate_grid(geometry, tile_size_deg=None):
    """
    Generar una cuadrícula de mosaicos para referencia.
    Nota: La exportación a GCS ahora usa la división nativa de GEE.
    """
    tile_size = tile_size_deg or CONFIG['tile_size_deg']
    bounds = geometry.bounds().coordinates().getInfo()[0]

    xmin, ymin = bounds[0][0], bounds[0][1]
    xmax, ymax = bounds[2][0], bounds[2][1]

    ncols = math.ceil((xmax - xmin) / tile_size)
    nrows = math.ceil((ymax - ymin) / tile_size)

    tiles = []
    for col in range(ncols):
        for row in range(nrows):
            x0, y0 = xmin + col * tile_size, ymin + row * tile_size
            x1, y1 = x0 + tile_size, y1 + row + tile_size
            tile_geom = ee.Geometry.Rectangle([x0, y0, x1, y1])
            tiles.append({'tile_id': f"c{col:02d}r{row:02d}", 'geometry': tile_geom})
    return tiles


# ─── FUNCIONES DE EXPORTACIÓN ─────────────────────────────────────────────────

def export_to_asset(mosaic, name, year, month=None, period='monthly'):
    """Enviar tarea de exportación de GEE a Asset (mosaico nacional completo)."""
    country_geom = get_country_geometry()

    if period == 'monthly':
        t_start = ee.Date(f'{year}-{month:02d}-01').millis()
        t_end   = ee.Date(f'{year}-{month:02d}-01').advance(1, 'month').millis()
    else:
        t_start = ee.Date(f'{year}-01-01').millis()
        t_end   = ee.Date(f'{year+1}-01-01').millis()

    img = mosaic \
        .clip(country_geom) \
        .set({
            'system:time_start': t_start,
            'system:time_end':   t_end,
            'country':  CONFIG['country'],
            'year':     year,
            'month':    month or 0,
            'period':   period,
            'sensor':   'sentinel2',
            'bands':    CONFIG['bands_all'],
            'name':     name,
        })

    if period == 'monthly':
        asset_id = f"{CONFIG['asset_mosaics_monthly']}/{name}"
    else:
        asset_id = f"{CONFIG['asset_mosaics_yearly']}/{name}"

    task = ee.batch.Export.image.toAsset(
        image       = img,
        description = f'ASSET_{name}',
        assetId     = asset_id,
        region      = country_geom.bounds(),
        scale       = 10,
        maxPixels   = 1e13,
        pyramidingPolicy = {'.default': 'median'},
    )
    task.start()
    return task


def export_to_gcs(mosaic, name, year, month=None, period='monthly'):
    """
    Enviar tareas de exportación de GEE a GCS para cada banda por separado.
    """
    geometry = get_country_geometry()
    
    if period == 'monthly':
        folder = monthly_chunk_path(year, month)
    else:
        folder = yearly_chunk_path(year)

    tasks = []
    for band in CONFIG['bands_all']:
        band_name = f"{name}_{band}"
        task = ee.batch.Export.image.toCloudStorage(
            image           = mosaic.select(band).clip(geometry),
            description     = f'GCS_{band_name}',
            bucket          = CONFIG['bucket'],
            fileNamePrefix  = f"{folder}/{band_name}",
            region          = geometry.bounds(),
            scale           = 10,
            maxPixels       = 1e13,
            fileFormat      = 'GeoTIFF',
            formatOptions   = {'cloudOptimized': True},
        )
        task.start()
        tasks.append(task)
    return tasks
# ─── VERIFICACIÓN DE ESTADO DE GCS ────────────────────────────────────────────

# ─── FINAL DEL MÓDULO DE LÓGICA ───────────────────────────────────────────────
# Las interfaces de usuario se han movido a:
# M1_export.py (GEE -> GCS)
# M2_mosaic.py  (GCS -> COG)

"""
M1 — Despachador de Exportaciones
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Generación de mosaicos en GEE
  2. Verificar qué meses/años ya están en GCS
  3. Botón "Exportar Faltantes" para automatización masiva
"""

import ee
import calendar
import ipywidgets as widgets
from IPython.display import display, clear_output
from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, yearly_chunk_path
# from M1_mosaic_generator import build_mosaic, export_to_asset, export_to_gcs, check_mosaic_status

class ExportDispatcherUI:
    def __init__(self):
        self._build_ui()

    def _get_active_tasks(self):
        # Devuelve nombres bases que están en ejecución o listos
        import ee
        active_names = set()
        try:
            tasks = ee.batch.Task.list()
            active = [t for t in tasks if t.state in ['READY', 'RUNNING']]
            for t in active:
                desc = t.config.get('description', '')
                if desc.startswith('ASSET_') or desc.startswith('GCS_'):
                    base = desc.replace('ASSET_', '').replace('GCS_', '')
                    # GCS añade sufijos _band, cortamos eso
                    if '_blue' in base: base = base.split('_blue')[0]
                    elif '_green' in base: base = base.split('_green')[0]
                    # Cortar sufijo rápido por longitud o buscar 's2_fire_peru_year_M'
                    parts = base.split('_')
                    if len(parts) >= 4 and parts[0] == 's2':
                        # reconstruir s2_fire_peru_2020_01
                        # las ultimas labels podrian ser los meses y el año
                        clean_base = '_'.join(parts[:5]) # s2_fire_peru_2020_01
                        active_names.add(clean_base)
                        clean_base_yearly = '_'.join(parts[:4]) # s2_fire_peru_2020
                        active_names.add(clean_base_yearly)
        except Exception as e:
            print(f'Error leyendo tareas: {e}')
        return active_names

    def _build_ui(self):
        from ipywidgets import HTML, Checkbox, VBox, HBox, Button, Layout, Label
        import ipywidgets as widgets
        from IPython.display import display, clear_output
        title = HTML("""
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#e94560;padding:16px;border-radius:10px;">
                🚀 <b>Despachador Inteligente</b> — GEE → Cloud Storage / Asset
            </div>
            <div style="margin-top:10px; font-style:italic;">Seleccione las tareas de exportación granularmente. Los shards de GCS son por banda.</div>
        """)
        self.out = widgets.Output()
        self.ui = VBox([title, self.out])
        
        with self.out:
            clear_output()
            print("⏳ Analizando disponibilidad de Shards y Assets en tiempo real...")
            
        import datetime
        now = datetime.datetime.now()
        current_year = now.year
        current_month = now.month
        start_year = 2019
        
        self.years = list(range(current_year, start_year - 1, -1))
        self.months = list(range(12, 0, -1))
        self.bands = CONFIG['bands_all']
        
        from M2_mosaic import fetch_all_gcs_files
        fetch_all_gcs_files(force=False, progress_out=self.out)
        active_tasks = self._get_active_tasks()
        
        # Optimización masiva: Cachear nombres de archivos en un SET para búsqueda O(1)
        with self.out: print("⏳ [1/3] Analizando GCS para búsqueda rápida...")
        all_gcs = fetch_all_gcs_files()
        presence_gcs = set(f.split('/')[-1] for f in all_gcs if f.endswith('.tif'))
        
        # Optimización: Listar Assets una sola vez
        with self.out: print("⏳ [2/3] Listando Assets en GEE...")
        try:
            m_assets_raw = ee.data.listAssets({'parent': CONFIG['asset_mosaics_monthly']})['assets']
            existing_m_assets = [a['name'].split('/')[-1] for a in m_assets_raw]
        except: existing_m_assets = []
        
        try:
            y_assets_raw = ee.data.listAssets({'parent': CONFIG['asset_mosaics_yearly']})['assets']
            existing_y_assets = [a['name'].split('/')[-1] for a in y_assets_raw]
        except: existing_y_assets = []

        with self.out: print("⏳ [3/3] Construyendo matriz de checkboxes...")

        self.chk_dict = {}
        items_visuals = []
        from M0_auth_config import mosaic_name, monthly_chunk_path, yearly_chunk_path
        
        for y in self.years:
            # Monthly
            months_to_show = [m for m in self.months if y < current_year or m <= current_month]
            for m in months_to_show:
                name_base = mosaic_name(y, m, 'monthly')
                # 1. Asset Checkbox
                has_asset = name_base in existing_m_assets
                
                chk_a = self._create_chk_m1(name_base, y, m, 'monthly', 'asset', has_asset, active_tasks)
                self.chk_dict[f"{name_base}_asset"] = chk_a
                items_visuals.append(chk_a)
                
                # 2. GCS Band Checkboxes
                for b in self.bands:
                    # Búsqueda que admite sufijos de shards (ej: -0000-0000)
                    has_gcs = any(f.startswith(f"{name_base}_{b}") for f in presence_gcs)
                    chk_g = self._create_chk_m1(name_base, y, m, 'monthly', f'gcs_{b}', has_gcs, active_tasks)
                    self.chk_dict[f"{name_base}_gcs_{b}"] = chk_g
                    items_visuals.append(chk_g)
            
            # Yearly
            name_y = mosaic_name(y, period='yearly')
            # Asset
            has_ay = name_y in existing_y_assets
            chk_ay = self._create_chk_m1(name_y, y, None, 'yearly', 'asset', has_ay, active_tasks)
            self.chk_dict[f"{name_y}_asset"] = chk_ay
            items_visuals.append(chk_ay)
            
            # GCS
            for b in self.bands:
                has_gcs_y = any(f.startswith(f"{name_y}_{b}") for f in presence_gcs)
                chk_gy = self._create_chk_m1(name_y, y, None, 'yearly', f'gcs_{b}', has_gcs_y, active_tasks)
                self.chk_dict[f"{name_y}_gcs_{b}"] = chk_gy
                items_visuals.append(chk_gy)

        self.flex_box = HBox(items_visuals, layout=Layout(flex_flow='row wrap', width='100%', grid_gap='5px', padding='10px', max_height='500px', overflow='y-scroll'))
        
        self.btn_select_all = Button(description='☑️ Marcar Pendientes', button_style='info', layout=Layout(width='200px'))
        self.btn_clear_all  = Button(description='☐ Limpiar', button_style='', layout=Layout(width='120px'))
        self.btn_manage     = Button(description='⚙️ Gestionar (Borrar/Canc)', button_style='warning', layout=Layout(width='220px'))
        
        self.btn_select_all.on_click(self._on_select_all)
        self.btn_clear_all.on_click(self._on_clear_all)
        self.btn_manage.on_click(self._on_manage)
        
        msg = HTML("""
            <div style="color:#e94560; font-weight:bold; margin-top:10px; border-left:4px solid; padding-left:10px;">
                👉 Después de seleccionar, ejecute la SIGUIENTE CELDA del notebook para disparar el proceso.
            </div>
        """)
        
        btns = HBox([self.btn_select_all, self.btn_clear_all, self.btn_manage])
        
        self.view_standard = VBox([self.flex_box, btns, msg])
        
        # UI de gestión (se oculta por defecto)
        self.btn_delete = Button(description='🔥 Borrar Seleccionados', button_style='danger', layout=Layout(width='200px'))
        self.btn_cancel_m = Button(description='↩️ Volver', button_style='', layout=Layout(width='120px'))
        self.btn_delete.on_click(self._on_delete_real)
        self.btn_cancel_m.on_click(self._on_cancel_manage)
        self.view_manage = VBox([
            HTML("<b style='color:orange;'>🛠️ MODO GESTIÓN: Seleccione archivos YA EXPORTADOS para borrar de GEE/GCS.</b>"),
            self.flex_box,
            HBox([self.btn_delete, self.btn_cancel_m])
        ])

        with self.out:
            clear_output()
            display(self.view_standard)

    def _create_chk_m1(self, name, y, m, p, type, exists, active_tasks):
        from ipywidgets import Checkbox, Layout
        label_p = f"{y}-{m:02d}" if m else f"{y}-Anual"
        label_t = "Asset" if type=='asset' else f"GCS {type.split('_')[1]}"
        desc = f"{label_p} {label_t}"
        
        is_active = any(name in tn for tn in active_tasks)
        
        chk = Checkbox(value=False, description=desc, indent=False, layout=Layout(width='180px', overflow='hidden'))
        chk._meta = {'year': y, 'month': m, 'period': p, 'name': name, 'type': type, 'exists': exists}
        
        if exists:
            chk.description = f"✅ OK {desc}"
            chk.disabled = True
            chk.style = {'description_width': 'initial', 'background': '#d4edda'}
        elif is_active:
            chk.description = f"⏳ {desc}"
            chk.disabled = True
            chk.style = {'description_width': 'initial', 'background': '#fff3cd'}
        else:
            chk.description = f"🧩 {desc}"
            
        return chk

    def _on_manage(self, _):
        # Entrar en modo gestión: habilitar solo lo que existe
        for chk in self.chk_dict.values():
            if chk._meta['exists']:
                chk.disabled = False
                chk.value = False
            else:
                chk.disabled = True
                chk.value = False
        with self.out:
            clear_output()
            display(self.view_manage)

    def _on_cancel_manage(self, _):
        self._build_ui() # Refrescar todo

    def _on_delete_real(self, _):
        to_delete = [chk._meta for chk in self.chk_dict.values() if chk.value]
        if not to_delete: return
        print(f"🔥 Borrando {len(to_delete)} items...")
        # Lógica de borrado (Asset/GCS)
        for item in to_delete:
            y, m, p, name = item['year'], item['month'], item['period'], item['name']
            if item['type'] == 'asset':
                root = CONFIG['asset_mosaics_monthly'] if p == 'monthly' else CONFIG['asset_mosaics_yearly']
                try: ee.data.deleteAsset(f"{root}/{name}")
                except: pass
            else:
                # GCS
                band = item['type'].split('_')[1]
                path = f"gs://{CONFIG['bucket']}/{CONFIG['folder_output']}/{item['name']}_{band}.tif"
                import subprocess
                subprocess.run(['gsutil', 'rm', path], capture_output=True)
        self._build_ui()

    def _on_select_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled: chk.value = True

    def _on_clear_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled:
                chk.value = False

    def get_selected(self):
        """Devolver la lista de metadatos de los mosaicos seleccionados para exportar."""
        to_export = []
        for chk in self.chk_dict.values():
            if chk.value and not chk.disabled:
                to_export.append(chk._meta)
        return to_export

    def _on_execute(self, _):
        to_export = self.get_selected()
        if not to_export:
            with self.out:
                print("⚠️ No hay ningún mosaico marcado para exportar.")
            return
            
        with self.out:
            from IPython.display import clear_output
            clear_output()
            print(f"✅ Se han marcado {len(to_export)} mosaicos.")
            print("🚀 Para iniciar la exportación de forma robusta, ejecute la SIGUIENTE CELDA del notebook.")
            print("   (Esto evitará que la interfaz se bloquee durante procesos largos).")

    def dispatch(self, to_export):
        """Dispara las tareas de exportación en GEE basándose en la selección granular."""
        if not to_export:
            print("⚠️ Lista de exportación vacía.")
            return
            
        import ee
        from M0_auth_config import get_country_geometry, mosaic_name
        geom = get_country_geometry()
        
        # Agrupar por periodo para no reconstruir el mosaico múltiples veces
        by_period = {}
        for item in to_export:
            key = (item['year'], item['month'], item['period'], item['name'])
            if key not in by_period: by_period[key] = []
            by_period[key].append(item)

        print(f"🔥 Iniciando despacho de {len(to_export)} tareas granulares...")
        for (y, m, p, name), items in by_period.items():
            if p == 'monthly':
                start = ee.Date(f'{y}-{m:02d}-01')
                end = start.advance(1, 'month')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=True, year=y, month=m)
            else:
                start = ee.Date(f'{y}-01-01')
                end = ee.Date(f'{y+1}-01-01')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=False)
            
            for item in items:
                t_type = item['type']
                if t_type == 'asset':
                    export_to_asset(mosaic, name, y, m, p)
                    print(f"   🚀 Asset: {name} ENVIADO.")
                elif t_type.startswith('gcs_'):
                    band = t_type.replace('gcs_', '')
                    # GCS granular (una banda a la vez)
                    folder = CONFIG['gcs_monthly_chunks'] if p == 'monthly' else CONFIG['gcs_yearly_chunks']
                    band_name = f"{name}_{band}"
                    task = ee.batch.Export.image.toCloudStorage(
                        image           = mosaic.select(band).clip(geom),
                        description     = f'GCS_{band_name}',
                        bucket          = CONFIG['bucket'],
                        fileNamePrefix  = f"{folder}/{band_name}",
                        region          = geom.bounds(),
                        scale           = 10,
                        maxPixels       = 1e13,
                        fileFormat      = 'GeoTIFF',
                        formatOptions   = {'cloudOptimized': True},
                    )
                    task.start()
                    print(f"   🚀 GCS {band}: {name} ENVIADO.")

    def run_export(self, is_confirm=False):
        from IPython.display import clear_output
        selected = self.get_selected()
        clear_output(wait=True)
        if not selected:
            print("⚠️ No has seleccionado ninguna tarea en la interfaz de arriba.")
            return

        else:
            self.dispatch(selected)

    def show(self):
        from IPython.display import display
        display(self.ui)

def start_export(ui_obj, confirm=False):
    """Función de conveniencia para llamar desde el notebook."""
    if ui_obj is None:
        print("⚠️ La interfaz no ha sido inicializada.")
        return
    ui_obj.run_export(is_confirm=confirm)

def run_ui():
    from IPython.display import clear_output, display
    clear_output(wait=True)
    print("✨ Cargando interfaz del Despachador...")
    ui_obj = ExportDispatcherUI()
    display(ui_obj.ui)
    return ui_obj
