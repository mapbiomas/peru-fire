
import tempfile, glob, subprocess, re
def list_gcs_files(prefix):
    """Enumerar archivos en un prefijo de GCS. Devuelve una lista de nombres de archivos."""
    try:
        result = subprocess.run(
            ['gsutil', 'ls', f"gs://{CONFIG['bucket']}/{prefix}/"],
            capture_output=True, text=True
        )
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return files
    except Exception as e:
        print(f"  ⚠️  error de gsutil: {e}")
        return []


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

def assemble_country_mosaic(year, month=None, period='monthly', bands=None):
    """
    Descargar fragmentos por banda, construir VRT y convertir a COG nacional.
    Identifica automáticamente las bandas presentes en la carpeta de GCS.
    """
    import tempfile, glob, re

    if period == 'monthly':
        chunk_prefix  = monthly_chunk_path(year, month)
        mosaic_prefix = monthly_mosaic_path(year, month)
        base_name = mosaic_name(year, month, 'monthly')
    else:
        chunk_prefix  = yearly_chunk_path(year)
        mosaic_prefix = yearly_mosaic_path(year)
        base_name = mosaic_name(year, period='yearly')

    print(f"\n🚀 Iniciando ensamblaje nacional para: {base_name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Listar archivos remotos para identificar bandas disponibles
        print(f"  🔍 Analizando fragmentos en gs://{CONFIG['bucket']}/{chunk_prefix}/")
        ls_res = subprocess.run([
            'gsutil', 'ls', f"gs://{CONFIG['bucket']}/{chunk_prefix}/*.tif"
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
                if f"_{b_name}_" in fname or fname.endswith(f"_{b_name}.tif"):
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
            band_tmp = os.path.join(tmpdir, b_name)
            os.makedirs(band_tmp, exist_ok=True)

            # Descargar shards de ESTA banda
            print(f"    ⬇️  Descargando...")
            subprocess.run([
                'gsutil', '-m', 'cp',
            ] + remote_shards + [band_tmp], check=True, capture_output=True)

            local_shards = glob.glob(os.path.join(band_tmp, '*.tif'))
            if not local_shards: continue

            # Construir VRT
            vrt_path = os.path.join(tmpdir, f"{base_name}_{b_name}.vrt")
            subprocess.run(['gdalbuildvrt', vrt_path] + local_shards, check=True, capture_output=True)

            # Convertir a COG con compresión LZW
            cog_remote_name = f"{base_name}_{b_name}_cog.tif"
            cog_local_path = os.path.join(tmpdir, cog_remote_name)
            
            print(f"    🗜️  Optimizando COG...")
            subprocess.run([
                'gdal_translate',
                '-of', 'COG',
                '-co', 'COMPRESS=LZW',
                '-co', 'PREDICTOR=2',
                '-co', 'NUM_THREADS=ALL_CPUS',
                '-co', 'BIGTIFF=YES',
                vrt_path, cog_local_path
            ], check=True, capture_output=True)

            # Subir a la carpeta final
            dest = f"gs://{CONFIG['bucket']}/{mosaic_prefix}/{cog_remote_name}"
            subprocess.run(['gsutil', 'cp', cog_local_path, dest], check=True, capture_output=True)
            print(f"    ✅ Subido: {dest}")
            results.append(dest)

    print(f"\n✅ Ensamblaje completado para: {base_name}")
    return results



"""
M1b — Ensamblador de Mosaicos Nacionales
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Ensamblar fragmentos (shards) de GCS en COG nacional
  2. Botón "Mosaicar Faltantes" (lo que tiene shards pero no COG)
  3. Panel de descargas directas
"""

print("DEBUG: M1b module file is being LOADED")

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
        print("DEBUG: MosaicAssemblerUI initializing")
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        title = HTML("""
            <div style="background:linear-gradient(135deg,#003300,#004d00);color:#b3ffb3;padding:14px;border-radius:10px;">
                🗺️ <b>Ensamblador de Mosaicos</b> — GCS Shards → COG Nacional
            </div>
        """)
        self.w_years = widgets.SelectMultiple(
            options=range(2017, 2027), value=[2024], description='Años:',
            style={'description_width': '80px'}, layout=widgets.Layout(width='150px')
        )
        self.w_months = widgets.SelectMultiple(
            options=[(f'{m:02d}', m) for m in range(1, 13)], value=[1], description='Meses:',
            style={'description_width': '60px'}, layout=widgets.Layout(width='120px')
        )
        self.w_period = widgets.RadioButtons(
            options=['monthly', 'yearly', 'both'],
            value='monthly', description='Período:',
            style={'description_width': '80px'},
        )
        self.w_bands = widgets.SelectMultiple(
            options=CONFIG['bands_all'],
            value=CONFIG['bands_all'],
            description='Bandas:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='200px', height='120px')
        )
        
        self.btn_status = widgets.Button(description='🔍 Verificar Shards', button_style='info')
        self.btn_miss   = widgets.Button(description='🏗️ Mosaicar Faltantes', button_style='warning')
        self.btn_all    = widgets.Button(description='🌊 Mosaicar TODO', button_style='danger')
        self.out = widgets.Output()
        
        controls = widgets.VBox([
            widgets.HBox([self.w_years, self.w_months, self.w_bands]),
            self.w_period,
            widgets.HBox([self.btn_status, self.btn_miss, self.btn_all])
        ])
        self.ui = widgets.VBox([title, controls, self.out])
        
        self.btn_status.on_click(self._on_status)
        self.btn_miss.on_click(self._on_miss)
        self.btn_all.on_click(self._on_all)

    def _get_status_dict(self, years, months, period):
        to_assemble = []
        ready = []
        for year in years:
            if period in ('monthly', 'both'):
                status = check_mosaic_status(year, months, 'monthly')
                for name, s in status.items():
                    m = int(name.split('_')[-1])
                    if s['mosaic']:
                        ready.append((year, m, "monthly", "Completado"))
                    elif s['chunks'] > 0:
                        to_assemble.append((year, m, "monthly", "Pendiente (Shards listos)"))
                    else:
                        ready.append((year, m, "monthly", "Sin datos en GCS"))
            if period in ('yearly', 'both'):
                status = check_mosaic_status(year, period='yearly')
                for name, s in status.items():
                    if s['mosaic']:
                        ready.append((year, None, "yearly", "Completado"))
                    elif s['chunks'] > 0:
                        to_assemble.append((year, None, "yearly", "Pendiente (Shards listos)"))
                    else:
                        ready.append((year, None, "yearly", "Sin datos en GCS"))
        return to_assemble, ready

    def _on_status(self, _):
        years, months = list(self.w_years.value), list(self.w_months.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            pend, done = self._get_status_dict(years, months, period)
            if pend:
                print(f"🏗️  {len(pend)} periodos listos para ser mosaiqueados:")
                for y, m, p, msg in pend:
                    label = f"{y}-{m:02d}" if p == 'monthly' else f"{y} (Anual)"
                    print(f"   - {label} ({msg})")
            else:
                print("✅ No hay mosaicos pendientes de ensamblaje.")
            print("\n🔍 Detalles adicionales:")
            for y, m, p, msg in done:
                label = f"{y}-{m:02d}" if p == 'monthly' else f"{y} (Anual)"
                print(f"   - {label}: {msg}")

    def _on_miss(self, _):
        years, months = list(self.w_years.value), list(self.w_months.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            pend, _ = self._get_status_dict(years, months, period)
            if not pend:
                print("✅ Nada emocionante que hacer.")
                return
            print(f"🛠️  Ensamblando {len(pend)} mosaicos faltantes...")
            selected_bands = list(self.w_bands.value)
            for y, m, p, _ in pend:
                assemble_country_mosaic(y, m, p, bands=selected_bands)
                self._show_download_links(y, m, p, bands=selected_bands)

    def _on_all(self, _):
        years = list(self.w_years.value)
        period = self.w_period.value
        selected_bands = list(self.w_bands.value)
        with self.out:
            clear_output()
            print(f"🌊 Mosaiqueando TODO el periodo para los años {years}...")
            pend, _ = self._get_status_dict(years, range(1, 13), period)
            for y, m, p, msg in pend:
                label = f"{y}-{m:02d}" if p == 'monthly' else f"{y} (Anual)"
                print(f"\n📂 Procesando {label}...")
                assemble_country_mosaic(y, m, p, bands=selected_bands)
                self._show_download_links(y, m, p, bands=selected_bands)

    def _show_download_links(self, year, month, period='monthly', bands=None):
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
        links_html = f"<b>📥 Mosaicos Ensamblados ({label}):</b><br>"
        for band in target_bands:
            url = f"https://storage.googleapis.com/{CONFIG['bucket']}/{mosaic_pref}/{base}_{band}_cog.tif"
            links_html += f"• <a href='{url}' target='_blank' style='color:#4caf50;'>{band}</a> &nbsp;"
        
        display(widgets.HTML(f"<div style='background:#111;padding:12px;border-left:4px solid #4caf50;margin-top:5px;font-family:monospace;'>{links_html}</div>"))

    def show(self):
        display(self.ui)

def run_ui():
    print("DEBUG: run_ui() CALLED in M1b")
    ui_obj = MosaicAssemblerUI()
    return ui_obj.ui
