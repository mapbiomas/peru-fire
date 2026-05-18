from M0_auth_config import CONFIG, _get_fs, _gcs_models_base
from M5_queue import load_queue, save_queue, make_job_id, tile_path, gcs_full
from M5_inference import load_model_from_gcs, classify_cell
from M5_publisher import merge_region_tiles, generate_tile_stats, generate_region_stats, upload_to_gee

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

    if 'publish' in phases:
        _run_publish(queue, out)


def _run_classification(queue, out, progress_callback=None):
    """Fase 1: clasifica tiles pendientes."""
    pending = [j for j in queue if j['status'] == 'PENDING' and j.get('enabled', True)]

    if not pending:
        with out:
            clear_output()
            display(HTML("<b style='color:green;'>No pending jobs to classify.</b>"))
        return

    with out:
        print("--- PHASE 1: CLASSIFICATION ---")

    for job in pending:
        job['status'] = 'RUNNING'
        save_queue(queue)

        try:
            with out:
                print(f"Starting: [{job['id']}]")

            _process_job(job, out, progress_callback)

            job['status'] = 'COMPLETED'
            job['progress'] = '100%'
            save_queue(queue)

            with out:
                print(f"OK: {job['id']} completed.")

        except Exception as e:
            job['status'] = 'FAILED'
            save_queue(queue)
            with out:
                print(f"ERROR in {job['id']}: {e}")
            break


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

        try:
            with out:
                print(f"Publishing: [{job['id']}]")

            mosaic_path = merge_region_tiles(model_id, region, period, fs=fs)

            if mosaic_path:
                job['progress'] = '50% (mosaic)'
                save_queue(queue)

            if job.get('upload_gee'):
                upload_to_gee(model_id, region, period, fs=fs)
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


def _process_job(job, out, progress_callback=None):
    """Procesa un trabajo: carga modelo, itera tiles, clasifica."""
    import ee
    from M0_auth_config import authenticate, _gcs_models_base

    fs = _get_fs()
    model_id = job['model']
    region_name = job['region']
    period = job['period']

    parts = period.split('_')
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 0

    # 1. Cargar modelo + metadatos
    model_dir = f"{CONFIG['bucket']}/{_gcs_models_base()}/{model_id}"
    model, meta, bands_config, norm_stats = load_model_from_gcs(model_dir, fs, logger=lambda m, l=None: out.append_display_data(m))

    # 2. Obtener grid de celdas de la region
    with out:
        print(f"  GEE grid for '{region_name}'...")

    cells = _get_region_cells(region_name)
    if not cells:
        raise ValueError(f"No cells found for {region_name}.")

    total = len(cells)
    with out:
        print(f"  {total} tiles to process.")

    # 3. Validar COGs antes de iterar tiles
    from M5_inference import build_band_paths
    band_paths = build_band_paths(bands_config, year, month)
    first_band = list(band_paths.keys())[0]
    with out:
        print(f"  Verifying COG paths for band '{first_band}'...")
        for b, p in band_paths.items():
            exists = "OK" if fs.exists(f"gs://{p}") else "MISSING"
            print(f"    {b}: gs://{p}  [{exists}]")
    first_full = f"gs://{band_paths[first_band]}"
    if not fs.exists(first_full):
        raise FileNotFoundError(f"COG not found at: {first_full}")

    # 4. Clasificar cada tile
    tile_results = []
    predict_fn = lambda x: model.predict(x, verbose=0)

    for i, cell in enumerate(cells):
        cell_id = cell['name']

        if i % 5 == 0:
            queue = load_queue()
            for qj in queue:
                if qj['id'] == job['id']:
                    qj['progress'] = f"{i}/{total} ({i/total:.1%})"
            save_queue(queue)

        # Checkpoint: salta si ya existe
        out_rel = tile_path(model_id, region_name, cell_id, period)
        out_full = gcs_full(out_rel)

        if fs.exists(out_full):
            if progress_callback:
                progress_callback(model_id, region_name, cell_id, i, total, 'skipped')
            continue

        with out:
            print(f"  [{i+1:03d}/{total}] {cell_id} ...")

        if progress_callback:
            progress_callback(model_id, region_name, cell_id, i, total, 'processing')

        try:
            stats = classify_cell(
                cell_id, predict_fn, bands_config, norm_stats,
                year, month, out_full, logger=lambda m, l=None: out.append_display_data(m)
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
                print(f"    [WARN] {cell_id} returned no stats (check logs above)")
            if progress_callback:
                progress_callback(model_id, region_name, cell_id, i, total, 'error')

    # 4. Generar estadisticas de los tiles
    if tile_results:
        with out:
            print(f"  Generating stats for {len(tile_results)} tiles...")
        generate_tile_stats(model_id, region_name, period, tile_results, fs=fs)
        generate_region_stats(model_id, region_name, period, tile_results, fs=fs)
    else:
        with out:
            print(f"  No tiles classified (all failed).")


def _get_region_cells(region_name):
    """Busca celdas cim-world que intersectan la region."""
    import ee
    cim = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")

    if region_name.lower() == 'peru':
        region_fc = ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME', 'Peru'))
    else:
        region_fc = ee.FeatureCollection(CONFIG['asset_regions']).filter(ee.Filter.eq('region_nam', region_name))

    intersected = cim.filterBounds(region_fc.geometry())
    try:
        names = intersected.aggregate_array('name').getInfo()
        return [{'name': str(n)} for n in names]
    except Exception as e:
        print(f"Error searching grid in GEE: {e}")
        return []
