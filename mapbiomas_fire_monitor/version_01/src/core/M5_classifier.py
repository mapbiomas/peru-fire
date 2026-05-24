import os
import csv
import time
import threading
import numpy as np
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from M0_auth_config import CONFIG, _get_fs, _gcs_models_base, _gcs_download, _gcs_upload, get_temp_dir
from M_cache import CacheManager
from M5_workplan import load_workplan, save_workplan, make_job_id, tile_path, gcs_full, archive_job_on_gcs, delete_pending_job_gcs, tile_stats_path, region_stats_path, consolidated_stats_path
from M5_inference import load_model_from_gcs, classify_cell_with_cogs, build_band_paths
from M_regions import REGION_NAME_PROPERTY

_log_lock = threading.Lock()

def _fmt_time(s):
    h, r = divmod(int(s), 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"

def _log(out, msg):
    with _log_lock, out:
        print(msg)

def _auto_workers():
    return max(1, os.cpu_count() or 1)

def run_m5_workplan(progress_callback=None, n_workers=None):
    """Motor de clasificacion M5.

    Procesa todos los jobs PENDING del workplan, agrupados por (modelo, periodo).
    No incluye mosaicado ni publicacion — use M6_publisher.run_m6_publish().

    Args:
        progress_callback: opcional, llamado tras cada tile.
            firma: progress_callback(model, region, cell_id, i, total, status)
        n_workers: workers paralelos (default: auto detecta via os.cpu_count())
    """
    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets

    if n_workers is None:
        n_workers = _auto_workers()
    n_workers = max(1, n_workers)

    out = widgets.Output()
    display(out)
    print(f"Workers: {n_workers}")

    plan = load_workplan()
    _run_classification(plan, out, progress_callback, n_workers)


def _run_classification(plan, out, progress_callback=None, n_workers=None):
    """Fase 1: agrupa jobs por (modelo, periodo) y clasifica compartiendo COGs."""
    pending = [j for j in plan if j['status'] == 'PENDING' and j.get('enabled', True)]

    if not pending:
        with out:
            clear_output()
            display(HTML("<b style='color:green;'>No pending jobs to classify.</b>"))
        return

    with out:
        print("--- Phase 1: Classification ---")

    groups = defaultdict(list)
    for j in pending:
        groups[(j['model'], j['period'])].append(j)

    for (model_id, period), group in groups.items():
        with out:
            print(f"\nGroup: model '{model_id}' | period {period} | {len(group)} region(s)")

        try:
            _process_period(model_id, period, group, out, progress_callback, n_workers)
        except Exception as e:
            import traceback
            with out:
                print(f"[FATAL] Group '{model_id}' | {period} failed:")
                traceback.print_exc()
            p = load_workplan()
            for job in group:
                for pj in p:
                    if pj['id'] == job['id']:
                        pj['status'] = 'FAILED'
            save_workplan(p)
            continue


def generate_tile_stats(model_id, region, period, tile_results, fs=None, logger=None, campaign=None):
    """Guarda estadisticas por tile en CSV (usado por M5 durante classificacao)."""
    if fs is None:
        fs = _get_fs()

    if not tile_results:
        if logger:
            logger(f"    [WARN] No tile results to compute stats")
        return

    gcs_path = gcs_full(tile_stats_path(model_id, campaign))
    local_tmp = os.path.join(get_temp_dir('stats'), "stats_tile.csv")

    fieldnames = ['model_id', 'region', 'period', 'tile_id',
                  'total_pixels', 'burned_pixels', 'mean_confidence']

    rows = []
    for tr in tile_results:
        rows.append({
            'model_id': model_id,
            'region': region,
            'period': period,
            'tile_id': tr.get('tile_id', ''),
            'total_pixels': tr.get('total_pixels', 0),
            'burned_pixels': tr.get('burned_pixels', 0),
            'mean_confidence': f"{tr.get('mean_confidence', 0):.4f}",
        })

    with open(local_tmp, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    _gcs_upload(local_tmp, gcs_path)
    os.remove(local_tmp)

    if logger:
        logger(f"    Tile stats saved ({len(rows)} tiles)")


def generate_region_stats(model_id, region, period, tile_results, fs=None, logger=None, campaign=None):
    """Agrega estadisticas por region+periodo y alimenta consolidated (usado por M5 durante classificacao)."""
    from M_gcs import mkdir

    if fs is None:
        fs = _get_fs()

    if not tile_results:
        return

    total_pixels = sum(tr.get('total_pixels', 0) for tr in tile_results)
    burned_pixels = sum(tr.get('burned_pixels', 0) for tr in tile_results)
    confidences = [tr.get('mean_confidence', 0) for tr in tile_results if tr.get('burned_pixels', 0) > 0]

    resolution_m = 10
    pixel_area_m2 = resolution_m ** 2
    burned_area_km2 = burned_pixels * pixel_area_m2 / 1_000_000
    total_area_km2 = total_pixels * pixel_area_m2 / 1_000_000 if total_pixels else 0

    row = {
        'model_id': model_id,
        'region': region,
        'period': period,
        'tiles_total': len(tile_results),
        'tiles_processed': len([tr for tr in tile_results if tr.get('total_pixels', 0) > 0]),
        'total_pixels': total_pixels,
        'burned_pixels': burned_pixels,
        'burned_area_km2': f"{burned_area_km2:.2f}",
        'total_area_km2': f"{total_area_km2:.2f}",
        'burned_percentage': f"{(burned_pixels / total_pixels * 100):.2f}" if total_pixels else "0.00",
        'mean_confidence': f"{np.mean(confidences):.4f}" if confidences else "0.0000",
    }

    local_tmp = os.path.join(get_temp_dir('stats'), "stats_region.csv")
    fieldnames = list(row.keys())

    gcs_path = gcs_full(region_stats_path(model_id, campaign))
    existing_rows = []
    try:
        local_existing = os.path.join(get_temp_dir('stats'), "existing.csv")
        _gcs_download(gcs_path, local_existing)
        with open(local_existing, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r['region'] == region and r['period'] == period:
                    continue
                existing_rows.append(r)
        os.remove(local_existing)
    except Exception:
        pass

    with open(local_tmp, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing_rows:
            writer.writerow(r)
        writer.writerow(row)

    _gcs_upload(local_tmp, gcs_path)
    os.remove(local_tmp)

    consolidated_path = gcs_full(consolidated_stats_path())
    cons_rows = []
    try:
        local_cons = os.path.join(get_temp_dir('stats'), "consolidated.csv")
        _gcs_download(consolidated_path, local_cons)
        with open(local_cons, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r['region'] == region and r['period'] == period and r['model_id'] == model_id:
                    continue
                cons_rows.append(r)
        os.remove(local_cons)
    except Exception:
        pass

    local_cons = os.path.join(get_temp_dir('stats'), "consolidated.csv")
    with open(local_cons, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in cons_rows:
            writer.writerow(r)
        writer.writerow(row)

    dir_path = consolidated_path.rsplit('/', 1)[0]
    mkdir(dir_path)
    _gcs_upload(local_cons, consolidated_path)
    os.remove(local_cons)

    if logger:
        logger(f"    Region + consolidated stats updated")


def _classify_one_tile(cell, model_id, region_name, period, campaign,
                        predict_fn, bands_config, norm_stats, band_paths, band_order,
                        out, worker_id, fs):
    cell_id = cell['name']
    out_rel = tile_path(model_id, region_name, cell_id, period, campaign)
    out_full = gcs_full(out_rel)

    if fs.exists(out_full):
        _log(out, f"    [W{worker_id}] {cell_id}: already exists, skipped")
        return ('skipped', cell_id, region_name, None, worker_id)

    _log(out, f"    [W{worker_id}] >>> {cell_id}")
    try:
        stats = classify_cell_with_cogs(
            cell_id, predict_fn, bands_config, norm_stats,
            out_full, band_paths, band_order,
            logger=lambda m: _log(out, m), worker_id=worker_id
        )
    except Exception as e:
        _log(out, f"    [W{worker_id}] {cell_id}: [ERROR] {e}")
        return ('error', cell_id, region_name, None, worker_id)

    if stats:
        stats['tile_id'] = cell_id
        stats['region'] = region_name
        stats['period'] = period
        return ('done', cell_id, region_name, stats, worker_id)
    else:
        _log(out, f"    [W{worker_id}] <<< {cell_id} warn: no stats")
        return ('warn', cell_id, region_name, None, worker_id)


def _process_period(model_id, period, group_jobs, out, progress_callback=None, n_workers=None):
    """Procesa todas las regiones de un (modelo, periodo) compartiendo COGs.

    Los COGs se descargan una unica vez y se reusan para todos los tiles
    de todas las regiones del grupo.
    """
    import ee
    from M0_auth_config import authenticate, _gcs_models_base

    authenticate()
    fs = _get_fs()

    # Extrai campanha do primeiro job (todos no grupo compartilham o mesmo periodo)
    campaign = group_jobs[0].get('campaign', '') if group_jobs else ''

    parts = period.split('_')
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 0

    # 1. Cargar modelo + metadatos (una vez)
    with out:
        print(f"  Loading model '{model_id}'...")

    model_dir = f"gs://{CONFIG['bucket']}/{_gcs_models_base()}/{model_id}"
    model, meta, bands_config, norm_stats, band_order = load_model_from_gcs(
        model_dir, fs, logger=lambda m: _log(out, m)
    )
    predict_fn = lambda x: model.predict(x, verbose=0, batch_size=65536)

    # 2. Construir paths e verificar COGs via CacheManager primeiro
    band_paths = build_band_paths(bands_config, year, month)

    period_type = 'monthly' if month else 'annually'
    state = CacheManager.get_state()
    known_cogs = set(state.get(f'cogs_{period_type}', []))

    with out:
        print(f"  Checking COGs for period '{period}'...")
    for b, p in band_paths.items():
        # Extrai o nome base (ex: image_peru_fire_sentinel2_minnbr_2025_08_blue)
        cog_basename = os.path.basename(p).lower().replace('_cog.tif', '')
        in_cache = cog_basename in known_cogs
        exists = "OK (cache)" if in_cache else ("OK" if fs.exists(f"gs://{p}") else "MISSING")
        with out:
            print(f"    {b}: {exists}")

    first_full = f"gs://{band_paths[band_order[0]]}"
    first_basename = os.path.basename(first_full).lower().replace('_cog.tif', '')
    if first_basename not in known_cogs and not fs.exists(first_full):
        raise FileNotFoundError(f"COG not found at: {first_full}")

    with out:
        print(f"  COGs opened via streaming ({len(band_paths)} bands)")

    all_tile_results = []

    # 4. Pre-computar celdas de todas as regiões para progresso cumulativo
    region_cells_map = {}
    for job in group_jobs:
        region_cells_map[job['region']] = _get_region_cells(job['region'])
    total_cells_group = sum(len(cells) for cells in region_cells_map.values())
    processed = 0
    _t0 = time.time()
    _done = 0
    _completed_cards = 0
    _total_cards = len(group_jobs)

    # 5. Procesar cada region del grupo
    for job_idx, job in enumerate(group_jobs):
        region_name = job['region']

        job['status'] = 'RUNNING'
        p = load_workplan()
        for pj in p:
            if pj['id'] == job['id']:
                pj['status'] = 'RUNNING'
        save_workplan(p)

        with out:
            print(f"\n  Region {job_idx+1}/{len(group_jobs)}: {region_name}")

        cells = region_cells_map[region_name]
        if not cells:
            with out:
                print(f"  [WARN] No cells found for {region_name}")
            continue

        total = len(cells)
        with out:
            print(f"  {total} tiles to process.")

        tile_results = []

        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = {}
            for i, cell in enumerate(cells):
                worker_id = (i % n_workers) + 1
                future = executor.submit(
                    _classify_one_tile,
                    cell, model_id, region_name, period, campaign,
                    predict_fn, bands_config, norm_stats, band_paths, band_order,
                    out, worker_id, fs
                )
                futures[future] = cell['name']

            completed_in_region = 0
            _last_eta_log = time.time()
            for future in as_completed(futures):
                status, cell_id, reg, stats, wid = future.result()
                completed_in_region += 1
                now = time.time()
                tile_elapsed = (stats.get('tile_elapsed', 0) if stats else 0)

                if status == 'skipped':
                    _done += 1
                    if progress_callback:
                        progress_callback(model_id, reg, cell_id, completed_in_region, total, 'skipped')
                elif status == 'error':
                    _done += 1
                    if progress_callback:
                        progress_callback(model_id, reg, cell_id, completed_in_region, total, 'error')
                elif status == 'warn':
                    if progress_callback:
                        progress_callback(model_id, reg, cell_id, completed_in_region, total, 'error')
                else:
                    # status == 'done'
                    _done += 1
                    tile_results.append(stats)
                    if progress_callback:
                        progress_callback(model_id, reg, cell_id, completed_in_region, total, 'done')
                    group_elapsed = now - _t0
                    avg_tile = group_elapsed / max(_done, 1)
                    group_remaining = avg_tile * (total_cells_group - _done)
                    group_total = group_elapsed + group_remaining
                    _log(out, f"    [W{wid}] <<< {cell_id} done in {_fmt_time(tile_elapsed)} "
                          f"| tile {completed_in_region}/{total}"
                          f" | region {job_idx+1}/{_total_cards}"
                          f" | group {_done}/{total_cells_group}"
                          f" | elapsed group {_fmt_time(group_elapsed)}"
                          f" | total ~{_fmt_time(group_total)} | remaining ~{_fmt_time(group_remaining)}")

                # ETA log every 5 tiles or on the last one
                if completed_in_region == total or now - _last_eta_log >= 15 or completed_in_region % 5 == 0:
                    _last_eta_log = now
                    group_elapsed = now - _t0
                    remaining = total_cells_group - (processed + completed_in_region)
                    avg = group_elapsed / max(_done, 1)
                    eta = avg * remaining
                    total_proj = group_elapsed + eta
                    with out:
                        print(f"  > Group progress: {_done}/{total_cells_group} tiles "
                              f"| elapsed {_fmt_time(group_elapsed)} | total ~{_fmt_time(total_proj)} | remaining ~{_fmt_time(eta)}")

            # ETA final da regiao (garantido)
            elapsed = time.time() - _t0
            remaining = total_cells_group - (processed + completed_in_region)
            avg = elapsed / max(_done, 1)
            eta = avg * remaining
            total_proj = elapsed + eta
            with out:
                print(f"  > Group progress: {_done}/{total_cells_group} tiles "
                      f"| elapsed {_fmt_time(elapsed)} | total ~{_fmt_time(total_proj)} | remaining ~{_fmt_time(eta)}")

            # Salva progresso no workplan
            p = load_workplan()
            pct = (processed + completed_in_region) / total_cells_group if total_cells_group else 0
            for pj in p:
                if pj['id'] == job['id']:
                    pj['progress'] = f"{_done}/{total_cells_group} ({pct:.1%})"
            save_workplan(p)

        processed += total

        if tile_results:
            all_tile_results.extend(tile_results)
            with out:
                print(f"  Computing stats for {len(tile_results)} tiles...")
            generate_tile_stats(model_id, region_name, period, tile_results, fs=fs, campaign=campaign)
            generate_region_stats(model_id, region_name, period, tile_results, fs=fs, campaign=campaign)
            archive_job_on_gcs(job, tile_results, fs=fs)
        else:
            with out:
                print(f"  No tiles classified for {region_name}")
            delete_pending_job_gcs(model_id, region_name, period, fs=fs)

        _completed_cards += 1
        p = load_workplan()
        for pj in p:
            if pj['id'] == job['id']:
                pj['status'] = 'COMPLETED'
                pj['progress'] = '100%'
        save_workplan(p)

        with out:
            total_elapsed = time.time() - _t0
            print(f"  OK: {region_name} completed"
                  f" | region {_completed_cards}/{_total_cards}"
                  f" | group {_done}/{total_cells_group} tiles"
                  f" | elapsed {_fmt_time(total_elapsed)}")

    total_time = time.time() - _t0
    with out:
        print(f"  --- Group {model_id} | {period} done in {_fmt_time(total_time)} ---")


def _get_region_cells(region_name):
    """Busca celdas cim-world que intersectan la region."""
    import ee
    cim = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")

    if region_name.lower() == 'peru':
        region_fc = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
    else:
        region_fc = ee.FeatureCollection(CONFIG['asset_regions']).filter(ee.Filter.eq(REGION_NAME_PROPERTY, region_name))

    intersected = cim.filterBounds(region_fc.geometry())
    try:
        names = intersected.aggregate_array('name').getInfo()
        return [{'name': str(n)} for n in names]
    except Exception as e:
        print(f"[ERROR] Grid search failed: {e}")
        return []
