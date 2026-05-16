"""
Script para migrar amostras da raiz de LIBRARY_SAMPLES para uma pasta de CAMPANHA.
Padrão: .../LIBRARY_SAMPLES/samples_XXXX -> .../LIBRARY_SAMPLES/monitor_01/samples_XXXX
"""
import ee
import os
import sys
import subprocess

# Adiciona o diretório src/core ao path para permitir imports
current_dir = os.path.dirname(os.path.abspath(__file__)) # scratch
version_dir = os.path.dirname(current_dir) # version_01
core_path = os.path.join(version_dir, 'src', 'core')
if core_path not in sys.path:
    sys.path.append(core_path)

from M0_auth_config import authenticate, CONFIG, GLOBAL_OPTS

# --- CONFIGURAÇÃO ---
CAMPAIGN = 'monitor_01'
DRY_RUN = False  # Executando de fato conforme solicitado

def migrate_gee():
    print(f"\n--- Migrando Assets GEE para campanha: {CAMPAIGN} ---")
    base_path = CONFIG['asset_monitor_base'] + '/LIBRARY_SAMPLES'
    campaign_path = f"{base_path}/{CAMPAIGN}"
    
    # Garante que a pasta da campanha existe
    try:
        ee.data.createAsset({'type': 'FOLDER'}, campaign_path)
        print(f"DONE: Pasta criada: {campaign_path}")
    except:
        print(f"INFO: Pasta ja existe ou erro ao criar: {campaign_path}")

    # Lista assets na raiz
    assets = ee.data.listAssets(base_path)['assets']
    for a in assets:
        asset_id = a['id']
        asset_name = asset_id.split('/')[-1]
        
        # Filtra apenas o que parece ser amostra (samples_XXXX) e ignora a pasta da campanha
        if asset_name.startswith('samples_') and asset_name != CAMPAIGN:
            dest_id = f"{campaign_path}/{asset_name}"
            print(f"MOVE: [GEE] Movendo: {asset_name} -> {CAMPAIGN}/")
            if not DRY_RUN:
                try:
                    ee.data.renameAsset(asset_id, dest_id)
                    print(f"   SUCCESS")
                except Exception as e:
                    print(f"   ERROR: {e}")

def migrate_gcs():
    print(f"\n--- Migrando Arquivos GCS para campanha: {CAMPAIGN} ---")
    from M_cache import _get_fs
    fs = _get_fs()
    bucket = CONFIG['bucket']
    base_path = f"{bucket}/{CONFIG['gcs_library_samples']}"
    
    # Lista tudo na pasta e filtra no Python usando gcsfs
    try:
        all_items = fs.ls(base_path)
        print(f"DEBUG: Encontrados {len(all_items)} itens no total no GCS.")
        # Filtra apenas arquivos CSV na raiz (ignorando a pasta da campanha)
        files = [f for f in all_items if f.endswith('.csv')]
        print(f"DEBUG: Encontrados {len(files)} arquivos .csv para mover.")
    except Exception as e:
        print(f"ERROR: Erro ao listar GCS: {e}")
        files = []

    if not files:
        print("INFO: Nenhuma amostra .csv encontrada na raiz do GCS.")
        return

    for f in files:
        f_name = f.split('/')[-1]
        dest = f"{bucket}/{CONFIG['gcs_library_samples']}/{CAMPAIGN}/{f_name}"
        print(f"MOVE: [GCS] Movendo: {f_name} -> {CAMPAIGN}/")
        if not DRY_RUN:
            try:
                fs.mv(f, dest)
                print(f"   SUCCESS")
            except Exception as e:
                print(f"   ERROR: {e}")

if __name__ == "__main__":
    authenticate()
    print(f"Modo: {'DRY_RUN (Apenas Simulação)' if DRY_RUN else 'EXECUÇÃO REAL'}")
    migrate_gee()
    migrate_gcs()
    print("\nPronto!")
