
import tempfile, glob, subprocess, re
from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, monthly_mosaic_path, yearly_chunk_path, yearly_mosaic_path, get_temp_dir, check_command_exists
_GCS_CACHE = None

def fetch_all_gcs_files(force=False, progress_out=None):
    """
    Descarga todo el árbol de archivos de GCS de una vez para optimizar las consultas repetidas.
    """
    global _GCS_CACHE
    if _GCS_CACHE is not None and not force:
        return _GCS_CACHE

    import platform
    cmd = 'gsutil.cmd' if platform.system() == 'Windows' else 'gsutil'
    
    if progress_out:
        with progress_out:
            print("⏳ [1/2] Conectando a GCS y descargando índice completo del bucket (esto acelerará 100x las consultas)...")
            
    try:
        result = subprocess.run(
            [cmd, 'ls', '-r', f"gs://{CONFIG['bucket']}/"],
            capture_output=True, text=True
        )
        lines = result.stdout.splitlines()
        # Filtrar directorios o metadatos que terminan en ':' de la salida recursiva
        _GCS_CACHE = [line.strip() for line in lines if line.strip() and not line.endswith(':')]
        
        if progress_out:
            with progress_out:
                print(f"✅ [2/2] Índice cachado en memoria ({len(_GCS_CACHE)} recortes detectados).")
                
        return _GCS_CACHE
    except Exception as e:
        if progress_out:
            with progress_out: print(f"  ⚠️  error crítico al cargar caché de GCS: {e}")
        return []

def list_gcs_files(prefix):
    """Filtrar el caché global buscando archivos en un sub-prefijo de GCS."""
    all_files = fetch_all_gcs_files()
    target_prefix = f"gs://{CONFIG['bucket']}/{prefix}"
    # Validar que los archivos inician con el prefijo deseado (emulando gsutil ls gs://bucket/prefix/)
    return [f for f in all_files if f.startswith(target_prefix)]


def check_mosaic_status(year, months=None, period='monthly'):
    """
    Verificar qué mosaicos ya han sido exportados a GCS.
    Devuelve un diccionario: {mosaic_name: {'chunks': int, 'mosaic': bool}}
    """
    status = {}
    if period == 'monthly':
        check_months = months or list(range(1, 13))
        for month in check_months:
            name = mosaic_name(year, month, 'monthly')
            chunk_prefix = monthly_chunk_path(year, month)
            mosaic_prefix = monthly_mosaic_path(year, month)
            chunks = list_gcs_files(chunk_prefix)
            mosaics = list_gcs_files(mosaic_prefix)
            status[name] = {
                'chunks': len(chunks),
                'mosaic': len(mosaics) > 0,
            }
    else:
        name = mosaic_name(year, period='yearly')
        chunk_prefix = yearly_chunk_path(year)
        mosaic_prefix = yearly_mosaic_path(year)
        chunks = list_gcs_files(chunk_prefix)
        mosaics = list_gcs_files(mosaic_prefix)
        status[name] = {
            'chunks': len(chunks),
            'mosaic': len(mosaics) > 0,
        }
    return status


# ─── ENSAMBLAJE DE MOSAICO NACIONAL (VRT → COG) ───────────────────────────────

def check_m2_dependencies():
    """Verifica que gsutil y gdal estén disponibles."""
    deps = {
        'gsutil':  'gsutil' if os.name != 'nt' else 'gsutil.cmd',
        'gdalbuildvrt': 'gdalbuildvrt',
        'gdal_translate': 'gdal_translate'
    }
    missing = []
    for name, cmd in deps.items():
        if not check_command_exists(cmd):
            missing.append(name)
    return missing

def run_cmd(args, label="Comando"):
    """Ejecuta un comando y reporta errores detallados."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        return res
    except subprocess.CalledProcessError as e:
        print(f"  ❌ ERROR en {label}:")
        if e.stderr:
            print(f"     {e.stderr.strip()}")
        else:
            print(f"     {e.stdout.strip()}")
        raise e

def assemble_country_mosaic(year, month=None, period='monthly', bands=None, index=0, total=1, start_time_total=None):
    """
    Descargar fragmentos por banda, construir VRT y convertir a COG nacional.
    Identifica automáticamente las bandas presentes en la carpeta de GCS.
    """
    import tempfile, glob, re, time

    if period == 'monthly':
        chunk_prefix  = monthly_chunk_path(year, month)
        mosaic_prefix = monthly_mosaic_path(year, month)
        base_name = mosaic_name(year, month, 'monthly')
        label = f"{year}-{month:02d}"
    else:
        chunk_prefix  = yearly_chunk_path(year)
        mosaic_prefix = yearly_mosaic_path(year)
        base_name = mosaic_name(year, period='yearly')
        label = f"{year} (Anual)"

    print("-" * 40)
    progress_str = f"[{index+1}/{total}]"
    
    eta_str = ""
    if start_time_total and index > 0:
        elapsed = time.time() - start_time_total
        avg_time = elapsed / index
        remaining = avg_time * (total - index)
        mins, secs = divmod(int(remaining), 60)
        eta_str = f" | ETA: {mins:02d}m {secs:02d}s"

    print(f"🚀 {progress_str} Iniciando: {label}{eta_str}")
    print(f"   Identificador: {base_name}")

    # Verificar Dependencias
    missing = check_m2_dependencies()
    if missing:
        print(f"  ❌ ABORTO: Faltan herramientas esenciales en el sistema: {', '.join(missing)}")
        print("     Asegúrese de haber activado el entorno de Conda y que GDAL esté instalado.")
        return

    import platform
    gsutil_cmd = 'gsutil.cmd' if platform.system() == 'Windows' else 'gsutil'

    # Espacio de trabajo local (evitamos OneDrive si es posible)
    work_root = get_temp_dir()
    session_id = f"m2_{base_name}_{int(time.time())}"
    tmp_path = os.path.join(work_root, session_id)
    os.makedirs(tmp_path, exist_ok=True)

    try:
        # 1. Listar archivos remotos para identificar bandas disponibles
        print(f"  🔍 Analizando fragmentos en gs://{CONFIG['bucket']}/{chunk_prefix}/")
        ls_res = subprocess.run([
            gsutil_cmd, 'ls', f"gs://{CONFIG['bucket']}/{chunk_prefix}/*.tif"
        ], capture_output=True, text=True)
        
        all_remote_files = [line.strip() for line in ls_res.stdout.splitlines() if line.strip()]
        if not all_remote_files:
            print("  ⚠️  No se encontraron fragmentos. Saltando.")
            return

        # Identificar bandas (formato esperado: name_band_shard.tif)
        target_bands = bands or CONFIG['bands_all']
        band_files = {}
        for f in all_remote_files:
            fname = os.path.basename(f)
            for b_name in target_bands:
                # Detect files accurately by matching the expected base layer prefix
                if fname.startswith(f"{base_name}_{b_name}"):
                    if b_name not in band_files: band_files[b_name] = []
                    band_files[b_name].append(f)
                    break

        if not band_files:
            print(f"  ⚠️  No se detectaron bandas válidas en los archivos encontrados.")
            return

        # 2. Procesar cada banda por separado
        results = []
        for b_name, remote_shards in band_files.items():
            print(f"\n  🗂️  Procesando banda: {b_name} ({len(remote_shards)} fragmentos)")
            band_tmp = os.path.join(tmp_path, b_name)
            os.makedirs(band_tmp, exist_ok=True)

            # Descargar shards de ESTA banda
            print(f"      ⬇️  Descargando a {band_tmp} ...")
            run_cmd([gsutil_cmd, '-m', 'cp'] + remote_shards + [band_tmp], label=f"Descarga de shards ({b_name})")

            local_shards = glob.glob(os.path.join(band_tmp, '*.tif'))
            if not local_shards: continue

            # Construir VRT
            vrt_path = os.path.join(tmp_path, f"{base_name}_{b_name}.vrt")
            run_cmd(['gdalbuildvrt', vrt_path] + local_shards, label=f"Creación de VRT ({b_name})")

            # Convertir a COG con compresión LZW
            cog_remote_name = f"{base_name}_{b_name}_cog.tif"
            cog_local_path = os.path.join(tmp_path, cog_remote_name)
            
            print(f"    🗜️  Transformando VRT a COG (optimizado)...")
            run_cmd([
                'gdal_translate',
                '-of', 'COG',
                '-co', 'COMPRESS=LZW',
                '-co', 'PREDICTOR=2',
                '-co', 'NUM_THREADS=ALL_CPUS',
                '-co', 'BIGTIFF=YES',
                vrt_path, cog_local_path
            ], label=f"Conversión a COG ({b_name})")

            # Subir a la carpeta final
            dest = f"gs://{CONFIG['bucket']}/{mosaic_prefix}/{cog_remote_name}"
            print(f"      ⬆️  Subiendo {cog_remote_name} a GCS...")
            run_cmd([gsutil_cmd, 'cp', cog_local_path, dest], label=f"Subida de COG ({b_name})")
            
            # Verificación de subida
            check_ls = subprocess.run([gsutil_cmd, 'ls', dest], capture_output=True)
            if check_ls.returncode == 0:
                print(f"      ✅ Éxito: {cog_remote_name}")
            else:
                print(f"      ❌ ERROR: No se detectó el archivo en {dest}")
            
            results.append(dest)
            
    finally:
        # Limpieza (opcionalmente podríamos dejarlo pero por defecto borramos)
        import shutil
        print(f"\n  🧹 Limpiando espacio temporal...")
        try:
            shutil.rmtree(tmp_path)
        except:
            pass

    print(f"\n✅ Ensamblaje completado para: {base_name}")
    return results



"""
M2 — Ensamblador Nacional
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Ensamblar fragmentos (shards) de GCS en COG nacional
  2. Botón "Mosaicar Faltantes" (lo que tiene shards pero no COG)
  3. Panel de descargas directas
"""

print("DEBUG: M2 module file is being LOADED")

import os
import subprocess
import calendar
import ipywidgets as widgets
from IPython.display import display, clear_output

# Importar configuraciones
from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, monthly_mosaic_path
# Importar lógica de mosaicos


class MosaicAssemblerUI:
    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML, Checkbox, VBox, HBox, Button, Layout, Label
        import ipywidgets as widgets
        from IPython.display import display, clear_output
        from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, monthly_mosaic_path, yearly_chunk_path, yearly_mosaic_path

        title = HTML("""
            <div style="background:linear-gradient(135deg,#003300,#004d00);color:#b3ffb3;padding:14px;border-radius:10px;">
                🗺️ <b>Ensamblador Analítico</b> — GCS Shards → COG
            </div>
            <div style="margin-top:10px; font-style:italic;">Analizando fragmentos (shards) disponibles en GCS de manera modular...</div>
        """)
        
        self.out = widgets.Output()
        self.ui = VBox([title, self.out])
        
        with self.out:
            clear_output()
            print("⏳ Conectando e indexando disponibilidad granular por banda...")
            
        import datetime
        now = datetime.datetime.now()
        current_year = now.year
        current_month = now.month
        start_year = 2019
        
        self.years = list(range(current_year, start_year - 1, -1))
        self.months = list(range(12, 0, -1))
        
        # === Carga en Masa ===
        from M2_mosaic import fetch_all_gcs_files, list_gcs_files
        fetch_all_gcs_files(force=False, progress_out=self.out)
        
        self.chk_dict = {}
        items_visuals = []
        
        all_bands = CONFIG['bands_all']
        
        for y in self.years:
            # Monthly
            months_to_show = [m for m in self.months if y < current_year or m <= current_month]
            for m in months_to_show:
                c_pref = monthly_chunk_path(y, m)
                m_pref = monthly_mosaic_path(y, m)
                
                chunks = list_gcs_files(c_pref)
                if not chunks:
                    continue
                    
                mosaics = list_gcs_files(m_pref)
                
                # Los fragmentos (shards) exportados por GEE son multi-banda (contienen todas las bandas)
                # Si existe al menos un chunk, entonces todas las bandas están disponibles para ser ensambladas
                for b in all_bands:
                    has_cog = any(f"_{b}_cog" in m_c or m_c.endswith(f"_{b}_cog.tif") for m_c in mosaics)
                    
                    name = f"{y}_{m:02d}_{b}"
                    meta = {'year': y, 'month': m, 'period': 'monthly', 'band': b}
                    desc = f"{y}-{m:02d} [{b}]"
                    
                    chk = Checkbox(value=False, disabled=has_cog, indent=False)
                    chk._meta = meta
                    self.chk_dict[name] = chk
                    
                    if has_cog:
                        base_n = mosaic_name(y, m, 'monthly')
                        url = f"https://storage.googleapis.com/{CONFIG['bucket']}/{m_pref}/{base_n}_{b}_cog.tif"
                        chk.layout = Layout(width='20px', margin='0')
                        link = HTML(value=f"<a href='{url}' target='_blank' style='text-decoration:none; color:#155724; font-weight:bold; font-size:12px;'>📥 {desc}</a>")
                        box = HBox([chk, link], layout=Layout(width='160px', overflow='hidden', background='#d4edda', align_items='center', border='1px solid #c3e6cb'))
                        items_visuals.append(box)
                    else:
                        chk.description = f"🧩 {desc}"
                        chk.layout = Layout(width='160px', overflow='hidden', background='#cce5ff', border='1px solid #b8daff')
                        items_visuals.append(chk)
            
            # Yearly
            cy_pref = yearly_chunk_path(y)
            my_pref = yearly_mosaic_path(y)
            chunks_y = list_gcs_files(cy_pref)
            if chunks_y:
                mosaics_y = list_gcs_files(my_pref)
                for b in all_bands:
                    has_cog = any(f"_{b}_cog" in m_c or m_c.endswith(f"_{b}_cog.tif") for m_c in mosaics_y)
                    
                    name = f"{y}_ yearly_{b}"
                    meta = {'year': y, 'month': None, 'period': 'yearly', 'band': b}
                    desc = f"{y}-Anual [{b}]"
                    
                    chk = Checkbox(value=False, disabled=has_cog, indent=False)
                    chk._meta = meta
                    self.chk_dict[name] = chk
                    
                    if has_cog:
                        base_ny = mosaic_name(y, period='yearly')
                        url = f"https://storage.googleapis.com/{CONFIG['bucket']}/{my_pref}/{base_ny}_{b}_cog.tif"
                        chk.layout = Layout(width='20px', margin='0')
                        link = HTML(value=f"<a href='{url}' target='_blank' style='text-decoration:none; color:#155724; font-weight:bold; font-size:12px;'>📥 {desc}</a>")
                        box = HBox([chk, link], layout=Layout(width='160px', overflow='hidden', background='#d4edda', align_items='center', border='1px solid #c3e6cb'))
                        items_visuals.append(box)
                    else:
                        chk.description = f"🧩 {desc}"
                        chk.layout = Layout(width='160px', overflow='hidden', background='#cce5ff', border='1px solid #b8daff')
                        items_visuals.append(chk)

        if not items_visuals:
            items_visuals = [Label("⚠️ Nungún fragmento disponible ha sido detectado en el Bucket.")]
            
        self.flex_box = HBox(items_visuals, layout=Layout(flex_flow='row wrap', width='100%', grid_gap='5px', padding='15px', max_height='500px', overflow='y-scroll'))
        
        self.btn_select_all = Button(description='☑️ Marcar Disponibles', button_style='info', layout=Layout(width='200px'))
        self.btn_clear_all  = Button(description='☐ Limpiar TODAS', button_style='', layout=Layout(width='150px'))
        self.btn_manage     = Button(description='⚙️ Gestionar (Borrar)', button_style='warning', layout=Layout(width='200px'))
        
        self.btn_select_all.on_click(self._on_select_all)
        self.btn_clear_all.on_click(self._on_clear_all)
        self.btn_manage.on_click(self._on_manage)
        
        msg = HTML("""
            <div style="color:#b3ffb3; font-weight:bold; margin-top:10px; border-left:4px solid; padding-left:10px;">
                👉 Después de seleccionar, ejecute la SIGUIENTE CELDA del notebook para iniciar el ensamblado COG.
            </div>
        """)
        
        btns = HBox([self.btn_select_all, self.btn_clear_all, self.btn_manage])
        
        self.view_standard = VBox([self.flex_box, btns, msg])
        
        # UI de gestión
        self.btn_delete = Button(description='🔥 Borrar COGs Seleccionados', button_style='danger', layout=Layout(width='250px'))
        self.btn_cancel_m = Button(description='↩️ Volver', button_style='', layout=Layout(width='120px'))
        self.btn_delete.on_click(self._on_delete_real)
        self.btn_cancel_m.on_click(self._on_cancel_manage)
        self.view_manage = VBox([
            HTML("<b style='color:orange;'>🛠️ MODO GESTIÓN (M2): Seleccione COGs (bandas finalizadas) para borrar de GCS.</b>"),
            self.flex_box,
            HBox([self.btn_delete, self.btn_cancel_m])
        ])

        title.value = title.value.replace("Analizando fragmentos (shards) disponibles en GCS de manera modular...", "✅ Análisis de GCS completado. Seleccione las bandas de mosaico a ensamblar.")
        
        with self.out:
            clear_output()
            display(self.view_standard)

    def _on_manage(self, _):
        for chk in self.chk_dict.values():
            if chk.disabled: # Significa que ya tiene COG (check verde)
                chk.disabled = False
                chk.value = False
            else:
                chk.disabled = True
                chk.value = False
        with self.out:
            clear_output()
            display(self.view_manage)

    def _on_cancel_manage(self, _):
        self._build_ui()

    def _on_delete_real(self, _):
        to_delete = [chk._meta for chk in self.chk_dict.values() if chk.value]
        if not to_delete: return
        print(f"🔥 Borrando {len(to_delete)} COGs...")
        from M0_auth_config import CONFIG, monthly_mosaic_path, yearly_mosaic_path
        import subprocess
        for item in to_delete:
            pref = monthly_mosaic_path(item['year'], item['month']) if item['period']=='monthly' else yearly_mosaic_path(item['year'])
            path = f"gs://{CONFIG['bucket']}/{pref}/{item['name']}_cog.tif"
            subprocess.run(['gsutil', 'rm', path], capture_output=True)
        self._build_ui()

    def _on_select_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled:
                chk.value = True

    def _on_clear_all(self, _):
        for chk in self.chk_dict.values():
            if not chk.disabled:
                chk.value = False

    def get_selected(self):
        """Devolver la lista de metadatos de los mosaicos marcados para ensamblar."""
        to_assemble = []
        for chk in self.chk_dict.values():
            if chk.value and not chk.disabled:
                to_assemble.append(chk._meta)
        return to_assemble

    def _on_execute(self, _):
        to_assemble = self.get_selected()
        if not to_assemble:
            with self.out:
                print("⚠️ No hay ningún mosaico/banda marcado para ensamblar.")
            return
            
        with self.out:
            from IPython.display import clear_output
            clear_output()
            print(f"✅ Se han marcado {len(to_assemble)} mosaicos/bandas.")
            print("🚀 Para iniciar el proceso de ensamblado nacional de forma robusta,")
            print("   ejecute la SIGUIENTE CELDA del notebook.")
            print("   (Esto es necesario porque el proceso usa GDAL local y puede tardar).")

    def execute(self, to_assemble):
        """Ejecuta el proceso de ensamblado para la lista proporcionada."""
        if not to_assemble:
            print("⚠️ Lista de ensamblado vacía.")
            return

        import time
        from IPython.display import clear_output
        print("⏳ Limpiando caché y forzando actualización de índice...")
        from M2_mosaic import fetch_all_gcs_files, assemble_country_mosaic
        fetch_all_gcs_files(force=True)
        
        total = len(to_assemble)
        start_time_total = time.time()
        
        print(f"🛠️ Iniciando ensamblaje de {total} ítems...")
        
        for i, meta in enumerate(to_assemble):
            y, m, p, b = meta['year'], meta['month'], meta['period'], meta['band']
            try:
                assemble_country_mosaic(y, m, p, bands=[b], index=i, total=total, start_time_total=start_time_total)
                self._show_download_links(y, m, p, bands=[b])
            except Exception as e:
                print(f"  ❌ Error fatal procesando {y}-{m} [{b}]: {e}")
        
        # Recargar el caché al final para tener la vista general actualizada
        fetch_all_gcs_files(force=True)
        print("\n✨ Proceso de ensamblaje finalizado.")

    def run_assemble(self, is_confirm=False):
        """
        Método de una sola línea para el notebook.
        Si is_confirm=False, solo muestra qué se va a procesar.
        Si is_confirm=True, ejecuta el ensamblado real.
        """
        from IPython.display import clear_output
        selected = self.get_selected()
        
        clear_output(wait=True)
        if not selected:
            print("⚠️ No has seleccionado ninguna banda en la interfaz de arriba.")
            return

        if not is_confirm:
            print(f"🔍 SIMULACIÓN: Se han seleccionado {len(selected)} ítems para ensamblar:")
            for s in selected:
                label = f"{s['year']}-{s['month']:02d}" if s['month'] else f"{s['year']} (Anual)"
                print(f"   - {label} [{s['band']}]")
            print("\n👉 Para ejecutar de verdad, cambia a: run_assemble(is_confirm=True)")
        else:
            self.execute(selected)

    def _show_download_links(self, year, month, period='monthly', bands=None):
        from M0_auth_config import mosaic_name, monthly_chunk_path, monthly_mosaic_path, yearly_chunk_path, yearly_mosaic_path, CONFIG
        from IPython.display import display
        import ipywidgets as widgets
        
        if period == 'monthly':
            prefix = monthly_chunk_path(year, month)
            mosaic_pref = monthly_mosaic_path(year, month)
            label = f"{year}-{month:02d}"
            base = mosaic_name(year, month, 'monthly')
        else:
            prefix = yearly_chunk_path(year)
            mosaic_pref = yearly_mosaic_path(year)
            label = f"{year} (Anual)"
            base = mosaic_name(year, period='yearly')

        target_bands = bands or CONFIG['bands_all']
        links_html = f"<b>📥 Mosaico Ensamblado ({label}):</b><br>"
        for band in target_bands:
            url = f"https://storage.googleapis.com/{CONFIG['bucket']}/{mosaic_pref}/{base}_{band}_cog.tif"
            links_html += f"• <a href='{url}' target='_blank' style='color:#4caf50;'>{band}</a> &nbsp;"
        
        display(widgets.HTML(f"<div style='background:#111;padding:12px;border-left:4px solid #4caf50;margin-top:5px;font-family:monospace;'>{links_html}</div>"))

    def show(self):
        from IPython.display import display
        display(self.ui)


def start_assemble(ui_obj, confirm=False):
    """Función de una sola línea para el notebook."""
    if ui_obj is None:
        print("⚠️ La interfaz no ha sido inicializada.")
        return
    ui_obj.run_assemble(is_confirm=confirm)

def run_ui():
    from IPython.display import clear_output, display
    clear_output(wait=True)
    print("✨ Cargando interfaz del Ensamblador...")
    ui_obj = MosaicAssemblerUI()
    display(ui_obj.ui)
    return ui_obj
