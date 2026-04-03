"""
M1b — Ensamblador de Mosaicos Nacionales
MapBiomas Fuego Sentinel Monitor — Piloto Perú

Maneja:
  1. Ensamblar fragmentos (shards) de GCS en COG nacional
  2. Botón "Mosaicar Faltantes" (lo que tiene shards pero no COG)
  3. Panel de descargas directas
"""

import os
import subprocess
import calendar
import ipywidgets as widgets
from IPython.display import display, clear_output
from M0_auth_config import CONFIG, mosaic_name, monthly_chunk_path, monthly_mosaic_path
from M1_mosaic_generator import assemble_country_mosaic, check_mosaic_status

class MosaicAssemblerUI:
    def __init__(self):
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
        """Devuelve periodos que tienen shards (chunks > 0) pero NO mosaico final."""
        to_assemble = []
        ready = []
        for year in years:
            # Mensual
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
            # Anual
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
            # Solo los que tienen shards
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
            # Enlace al archivo COG final generado
            url = f"https://storage.googleapis.com/{CONFIG['bucket']}/{mosaic_pref}/{base}_{band}_cog.tif"
            links_html += f"• <a href='{url}' target='_blank' style='color:#4caf50;'>{band}</a> &nbsp;"
        
        display(widgets.HTML(f"<div style='background:#111;padding:12px;border-left:4px solid #4caf50;margin-top:5px;font-family:monospace;'>{links_html}</div>"))

    def show(self):
        display(self.ui)

def run_ui():
    MosaicAssemblerUI().show()
