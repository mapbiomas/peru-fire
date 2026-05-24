import os
import csv
import io
import time
import base64
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
from M0_auth_config import CONFIG, _get_fs
from M5_workplan import gcs_full, consolidated_stats_path, region_path
from M6_publisher import discover_classified_groups
from M_cache import CacheManager
from M_ui_components import make_empty_state, flash_output
from M_lang import L as Lang

L = widgets.Layout


class M6WorkplanUI:
    def __init__(self):
        self.fs = _get_fs()
        self._groups = []
        self._mosaics = set()
        self._stats_data = []
        self.lc_base = CONFIG['gcs_library_classifications']

        self.tabs = widgets.Tab()
        self.w_guide = widgets.HTML()
        self.tab_to_publish = widgets.VBox()
        self.tab_finished = widgets.VBox()
        self.tab_analytics = widgets.VBox()
        self.tab_coverage = widgets.VBox()

        self.btn_refresh = widgets.Button(description=Lang.REFRESH_M6, icon='refresh', layout=L(width='150px'))
        self.btn_refresh.on_click(lambda _: self._refresh_all())

        self._build_guide()

    def _build_guide(self):
        self.w_guide.value = Lang.GUIDE_M6_HTML.format(
            tab_publish=Lang.TAB_PUBLISH,
            tab_done=Lang.TAB_DONE,
            tab_analytics=Lang.TAB_ANALYTICS,
            tab_coverage=Lang.TAB_M6_COVERAGE,
        )

    def _discover_all(self):
        raw = discover_classified_groups(fs=self.fs)
        self._groups = sorted(raw)
        self._mosaics = set()
        for group in self._groups:
            m, r, p, c = group
            mg = gcs_full(region_path(m, r, p, c))
            if self.fs.exists(mg):
                self._mosaics.add(group)

    def _load_stats(self):
        self._stats_data = []
        lib_class = gcs_full(self.lc_base)
        patterns = [
            f"{lib_class}/*/consolidated_stats.csv",
            f"{lib_class}/consolidated_stats.csv",
        ]
        from M0_auth_config import _gcs_download
        for pat in patterns:
            for fp in sorted(self.fs.glob(pat)):
                try:
                    local_csv = os.path.join('/tmp', 'm6_consolidated.csv')
                    _gcs_download(fp, local_csv)
                    with open(local_csv, 'r') as f:
                        self._stats_data.extend(list(csv.DictReader(f)))
                    os.remove(local_csv)
                except Exception:
                    continue

    def _refresh_all(self):
        self._discover_all()
        self._load_stats()
        self._render_to_publish()
        self._render_finished()
        self._render_analytics()
        self._render_coverage()

    def _render_to_publish(self):
        pending = [g for g in self._groups if g not in self._mosaics]
        if not pending:
            self.tab_to_publish.children = [make_empty_state(Lang.NO_TASKS_PUBLISH)]
            return

        rows = []
        for m, r, p, c in sorted(pending):
            c_label = f"<span style='color:#7f8c8d;'> [{c}]</span>" if c else ""
            rows.append(widgets.HBox([
                widgets.HTML(f"<b>{m}</b>{c_label}", layout=L(width='220px')),
                widgets.HTML(r, layout=L(width='150px')),
                widgets.HTML(p, layout=L(width='120px')),
            ], layout=L(margin='2px 0', padding='4px', border='1px solid #eee')))
        self.tab_to_publish.children = [
            widgets.HTML(f"<b>{len(pending)} groups pending mosaic</b>"),
            widgets.VBox(rows, layout=L(margin='10px 0'))
        ]

    def _render_finished(self):
        done = sorted([g for g in self._groups if g in self._mosaics])
        if not done:
            self.tab_finished.children = [make_empty_state(Lang.NO_TASKS_DONE)]
            return

        rows = []
        for m, r, p, c in done:
            c_label = f"<span style='color:#7f8c8d;'> [{c}]</span>" if c else ""
            rows.append(widgets.HBox([
                widgets.HTML(f"<b>{m}</b>{c_label}", layout=L(width='220px')),
                widgets.HTML(r, layout=L(width='150px')),
                widgets.HTML(p, layout=L(width='120px')),
                widgets.HTML("<span style='color:green;'> mosaic OK</span>"),
            ], layout=L(margin='2px 0', padding='4px', border='1px solid #eee')))
        self.tab_finished.children = [
            widgets.HTML(f"<b>{len(done)} published groups</b>"),
            widgets.VBox(rows, layout=L(margin='10px 0'))
        ]

    def _render_analytics(self):
        if not self._stats_data:
            self.tab_analytics.children = [make_empty_state("No consolidated stats available. Run M6 publish first.")]
            return

        models = sorted(set(r['model_id'] for r in self._stats_data))
        regions = sorted(set(r['region'] for r in self._stats_data))
        periods = sorted(set(r['period'] for r in self._stats_data), reverse=True)

        f_model = widgets.Dropdown(options=['All'] + models, value='All', description=Lang.ANALYTICS_FILTER_MODEL, layout=L(width='200px'))
        f_region = widgets.Dropdown(options=['All'] + regions, value='All', description=Lang.ANALYTICS_FILTER_REGION, layout=L(width='200px'))
        f_period = widgets.Dropdown(options=['All'] + periods, value='All', description=Lang.ANALYTICS_FILTER_PERIOD, layout=L(width='200px'))
        filters = widgets.HBox([f_model, f_region, f_period])

        w_table = widgets.HTML()
        btn_download = widgets.Button(description=Lang.DOWNLOAD_TABLE, icon='download', layout=L(width='180px'))
        w_download = widgets.HTML()

        def _update_table(_=None):
            data = self._stats_data
            if f_model.value != 'All':
                data = [r for r in data if r['model_id'] == f_model.value]
            if f_region.value != 'All':
                data = [r for r in data if r['region'] == f_region.value]
            if f_period.value != 'All':
                data = [r for r in data if r['period'] == f_period.value]

            if not data:
                w_table.value = "<p style='color:gray;'>No matching records.</p>"
                return

            h = '<table style="border-collapse:collapse;width:100%;font-size:13px;">'
            h += '<tr style="background:#2c3e50;color:white;">'
            for col in ['Model', 'Region', 'Period', 'km\u00b2', '%', 'Confidence', 'Tiles']:
                h += f'<th style="padding:6px 10px;text-align:left;">{col}</th>'
            h += '</tr>'
            for row in data:
                h += '<tr style="border-bottom:1px solid #eee;">'
                h += f'<td style="padding:4px 10px;">{row["model_id"]}</td>'
                h += f'<td style="padding:4px 10px;">{row["region"]}</td>'
                h += f'<td style="padding:4px 10px;">{row["period"]}</td>'
                h += f'<td style="padding:4px 10px;">{row.get("burned_area_km2", "0")}</td>'
                h += f'<td style="padding:4px 10px;">{row.get("burned_percentage", "0")}%</td>'
                h += f'<td style="padding:4px 10px;">{row.get("mean_confidence", "0")}</td>'
                h += f'<td style="padding:4px 10px;">{row.get("tiles_total", "0")}</td>'
                h += '</tr>'
            h += '</table>'
            h += f'<p style="color:gray;font-size:12px;">{len(data)} records</p>'
            w_table.value = h
            btn_download._data = data

        def _on_download(_):
            data = getattr(btn_download, '_data', [])
            if not data:
                return
            now = time.strftime('%Y-%m-%d')
            fname = f"peru_fire_stats_{f_model.value}_{f_region.value}_{f_period.value}_{now}.csv"
            fname = fname.replace(' ', '_').replace('/', '-')

            output = io.StringIO()
            fieldnames = ['model_id', 'region', 'period', 'burned_area_km2', 'burned_percentage', 'mean_confidence', 'tiles_total', 'total_pixels', 'burned_pixels']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, '') for k in fieldnames})
            csv_bytes = output.getvalue().encode('utf-8')
            b64 = base64.b64encode(csv_bytes).decode('utf-8')
            w_download.value = f'<a href="data:text/csv;base64,{b64}" download="{fname}">Download {fname}</a>'

        for f in [f_model, f_region, f_period]:
            f.observe(_update_table, names='value')
        btn_download.on_click(_on_download)

        _update_table()
        self.tab_analytics.children = [filters, w_table, btn_download, w_download]

    def _render_coverage(self):
        all_rows = sorted(set((g[0], g[3]) for g in self._groups))
        all_regions = sorted(set(g[1] for g in self._groups))

        if not all_rows:
            self.tab_coverage.children = [make_empty_state("No classified groups found.")]
            return

        lines = ["<table style='border-collapse:collapse;font-size:13px;'>"]
        header = "<tr><th style='padding:6px 10px;text-align:left;'>Model</th>"
        for r in all_regions:
            header += f"<th style='padding:6px 10px;'>{r}</th>"
        header += "</tr>"
        lines.append(header)

        for m, c in all_rows:
            label = f"{m} [{c}]" if c else m
            line = f"<tr style='border-bottom:1px solid #eee;'><td style='padding:4px 10px;'><b>{label}</b></td>"
            for r in all_regions:
                periods = sorted([p for _m, _r, p, _c in self._groups if _m == m and _r == r and _c == c])
                periods_done = sorted([p for _m, _r, p, _c in self._mosaics if _m == m and _r == r and _c == c])
                if not periods:
                    cell = "<span style='color:#ccc;'>-</span>"
                else:
                    n = len(periods)
                    n_done = len(periods_done)
                    if n_done == n:
                        cell = f"<span style='color:green;'>{n}/{n}</span>"
                    elif n_done > 0:
                        cell = f"<span style='color:#f39c12;'>{n_done}/{n}</span>"
                    else:
                        cell = f"<span style='color:#3498db;'>0/{n}</span>"
                line += f"<td style='padding:4px 10px;text-align:center;'>{cell}</td>"
            line += "</tr>"
            lines.append(line)

        lines.append("</table>")
        legend = widgets.HTML("""
            <div style='margin-top:15px;font-size:12px;'>
                <span style='color:green;'>\u25cf Published</span> &nbsp;
                <span style='color:#f39c12;'>\u25cf Partial</span> &nbsp;
                <span style='color:#3498db;'>\u25cf Classified only</span> &nbsp;
                <span style='color:#ccc;'>\u25cf No data</span>
            </div>
        """)
        self.tab_coverage.children = [widgets.HTML("".join(lines)), legend]

    def display(self):
        self._build_guide()
        self._refresh_all()

        self.tabs.children = [
            self.w_guide, self.tab_to_publish, self.tab_finished,
            self.tab_analytics, self.tab_coverage
        ]
        self.tabs.set_title(0, Lang.TAB_GUIDE)
        self.tabs.set_title(1, Lang.TAB_PUBLISH)
        self.tabs.set_title(2, Lang.TAB_DONE)
        self.tabs.set_title(3, Lang.TAB_ANALYTICS)
        self.tabs.set_title(4, Lang.TAB_M6_COVERAGE)

        header = widgets.HBox([
            widgets.HTML("<b style='color:#2c3e50; font-size:14px;'>M6 - Mosaic, Stats & Publication</b>"),
            self.btn_refresh
        ], layout=L(margin='0 0 15px 0', align_items='center', padding='10px',
                    border='1px solid #e0e0e0', background='#fcfcfc'))

        display(widgets.VBox([header, self.tabs]))

    def refresh(self):
        self._refresh_all()


def run_m6_ui():
    ui = M6WorkplanUI()
    ui.display()
    return ui
