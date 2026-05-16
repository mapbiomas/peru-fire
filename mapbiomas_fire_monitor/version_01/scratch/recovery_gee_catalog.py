import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate

BASE_PATH = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES'

DRY_RUN = False # Mude para False para EXECUTAR DE VERDADE

def consolidate():
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO REAL] '} Iniciando consolidação GEE (Copia de Mosaicos)...")
    authenticate(project='ee-ipam')
    
    def list_recursive(parent):
        assets = []
        try:
            items = ee.data.listAssets({'parent': parent}).get('assets', [])
            for item in items:
                assets.append(item)
                if item['type'] in ['FOLDER', 'IMAGE_COLLECTION']:
                    assets.extend(list_recursive(item['id']))
        except: pass
        return assets

    print(f"Escaneando {BASE_PATH}...")
    all_assets = list_recursive(BASE_PATH)
    # Filtra apenas imagens que contenham "_blue_" para usar como fonte (representante do mosaico completo)
    source_images = [a for a in all_assets if a['type'] == 'IMAGE' and '_blue_' in a['id']]
    
    print(f"Encontradas {len(source_images)} imagens fonte (_blue_).")
    
    copies = []
    needed_collections = set()
    needed_folders = set()

    for img in source_images:
        old_id = img['id']
        parts = old_id.split('/')
        # .../LIBRARY_IMAGES(5)/SENSOR(6)/PERIOD(7)/MOSAIC(8)/BAND(9)/IMAGE(10)
        if len(parts) < 11: continue
        
        sensor = parts[6].upper()
        period = parts[7].upper()
        mosaic = parts[8].upper()
        # A nova coleção é o mosaico em minúsculo
        mosaic_coll_name = mosaic.lower()
        
        # Nome da imagem sem o sufixo da banda
        # Ex: image_peru_fire_sentinel2_minnbr_blue_2024_12 -> image_peru_fire_sentinel2_minnbr_2024_12
        img_name = parts[10].replace('_blue_', '_')
        
        new_id = f"{BASE_PATH}/{sensor}/{period}/{mosaic_coll_name}/{img_name}"
        target_coll = f"{BASE_PATH}/{sensor}/{period}/{mosaic_coll_name}"
        
        copies.append((old_id, new_id))
        needed_collections.add(target_coll)
        needed_folders.add(f"{BASE_PATH}/{sensor}")
        needed_folders.add(f"{BASE_PATH}/{sensor}/{period}")

    if not copies:
        print("Nenhuma imagem para consolidar encontrada.")
        return

    print(f"\n--- PLANO DE CONSOLIDACAO ---")
    print(f"Coleções a criar: {len(needed_collections)}")
    print(f"Cópias planejadas: {len(copies)}")
    
    if DRY_RUN:
        print("\n--- MODO SIMULAÇÃO ---")
        for old, new in copies[:5]:
            print(f"  [SIM] Copy: {old} \n        -> {new}")
        return

    # EXECUÇÃO REAL
    # 1. Cria Estrutura
    for f in sorted(list(needed_folders)):
        try: ee.data.createAsset({'type': 'FOLDER'}, f); print(f"  [OK] Folder: {f}")
        except: pass
    for c in sorted(list(needed_collections)):
        try: ee.data.createAsset({'type': 'IMAGE_COLLECTION'}, c); print(f"  [OK] Coll: {c}")
        except: pass

    # 2. Executa Cópias
    for old, new in copies:
        try:
            # GEE copyAsset(source, destination)
            ee.data.copyAsset(old, new, allowOverwrite=True)
            print(f"  [OK] Copiado: {new.split('/')[-1]}")
        except Exception as e:
            print(f"  [ERR] Erro ao copiar {old}: {e}")

    print("\n✅ Consolidação concluída. Os originais foram mantidos.")

if __name__ == "__main__":
    consolidate()
