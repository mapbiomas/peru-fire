"""
Diagnóstico do CacheManager - Compara o que está no cache com o que o M1 procura.
Execute da pasta version_01:
    python scratch/debug_cache.py
"""
import os, sys, json, re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'src'))
sys.path.append(os.path.join(BASE_DIR, 'src', 'core'))

from M0_auth_config import CONFIG, GLOBAL_OPTS, _get_fs, mosaic_name

def main():
    fs = _get_fs()
    bucket = CONFIG['bucket']
    cache_path = f"gs://{bucket}/{CONFIG['gcs_cache']}/state.json"

    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO DO CACHE")
    print(f"Arquivo: {cache_path}")
    print(f"{'='*60}\n")

    try:
        with fs.open(cache_path, 'r') as f:
            state = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler cache: {e}")
        return

    print(f"⏰ Última atualização: {state.get('updated_at', 'N/A')}")
    print(f"🌎 País: {state.get('country', 'N/A')}\n")

    # --- GCS CHUNKS ---
    chunks = state.get('gcs_chunks', {})
    print(f"{'='*60}")
    print(f"GCS CHUNKS: {len(chunks)} chaves encontradas")
    print(f"{'='*60}")
    for key, bands in list(chunks.items())[:20]:
        print(f"  📦 {key}")
        print(f"      Bandas: {bands}")
    if len(chunks) > 20:
        print(f"  ... e mais {len(chunks)-20} chaves")

    # --- GEE ASSETS ---
    assets_m = state.get('assets_monthly', [])
    print(f"\n{'='*60}")
    print(f"GEE ASSETS MENSAIS: {len(assets_m)} encontrados")
    print(f"{'='*60}")
    for a in assets_m[:20]:
        print(f"  🛰️  {a}")
    if len(assets_m) > 20:
        print(f"  ... e mais {len(assets_m)-20} assets")

    # --- COMPARAÇÃO: O que o M1 procura vs o que tem ---
    print(f"\n{'='*60}")
    print(f"VERIFICAÇÃO DE COMPATIBILIDADE (M1 vs Cache)")
    print(f"{'='*60}")

    test_cases = [
        # (year, month, sensor, mosaic, band)
        (2025, 1,  'sentinel2', 'minnbr',        'blue'),
        (2025, 1,  'sentinel2', 'minnbr',        'dayOfYear'),
        (2025, 1,  'sentinel2', 'minnbr_buffer', 'blue'),
        (2025, 1,  'sentinel2', 'minnbr_buffer', 'dayOfYear'),
        (2026, 3,  'sentinel2', 'minnbr_buffer', 'blue'),
        (2026, 3,  'sentinel2', 'minnbr_buffer', 'green'),
    ]

    for (y, m, sensor, mosaic, band) in test_cases:
        m_name = mosaic_name(y, m, 'monthly', band=band, mosaic=mosaic, sensor=sensor)
        m_base = mosaic_name(y, m, 'monthly', mosaic=mosaic, sensor=sensor)
        
        gcs_bands = chunks.get(m_base.lower(), [])
        gcs_ok = band in gcs_bands
        
        gee_ok = m_name.lower() in assets_m
        
        gcs_sym = "✅" if gcs_ok else "❌"
        gee_sym = "✅" if gee_ok else "❌"
        
        print(f"\n  [{sensor}/{mosaic}/{band} - {y}_{m:02d}]")
        print(f"    m_name (GEE):  {m_name.lower()}")
        print(f"    m_base (GCS):  {m_base.lower()}")
        print(f"    GCS {gcs_sym}: bandas encontradas = {gcs_bands}")
        print(f"    GEE {gee_sym}: nome encontrado no cache = {gee_ok}")

    # --- SCAN DIRETO DO GCS PARA VERIFICAR ---
    print(f"\n{'='*60}")
    print(f"SCAN DIRETO DO GCS (Primeiros 5 arquivos de cada método)")
    print(f"{'='*60}")
    
    lib_base = CONFIG['gcs_library_images']
    for mosaic_method in ['minnbr', 'minnbr_buffer']:
        search_path = f"{bucket}/{lib_base}/sentinel2/monthly/{mosaic_method}"
        try:
            files = fs.find(search_path)
            tifs = [f for f in files if f.endswith('.tif')]
            print(f"\n  📂 {mosaic_method}: {len(tifs)} arquivos .tif")
            for tif in tifs[:5]:
                print(f"    - {tif.split('/')[-1]}")
        except Exception as e:
            print(f"  ❌ Erro ao escanear {mosaic_method}: {e}")

if __name__ == '__main__':
    main()
