"""
M1a — Despachador de Exportaciones
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
from M1_mosaic_generator import build_mosaic, export_to_asset, export_to_gcs, check_mosaic_status

class ExportDispatcherUI:
    def __init__(self):
        self._build_ui()

    def _build_ui(self):
        from ipywidgets import HTML
        title = HTML("""
            <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#e94560;padding:16px;border-radius:10px;">
                🚀 <b>Despachador de Exportaciones</b> — GEE → GCS
            </div>
        """)
        self.w_years = widgets.SelectMultiple(
            options=range(2017, 2027), value=[2024], description='Años:',
            style={'description_width': '80px'}, layout=widgets.Layout(width='150px')
        )
        self.w_months = widgets.SelectMultiple(
            options=[(f'{m:02d}', m) for m in range(1, 13)], value=[1], description='Meses:',
            style={'description_width': '80px'}, layout=widgets.Layout(width='120px')
        )
        self.btn_status = widgets.Button(description='🔍 Verificar Faltantes', button_style='info')
        self.btn_miss   = widgets.Button(description='✨ Exportar Faltantes', button_style='warning')
        self.btn_all    = widgets.Button(description='🔥 Exportar TODO el Año', button_style='danger')
        self.w_period = widgets.RadioButtons(
            options=['monthly', 'yearly', 'both'],
            value='monthly', description='Período:',
            style={'description_width': '80px'},
        )
        self.out = widgets.Output()
        
        controls = widgets.VBox([
            widgets.HBox([self.w_years, self.w_months]),
            self.w_period,
            widgets.HBox([self.btn_status, self.btn_miss, self.btn_all])
        ])
        self.ui = widgets.VBox([title, controls, self.out])
        
        self.btn_status.on_click(self._on_status)
        self.btn_miss.on_click(self._on_miss)
        self.btn_all.on_click(self._on_all)

    def _get_missings(self, years, months, period):
        missing = []
        for year in years:
            # Mensual
            if period in ('monthly', 'both'):
                status = check_mosaic_status(year, months, 'monthly')
                for name, s in status.items():
                    if s['chunks'] == 0:
                        m = int(name.split('_')[-1])
                        missing.append((year, m, 'monthly'))
            # Anual
            if period in ('yearly', 'both'):
                status = check_mosaic_status(year, period='yearly')
                for name, s in status.items():
                    if s['chunks'] == 0:
                        missing.append((year, None, 'yearly'))
        return missing

    def _on_status(self, _):
        years, months = list(self.w_years.value), list(self.w_months.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            miss = self._get_missings(years, months, period)
            if not miss:
                print("✅ Todos los periodos seleccionados ya tienen fragmentos en GCS.")
            else:
                print(f"⚠️  Faltan {len(miss)} mosaicos por exportar:")
                for y, m, p in miss: 
                    label = f"{y}-{m:02d}" if p == 'monthly' else f"{y} (Anual)"
                    print(f"   - {label}")

    def _dispatch(self, list_to_export):
        from M0_auth_config import get_country_geometry
        geom = get_country_geometry()
        for year, month, p in list_to_export:
            name = mosaic_name(year, month, p)
            if p == 'monthly':
                start = ee.Date(f'{year}-{month:02d}-01')
                end = start.advance(1, 'month')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=True, year=year, month=month)
                export_to_gcs(mosaic, name, year, month, 'monthly')
            else:
                start = ee.Date(f'{year}-01-01')
                end = ee.Date(f'{year+1}-01-01')
                mosaic = build_mosaic(start, end, geom, apply_focus_mask=False)
                export_to_gcs(mosaic, name, year, period='yearly')
            print(f"   🚀 Tarea enviada: {name}")

    def _on_miss(self, _):
        years, months = list(self.w_years.value), list(self.w_months.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            miss = self._get_missings(years, months, period)
            if not miss:
                print("✅ Nada que exportar.")
                return
            print(f"🔥 Exportando {len(miss)} periodos faltantes...")
            self._dispatch(miss)

    def _on_all(self, _):
        years = list(self.w_years.value)
        period = self.w_period.value
        with self.out:
            clear_output()
            print(f"🚨 Iniciando exportación TOTAL para los años {years}...")
            to_export = []
            for y in years:
                if period in ('monthly', 'both'):
                    for m in range(1, 13): to_export.append((y, m, 'monthly'))
                if period in ('yearly', 'both'):
                    to_export.append((y, None, 'yearly'))
            self._dispatch(to_export)

    def show(self):
        display(self.ui)

def run_ui():
    ExportDispatcherUI().show()
