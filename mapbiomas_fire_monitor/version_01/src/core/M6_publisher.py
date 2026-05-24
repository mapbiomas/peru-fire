import os
import csv
import json
import time
import shutil
import numpy as np
import rasterio
from rasterio.merge import merge
from M0_auth_config import CONFIG, _get_fs, _gcs_download, _gcs_upload, get_temp_dir
from M5_workplan import (
    classified_tiles_dir, classified_region_dir, region_path,
    tile_stats_path, region_stats_path, consolidated_stats_path,
    tile_path, gcs_full
)
from M_cache import CacheManager


def _fmt_time(s):
    h, r = divmod(int(s), 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def merge_region_tiles(model_id, region, period, fs=None, logger=None, campaign=None):
    """Junta todos los tiles de una region en un mosaico regional."""
    if fs is None:
        fs = _get_fs()

    tiles_dir = gcs_full(classified_tiles_dir(model_id, campaign))
    pattern = f"tile_{region}_"
    tile_paths = sorted([
        p for p in fs.glob(f"{tiles_dir}/*.tif")
        if pattern in os.path.basename(p) and not p.endswith('.aux.xml')
    ])

    if not tile_paths:
        if logger:
            logger(f"    [WARN] No tiles found for {region}")
        return None

    if logger:
        logger(f"    Merging {len(tile_paths)} tiles for {region}...")

    out_gcs = gcs_full(region_path(model_id, region, period, campaign))
    tmpdir = os.path.join(get_temp_dir('mosaics'), f"merge_{model_id}_{region}_{period}_{int(time.time())}")

    try:
        local_tiles = []
        for i, tp in enumerate(tile_paths):
            local = os.path.join(tmpdir, f"tile_{i:04d}.tif")
            _gcs_download(tp, local)
            local_tiles.append(local)

        src_files = [rasterio.open(t) for t in local_tiles]
        mosaic, out_transform = merge(src_files)
        out_meta = src_files[0].meta.copy()
        for src in src_files:
            src.close()

        out_meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "compress": 'lzw'
        })

        mosaic_local = os.path.join(tmpdir, "mosaic.tif")
        with rasterio.open(mosaic_local, 'w', **out_meta) as dest:
            dest.write(mosaic)

        _gcs_upload(mosaic_local, out_gcs)

        if logger:
            logger(f"    Mosaic saved: {out_gcs}")
        return out_gcs

    finally:
        shutil.rmtree(tmpdir)


def compute_region_stats_from_mosaic(model_id, region, period, fs=None, logger=None, campaign=None):
    """Le o mosaico e computa estatisticas da regiao."""
    if fs is None:
        fs = _get_fs()

    mosaic_gcs = gcs_full(region_path(model_id, region, period, campaign))
    local_tmp = os.path.join(get_temp_dir('stats'), "mosaic_stats.tif")
    try:
        _gcs_download(mosaic_gcs, local_tmp)
    except Exception:
        if logger:
            logger(f"    [WARN] Mosaic not found for stats: {mosaic_gcs}")
        return None

    with rasterio.open(local_tmp) as src:
        class_band = src.read(1)
        prob_band = src.read(2)

    os.remove(local_tmp)

    total_valid = int((class_band >= 0).sum())
    burned_mask = class_band > 0.5
    n_burned = int(burned_mask.sum())

    resolution_m = 10
    pixel_area_m2 = resolution_m ** 2
    burned_area_km2 = n_burned * pixel_area_m2 / 1_000_000
    total_area_km2 = total_valid * pixel_area_m2 / 1_000_000 if total_valid else 0

    if n_burned > 0:
        mean_conf = float(prob_band[burned_mask].mean())
    else:
        mean_conf = 0.0

    row = {
        'model_id': model_id,
        'region': region,
        'period': period,
        'tiles_total': 0,
        'tiles_processed': 1,
        'total_pixels': total_valid,
        'burned_pixels': n_burned,
        'burned_area_km2': f"{burned_area_km2:.2f}",
        'total_area_km2': f"{total_area_km2:.2f}",
        'burned_percentage': f"{(n_burned / total_valid * 100):.2f}" if total_valid else "0.00",
        'mean_confidence': f"{mean_conf:.4f}",
    }
    return row


def update_consolidated_stats(row, fs=None, logger=None):
    """Adiciona/atualiza uma linha no consolidated_stats.csv."""
    from M_gcs import mkdir

    consolidated_path = gcs_full(consolidated_stats_path())
    fieldnames = list(row.keys())

    cons_rows = []
    try:
        local_cons = os.path.join(get_temp_dir('stats'), "consolidated.csv")
        _gcs_download(consolidated_path, local_cons)
        with open(local_cons, 'r') as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r['region'] == row['region'] and r['period'] == row['period'] and r['model_id'] == row['model_id']:
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
        logger(f"    Consolidated stats updated for {row['model_id']} | {row['region']} | {row['period']}")


def upload_to_gee(model_id, region, period, fs=None, logger=None, campaign=None, scale=10):
    """Envia el mosaico regional CLASSIFIED_REGION como ImageCollection a GEE."""
    import ee

    if fs is None:
        fs = _get_fs()

    mosaic_gcs = gcs_full(region_path(model_id, region, period, campaign))
    gcs_uri = f"gs://{mosaic_gcs}"

    if not fs.exists(mosaic_gcs):
        if logger:
            logger(f"    [WARN] Mosaic not found for GEE upload")
        return False

    if logger:
        logger(f"    Submitting GEE import task...")

    img = ee.Image.loadGeoTIFF(gcs_uri)

    parent = f"{CONFIG['asset_monitor_base']}/LIBRARY_CLASSIFICATIONS/REGIONAL/{model_id}"
    try:
        ee.data.createAsset({'type': 'ImageCollection'}, parent)
    except Exception:
        pass

    asset_id = f"{parent}/{region}_{period}"
    task = ee.batch.Export.image.toAsset(
        image=img,
        description=f"PUBLISH_{model_id}_{region}_{period}",
        assetId=asset_id,
        scale=scale,
        maxPixels=1e13,
        pyramidingPolicy={'.default': 'mean'}
    )
    task.start()

    if logger:
        logger(f"    GEE task submitted! Asset: {asset_id}")
    return True


def discover_classified_groups(fs=None, logger=None):
    """Scan GCS e descobre grupos (modelo, regiao, periodo) com tiles classificados."""
    if fs is None:
        fs = _get_fs()

    base = gcs_full(classified_tiles_dir('', ''))
    base = base.replace('/CLASSIFIED_TILES', '')
    prefix = base.rsplit('/', 1)[0] if base.endswith('/') else base

    groups = set()
    try:
        all_tiles = fs.glob(f"{prefix}/*/CLASSIFIED_TILES/tile_*.tif")
    except Exception as e:
        if logger:
            logger(f"    [ERROR] scanning GCS: {e}")
        return groups

    for tp in all_tiles:
        basename = os.path.basename(tp)
        parts = basename.replace('tile_', '', 1).split('_')
        if len(parts) < 3:
            continue
        region = parts[0]
        period = parts[-1].replace('.tif', '')
        model_dir = tp.split('/CLASSIFIED_TILES')[0]
        model_id = os.path.basename(model_dir)
        groups.add((model_id, region, period))

    return groups


def run_m6_publish(upload_gee=True, logger=None):
    """Entry point M6: scan tiles, mosaic, stats, GEE upload."""
    if logger is None:
        logger = print

    fs = _get_fs()
    groups = discover_classified_groups(fs=fs, logger=logger)

    if not groups:
        logger("  No classified tiles found in GCS.")
        return

    logger(f"  Found {len(groups)} classified groups.")
    groups = sorted(groups)
    _t0 = time.time()

    for idx, (model_id, region, period) in enumerate(groups):
        campaign = ''
        logger(f"\n  [{idx+1}/{len(groups)}] {model_id} | {region} | {period}")

        mosaic_exists = False
        mosaic_gcs = gcs_full(region_path(model_id, region, period, campaign))
        if fs.exists(mosaic_gcs):
            mosaic_exists = True
            logger(f"    Mosaic already exists, skipping merge.")

        if not mosaic_exists:
            mosaic_path = merge_region_tiles(model_id, region, period, fs=fs, logger=logger, campaign=campaign)
            if not mosaic_path:
                logger(f"    [WARN] No tiles to mosaic for {region}, skipping stats.")
                continue

        row = compute_region_stats_from_mosaic(model_id, region, period, fs=fs, logger=logger, campaign=campaign)
        if row:
            update_consolidated_stats(row, fs=fs, logger=logger)

        if upload_gee:
            upload_to_gee(model_id, region, period, fs=fs, logger=logger, campaign=campaign)

    total = time.time() - _t0
    logger(f"\n  --- M6 publish done in {_fmt_time(total)} ---")
