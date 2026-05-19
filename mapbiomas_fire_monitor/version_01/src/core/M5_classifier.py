import os
from collections import defaultdict
from M0_auth_config import CONFIG, _get_fs, _gcs_models_base, _gcs_download
from M_cache import CacheManager
from M5_queue import load_queue, save_queue, make_job_id, tile_path, gcs_full
from M5_inference import load_model_from_gcs, classify_cell_with_cogs, build_band_paths
from M5_publisher import merge_region_tiles, generate_tile_stats, generate_region_stats, upload_to_gee
from M_regions import REGION_NAME_PROPERTY

VALID_PHASES = ['classification', 'publish']

def run_m5_queue(phases=None, progress_callback=None):
    """Motor de procesamiento M5.

    Args:
        phases: lista con fases a ejecutar.
            'classification' — clasifica tiles pendientes
            'publish'        — mosaicado + stats + upload GEE
        progress_callback: opcional, llamado tras cada tile.
            firma: progress_callback(model, region, cell_id, i, total, status)
    """
    if phases is None:
        phases = ['classification', 'publish']

    if not isinstance(phases, list) or not any(p in VALID_PHASES for p in phases):
        print(f"Warning: Invalid 'phases' argument. Use {VALID_PHASES}.")
        return

    from IPython.display import display, HTML, clear_output
    import ipywidgets as widgets

    out = widgets.Output()
    display(out)

    queue = load_queue()

    if 'classification' in phases:
        _run_classification(queue, out, progress_callback)
        queue = load_queue()

    if 'publish' in phases:
        _run_publish(queue, out)


def _run_classification(queue, out, progress_callback=None):
    """Fase 1: agrupa jobs por (modelo, periodo) y clasifica compartiendo COGs."""
    pending = [j for j in queue if j['status'] == 'PENDING' and j.get('enabled', True)]

    if not pending:
        with out:
            clear_output()
            display(HTML("<b style='color:green;'>No pending jobs to classify.</b>"))
        return

    with out:
        print("--- PHASE 1: CLASSIFICATION ---")

    groups = defaultdict(list)
    for j in pending:
        groups[(j['model'], j['period'])].append(j)

    for (model_id, period), group in groups.items():
        with out:
            print(f"\nGroup: model={model_id} | period={period} | {len(group)} region(s)")

        try:
            _process_period(model_id, period, group, out, progress_callback)
        except Exception as e:
            import traceback
            with out:
                print(f"[FATAL] Group {model_id} | {period} failed:")
                traceback.print_exc()
            q = load_queue()
            for job in group:
                for qj in q:
                    if qj['id'] == job['id']:
                        qj['status'] = 'FAILED'
            save_queue(q)
            continue


def _run_publish(queue, out):
    """Fase 2: mosaicado, estadisticas y upload GEE."""
    to_publish = [j for j in queue if j['status'] == 'COMPLETED' and j.get('enabled', True)]

    if not to_publish:
        with out:
            print("No COMPLETED jobs to publish.")
        return

    with out:
        print("--- PHASE 2: PUBLISH (mosaic + stats + GEE) ---")

    fs = _get_fs()
    for job in to_publish:
        model_id = job['model']
        region = job['region']
        period = job['period']
        campaign = job.get('campaign', '')

        try:
            with out:
                print(f"Publishing: [{job['id']}]")

            mosaic_path = merge_region_tiles(model_id, region, period, fs=fs, campaign=campaign)

            if not mosaic_path:
                job['status'] = 'FAILED'
                job['progress'] = 'error: no mosaic generated'
                save_queue(queue)
                with out:
                    print(f"  No tiles to mosaic for {job['id']}, marking FAILED.")
                continue

            job['progress'] = '50% (mosaic)'
            save_queue(queue)

            if job.get('upload_gee'):
                upload_to_gee(model_id, region, period, fs=fs, campaign=campaign, scale=10)
                job['progress'] = '100% (published)'
            else:
                job['progress'] = '100% (mosaic)'

            job['status'] = 'FINISHED'
            save_queue(queue)

            with out:
                print(f"OK: {job['id']} finished.")

        except Exception as e:
            with out:
                print(f"ERROR publishing {job['id']}: {e}")


def _process_period(model_id, period, group_jobs, out, progress_callback=None):
    """Procesa todas las regiones de un (modelo, periodo) compartiendo COGs.

    Los COGs se descargan una unica vez y se reusan para todos los tiles
    de todas las regiones del grupo.
    """
    import ee
    from M0_auth_config import authenticate, _gcs_models_base, get_temp_dir

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

    model_dir = f"{CONFIG['bucket']}/{_gcs_models_base()}/{model_id}"
    with out:
        print(f"    Model dir: gs://{model_dir}/")
    model, meta, bands_config, norm_stats = load_model_from_gcs(
        model_dir, fs, logger=lambda m, l=None: out.append_display_data(m)
    )
    predict_fn = lambda x: model.predict(x, verbose=0)

    # 2. Construir paths e verificar COGs via CacheManager primeiro
    band_paths = build_band_paths(bands_config, year, month)
    bands_sorted = sorted(bands_config.keys())

    period_type = 'monthly' if month else 'annually'
    state = CacheManager.get_state()
    known_cogs = set(state.get(f'cogs_{period_type}', []))

    with out:
        print(f"  Verifying COG paths for period '{period}'...")
    for b, p in band_paths.items():
        # Extrai o nome base (ex: image_peru_fire_sentinel2_minnbr_2025_08_blue)
        cog_basename = os.path.basename(p).lower().replace('_cog.tif', '')
        in_cache = cog_basename in known_cogs
        exists = "OK (cache)" if in_cache else ("OK" if fs.exists(f"gs://{p}") else "MISSING")
        with out:
            print(f"    {b}: gs://{p}  [{exists}]")

    first_full = f"gs://{band_paths[bands_sorted[0]]}"
    first_basename = os.path.basename(first_full).lower().replace('_cog.tif', '')
    if first_basename not in known_cogs and not fs.exists(first_full):
        raise FileNotFoundError(f"COG not found at: {first_full}")

    # 3. Download de COGs (uma vez para o periodo inteiro)
    cogs = {}
    try:
        for b in bands_sorted:
            cog_full = f"gs://{band_paths[b]}"
            local_path = os.path.join(get_temp_dir(), os.path.basename(band_paths[b]))
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                with out:
                    print(f"    {b}: using cached {os.path.basename(band_paths[b])}")
            else:
                if os.path.exists(local_path):
                    os.remove(local_path)
                with out:
                    print(f"  Downloading COG: {os.path.basename(band_paths[b])}...")
                _gcs_download(cog_full, local_path)
                sz = os.path.getsize(local_path)
                if sz == 0:
                    raise IOError(f"Downloaded COG is empty (0 bytes): {cog_full}")
                with out:
                    print(f"    {b}: OK ({sz} bytes)")
            cogs[b] = local_path

        with out:
            print(f"  COGs ready ({len(cogs)} bands).")

        all_tile_results = []

        # 4. Pre-computar celdas de todas as regiões para progresso cumulativo
        region_cells_map = {}
        for job in group_jobs:
            region_cells_map[job['region']] = _get_region_cells(job['region'])
        total_cells_group = sum(len(cells) for cells in region_cells_map.values())
        processed = 0

        # 5. Procesar cada region del grupo
        for job_idx, job in enumerate(group_jobs):
            region_name = job['region']

            job['status'] = 'RUNNING'
            q = load_queue()
            for qj in q:
                if qj['id'] == job['id']:
                    qj['status'] = 'RUNNING'
            save_queue(q)

            with out:
                print(f"\n  Region [{job_idx+1}/{len(group_jobs)}]: {region_name}")

            cells = region_cells_map[region_name]
            if not cells:
                with out:
                    print(f"  [WARN] No cells found for {region_name}.")
                continue

            total = len(cells)
            with out:
                print(f"  {total} tiles to process.")

            tile_results = []

            for i, cell in enumerate(cells):
                cell_id = cell['name']

                if i % 5 == 0:
                    q = load_queue()
                    pct = (processed + i) / total_cells_group if total_cells_group else 0
                    for qj in q:
                        if qj['id'] == job['id']:
                            qj['progress'] = f"{processed + i}/{total_cells_group} ({pct:.1%})"
                    save_queue(q)

                out_rel = tile_path(model_id, region_name, cell_id, period, campaign)
                out_full = gcs_full(out_rel)

                if fs.exists(out_full):
                    if progress_callback:
                        progress_callback(model_id, region_name, cell_id, i, total, 'skipped')
                    continue

                with out:
                    print(f"  [{processed+i+1:03d}/{total_cells_group}] {cell_id} ...")

                if progress_callback:
                    progress_callback(model_id, region_name, cell_id, i, total, 'processing')

                try:
                    stats = classify_cell_with_cogs(
                        cell_id, predict_fn, bands_config, norm_stats,
                        out_full, cogs,
                        logger=lambda m, l=None: out.append_display_data(m)
                    )
                except Exception as e:
                    with out:
                        print(f"    [ERROR] {cell_id}: {e}")
                    stats = None

                if stats:
                    stats['tile_id'] = cell_id
                    stats['region'] = region_name
                    stats['period'] = period
                    tile_results.append(stats)
                    if progress_callback:
                        progress_callback(model_id, region_name, cell_id, i, total, 'done')
                else:
                    with out:
                        print(f"    [WARN] {cell_id} returned no stats")
                    if progress_callback:
                        progress_callback(model_id, region_name, cell_id, i, total, 'error')

            processed += total

            if tile_results:
                all_tile_results.extend(tile_results)
                with out:
                    print(f"  Generating stats for {len(tile_results)} tiles...")
                generate_tile_stats(model_id, region_name, period, tile_results, fs=fs, campaign=campaign)
                generate_region_stats(model_id, region_name, period, tile_results, fs=fs, campaign=campaign)
            else:
                with out:
                    print(f"  No tiles classified for {region_name}.")

            q = load_queue()
            for qj in q:
                if qj['id'] == job['id']:
                    qj['status'] = 'COMPLETED'
                    qj['progress'] = '100%'
            save_queue(q)

            with out:
                print(f"  OK: {region_name} completed.")

    finally:
        # 5. Limpar COGs locais
        removed = 0
        for b, local_path in cogs.items():
            if os.path.exists(local_path):
                os.remove(local_path)
                removed += 1
        with out:
            print(f"  Cleaned up {removed} local COG(s).")


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
        print(f"Error searching grid in GEE: {e}")
        return []
