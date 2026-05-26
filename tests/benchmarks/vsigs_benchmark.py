"""
vsigs_benchmark.py — Backend de benchmarks para comparar
download vs /vsigs/ na leitura e merge de COGs do GCS.

Uso:
    from vsigs_benchmark import (
        discover_periods, benchmark_read, benchmark_merge,
        compare_arrays, format_summary
    )
"""

import os
import time
import shutil
import subprocess
import tempfile
import numpy as np
from datetime import datetime


# ── RAM measurement ────────────────────────────────────────────────

def get_ram_mb():
    """Retorna uso de RAM do processo em MB."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def get_ram_delta_mb():
    """Retorna delta de RAM usando tracemalloc (stdlib, sempre disponivel)."""
    import tracemalloc
    if not tracemalloc.is_traced():
        tracemalloc.start()
        return 0.0
    current, _peak = tracemalloc.get_traced_memory()
    return current / (1024 * 1024)


# ── GCS helpers ─────────────────────────────────────────────────────

def _get_fs():
    from M0_auth_config import _get_fs as _fs
    from M_gcs import _get_fs as _mfs
    try:
        return _mfs()
    except Exception:
        return _fs()


def discover_periods(sensor='sentinel2'):
    """Lista periodos disponiveis com COGs no GCS.
    Retorna {period: {band: gcs_relative_path}}.
    """
    from M0_auth_config import CONFIG
    config = CONFIG
    bucket = config['bucket']
    prefix = config['gcs_library_images']

    fs = _get_fs()
    search = f"{bucket}/{prefix}/{sensor.upper()}/MONTHLY/minnbr"

    print(f"Buscando COGs em: gs://{search}/...")
    try:
        all_cogs = fs.glob(f"{search}/*/*.tif")
    except Exception as e:
        print(f"  [ERRO] fs.glob falhou: {e}")
        return {}

    # Agrupa por periodo
    periods = {}
    for cog_path in sorted(all_cogs):
        basename = os.path.basename(cog_path)
        if not basename.endswith('_cog.tif'):
            continue
        # Extrai dados do nome: image_peru_fire_sentinel2_minnbr_BLUE_YYYY_MM_cog.tif
        name_no_ext = basename.replace('_cog.tif', '')
        parts = name_no_ext.split('_')
        # Encontra a banda (penultimo ou ultimo antes da data?)
        # Padrao: image_COUNTRY_fire_SENSOR_MOSAIC_BAND_YYYY_MM
        # Banda esta na posicao 5 (0-indexed: image=0, country=1, fire=2, sensor=3, mosaic=4, band=5)
        if len(parts) < 7:
            continue
        band = parts[5]
        year = parts[6]
        month = parts[7] if len(parts) > 7 else '00'
        period = f"{year}_{month}"

        if period not in periods:
            periods[period] = {}
        periods[period][band] = cog_path

    return dict(sorted(periods.items()))


# ── Benchmark: single COG read ─────────────────────────────────────

def benchmark_read_download(cog_rel_path, fs=None):
    """Benchmark: baixa o COG, le com rasterio. Retorna dict de metricas."""
    if fs is None:
        fs = _get_fs()

    from M0_auth_config import CONFIG
    bucket = CONFIG['bucket']
    gcs_path = f"gs://{bucket}/{cog_rel_path}" if not cog_rel_path.startswith('gs://') else cog_rel_path
    rel = cog_rel_path.replace(f"{bucket}/", '') if bucket in cog_rel_path else cog_rel_path

    tmpdir = tempfile.mkdtemp(prefix='bench_dl_')
    local_path = os.path.join(tmpdir, os.path.basename(rel))
    gcs_uri = f"gs://{bucket}/{rel}" if not rel.startswith('gs://') else rel

    metrics = {'method': 'download', 'file': os.path.basename(rel)}

    # Download
    ram_before = get_ram_mb()
    t0 = time.time()
    try:
        subprocess.run(
            ['gsutil', 'cp', gcs_uri, local_path],
            check=True, capture_output=True, text=True, timeout=120
        )
    except subprocess.CalledProcessError as e:
        shutil.rmtree(tmpdir)
        raise RuntimeError(f"Download falhou: {e.stderr}")
    metrics['time_download_s'] = round(time.time() - t0, 2)
    metrics['ram_delta_download_mb'] = round(get_ram_mb() - ram_before, 1)
    metrics['file_size_mb'] = round(os.path.getsize(local_path) / (1024 * 1024), 1)

    # Leitura com rasterio
    import rasterio
    t0 = time.time()
    with rasterio.open(local_path) as src:
        arr = src.read(1)
        metrics['shape'] = arr.shape
        metrics['dtype'] = str(arr.dtype)
    metrics['time_read_s'] = round(time.time() - t0, 2)
    metrics['ram_delta_read_mb'] = round(get_ram_mb() - ram_before, 1)

    # Estatisticas
    valid = arr != src.nodata if src.nodata is not None else np.ones_like(arr, dtype=bool)
    metrics['pixels_valid'] = int(valid.sum())
    metrics['pixels_total'] = int(arr.size)
    metrics['pct_valid'] = round(metrics['pixels_valid'] / metrics['pixels_total'] * 100, 1) if metrics['pixels_total'] else 0
    metrics['min'] = float(arr[valid].min()) if metrics['pixels_valid'] else None
    metrics['max'] = float(arr[valid].max()) if metrics['pixels_valid'] else None
    metrics['mean'] = round(float(arr[valid].mean()), 2) if metrics['pixels_valid'] else None

    shutil.rmtree(tmpdir)
    return metrics, arr


def benchmark_read_vsigs(cog_rel_path):
    """Benchmark: le o COG via /vsigs/ com rasterio. Retorna dict de metricas."""
    vsi_path = f"/vsigs/{cog_rel_path}" if not cog_rel_path.startswith('/vsigs/') else cog_rel_path

    metrics = {'method': '/vsigs/', 'file': os.path.basename(cog_rel_path)}

    ram_before = get_ram_mb()
    t0 = time.time()

    import rasterio
    with rasterio.open(vsi_path) as src:
        arr = src.read(1)
        metrics['shape'] = arr.shape
        metrics['dtype'] = str(arr.dtype)

    metrics['time_read_s'] = round(time.time() - t0, 2)
    metrics['ram_delta_mb'] = round(get_ram_mb() - ram_before, 1)

    valid = arr != src.nodata if src.nodata is not None else np.ones_like(arr, dtype=bool)
    metrics['pixels_valid'] = int(valid.sum())
    metrics['pixels_total'] = int(arr.size)
    metrics['pct_valid'] = round(metrics['pixels_valid'] / metrics['pixels_total'] * 100, 1) if metrics['pixels_total'] else 0
    metrics['min'] = float(arr[valid].min()) if metrics['pixels_valid'] else None
    metrics['max'] = float(arr[valid].max()) if metrics['pixels_valid'] else None
    metrics['mean'] = round(float(arr[valid].mean()), 2) if metrics['pixels_valid'] else None

    return metrics, arr


def compare_arrays(arr1, arr2, label1='download', label2='/vsigs/'):
    """Compara dois arrays pixel a pixel. Retorna dict de comparacao."""
    result = {
        'identical': False,
        'same_shape': arr1.shape == arr2.shape,
        'same_dtype': arr1.dtype == arr2.dtype,
    }
    if result['same_shape']:
        result['identical'] = bool(np.array_equal(arr1, arr2))
        if not result['identical']:
            diff = arr1.astype(np.float64) - arr2.astype(np.float64)
            result['max_diff'] = float(np.abs(diff).max())
            result['mean_diff'] = round(float(np.abs(diff).mean()), 6)
            result['pct_different'] = round(float((diff != 0).mean()) * 100, 4)
    return result


# ── Benchmark: M2 merge simulation ─────────────────────────────────

def _check_gdal():
    """Verifica se gdalbuildvrt e gdal_translate estao disponiveis."""
    for cmd in ['gdalbuildvrt', 'gdal_translate']:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(f"{cmd} nao encontrado. Instale GDAL.")


def _run_cmd(args, label='comando', timeout=300):
    """Executa comando com timeout. Levanta RuntimeError em caso de falha."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, check=True, timeout=timeout)
        return r
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{label} falhou: {e.stderr.strip() if e.stderr else e.stdout.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{label} excedeu timeout ({timeout}s)")


def benchmark_merge_download(band_uris, fs=None, num_threads=2):
    """Simula merge M2 metodo ATUAL: download -> VRT local -> gdal_translate COG."""
    from M0_auth_config import CONFIG
    bucket = CONFIG['bucket']

    _check_gdal()
    if fs is None:
        fs = _get_fs()

    tmpdir = tempfile.mkdtemp(prefix='bench_m2_dl_')
    out_cog = os.path.join(tmpdir, 'mosaic_download.tif')
    metrics = {'method': 'M2 download', 'num_bands': len(band_uris), 'num_threads': num_threads}

    try:
        # Etapa 1: Download
        local_paths = []
        t0 = time.time()
        for uri in band_uris:
            rel = uri.replace(f"{bucket}/", '') if bucket in uri else uri
            local = os.path.join(tmpdir, os.path.basename(rel))
            subprocess.run(
                ['gsutil', 'cp', f"gs://{rel}", local],
                check=True, capture_output=True, text=True, timeout=120
            )
            local_paths.append(local)
        metrics['time_download_s'] = round(time.time() - t0, 2)

        # Etapa 2: gdalbuildvrt
        vrt_path = os.path.join(tmpdir, 'mosaic.vrt')
        t0 = time.time()
        _run_cmd(['gdalbuildvrt', '-q', vrt_path] + local_paths, label='gdalbuildvrt (download)')
        metrics['time_vrt_s'] = round(time.time() - t0, 2)

        # Etapa 3: gdal_translate
        t0 = time.time()
        _run_cmd([
            'gdal_translate', '-q', '-of', 'COG',
            '-co', 'COMPRESS=LZW', '-co', 'PREDICTOR=2',
            '-co', f'NUM_THREADS={num_threads}', '-co', 'BIGTIFF=YES',
            vrt_path, out_cog
        ], label='gdal_translate (download)')
        metrics['time_translate_s'] = round(time.time() - t0, 2)

        metrics['output_size_mb'] = round(os.path.getsize(out_cog) / (1024 * 1024), 1)
        metrics['total_time_s'] = round(
            metrics['time_download_s'] + metrics['time_vrt_s'] + metrics['time_translate_s'], 2
        )

        # Le o COG de saida para comparacao
        import rasterio
        with rasterio.open(out_cog) as src:
            out_arr = src.read()

    finally:
        shutil.rmtree(tmpdir)

    return metrics, out_arr


def benchmark_merge_vsigs(band_uris, num_threads=None):
    """Simula merge M2 metodo OTIMIZADO: VRT direto do GCS -> gdal_translate COG."""
    from M0_auth_config import CONFIG
    bucket = CONFIG['bucket']

    _check_gdal()
    if num_threads is None:
        num_threads = os.cpu_count() or 4

    tmpdir = tempfile.mkdtemp(prefix='bench_m2_vs_')
    out_cog = os.path.join(tmpdir, 'mosaic_vsigs.tif')
    metrics = {'method': 'M2 /vsigs/', 'num_bands': len(band_uris), 'num_threads': num_threads}

    try:
        vsi_paths = []
        for uri in band_uris:
            rel = uri.replace(f"{bucket}/", '') if bucket in uri else uri
            vsi_paths.append(f"/vsigs/{rel}")

        # Etapa 1: gdalbuildvrt direto do GCS (sem download)
        vrt_path = os.path.join(tmpdir, 'mosaic.vrt')
        t0 = time.time()
        try:
            _run_cmd(['gdalbuildvrt', '-q', vrt_path] + vsi_paths, label='gdalbuildvrt (/vsigs/)')
        except RuntimeError as e:
            # Colab: GDAL /vsigs/ nao tem driver GCS
            metrics['time_vrt_s'] = round(time.time() - t0, 2)
            metrics['time_translate_s'] = 0
            metrics['output_size_mb'] = 0
            metrics['total_time_s'] = 0
            metrics['gdal_vsigs_error'] = str(e)[:200]
            shutil.rmtree(tmpdir)
            return metrics, None
        metrics['time_vrt_s'] = round(time.time() - t0, 2)

        # Etapa 2: gdal_translate
        t0 = time.time()
        try:
            _run_cmd([
                'gdal_translate', '-q', '-of', 'COG',
                '-co', 'COMPRESS=LZW', '-co', 'PREDICTOR=2',
                '-co', f'NUM_THREADS={num_threads}', '-co', 'BIGTIFF=YES',
                vrt_path, out_cog
            ], label='gdal_translate (/vsigs/)')
        except RuntimeError as e:
            metrics['time_translate_s'] = round(time.time() - t0, 2)
            metrics['output_size_mb'] = 0
            metrics['total_time_s'] = 0
            metrics['gdal_vsigs_error'] = str(e)[:200]
            shutil.rmtree(tmpdir)
            return metrics, None

        metrics['time_translate_s'] = round(time.time() - t0, 2)
        metrics['output_size_mb'] = round(os.path.getsize(out_cog) / (1024 * 1024), 1)
        metrics['total_time_s'] = round(metrics['time_vrt_s'] + metrics['time_translate_s'], 2)

        import rasterio
        with rasterio.open(out_cog) as src:
            out_arr = src.read()

    finally:
        shutil.rmtree(tmpdir)

    return metrics, out_arr


# ── Formatting ──────────────────────────────────────────────────────

def format_summary(results):
    """Formata dict de resultados em tabela Markdown."""
    lines = []
    lines.append("| Métrica | Download | /vsigs/ | Ganho |")
    lines.append("|---------|----------|---------|-------|")
    dl = results.get('read_download', {})
    vs = results.get('read_vsigs', {})

    if dl and vs:
        dl_time = dl.get('time_read_s', 0)
        vs_time = vs.get('time_read_s', 0)
        ratio = round(dl_time / vs_time, 1) if vs_time > 0 else float('inf')
        lines.append(f"| Tempo leitura 1 COG | {dl_time}s | {vs_time}s | {ratio}x |")

        dl_dl = dl.get('time_download_s', 0)
        lines.append(f"| Tempo download | {dl_dl}s | 0s (sem download) | - |")

        dl_ram = dl.get('ram_delta_download_mb', 0)
        lines.append(f"| RAM cache disco | +{dl_ram:.0f} MB | 0 MB | infinito |")

        lines.append(f"| Pixels identicos | - | {results.get('pixels_identical', '?')} | - |")

    m2_dl = results.get('merge_download', {})
    m2_vs = results.get('merge_vsigs', {})
    if m2_dl and m2_vs:
        dl_total = m2_dl.get('total_time_s', 0)
        vs_total = m2_vs.get('total_time_s', 0)
        if 'gdal_vsigs_error' in m2_vs:
            lines.append(f"| Merge M2 | {dl_total}s | ERRO GDAL /vsigs/ | - |")
            lines.append(f"| | | {m2_vs['gdal_vsigs_error']} | |")
        elif vs_total > 0:
            ratio = round(dl_total / vs_total, 1)
            lines.append(f"| Merge M2 ({m2_dl.get('num_bands','?')} bandas) | {dl_total}s | {vs_total}s | {ratio}x |")
            lines.append(f"| NUM_THREADS | {m2_dl.get('num_threads','?')} | {m2_vs.get('num_threads','?')} | |")

    return '\n'.join(lines)
