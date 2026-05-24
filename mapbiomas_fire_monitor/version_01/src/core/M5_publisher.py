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


def generate_tile_stats(model_id, region, period, tile_results, fs=None, logger=None, campaign=None):
    """Guarda estadisticas por tile en CSV."""
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
    """Agrega estadisticas por region+periodo y alimenta consolidated."""
    if fs is None:
        fs = _get_fs()

    if not tile_results:
        return

    total_pixels = sum(tr.get('total_pixels', 0) for tr in tile_results)
    burned_pixels = sum(tr.get('burned_pixels', 0) for tr in tile_results)
    confidences = [tr.get('mean_confidence', 0) for tr in tile_results if tr.get('burned_pixels', 0) > 0]

    # Resolucion: sentinel2 = 10m
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

    # Guarda region_stats.csv (sobrescribe, es siempre la vista mas reciente)
    local_tmp = os.path.join(get_temp_dir('stats'), "stats_region.csv")
    fieldnames = list(row.keys())

    # Verifica si ya existe en GCS para hacer append
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

    # --- CONSOLIDATED (GERAL_STATS/) ---
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

    from M_gcs import mkdir
    dir_path = consolidated_path.rsplit('/', 1)[0]
    mkdir(dir_path)
    _gcs_upload(local_cons, consolidated_path)
    os.remove(local_cons)

    if logger:
        logger(f"    Region + consolidated stats updated")
        logger(f"    {region} {period}: {burned_area_km2:.2f} km2 ({burned_pixels:,} px burned)")


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
