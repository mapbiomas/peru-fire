import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate

BASE_PATH = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES'

DRY_RUN = True # Mude para False para EXECUTAR O RESGATE

def rescue():
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO REAL] '} Iniciando RESGATE de assets GEE...")
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
    images = [a for a in all_assets if a['type'] == 'IMAGE']
    
    moves = []
    needed_collections = set()
    needed_folders = set()
    
    print(f"Analisando {len(images)} imagens para possível resgate...")
    
    for i, img in enumerate(images):
        old_id = img['id']
        parts = old_id.split('/')
        # .../LIBRARY_IMAGES(5)/SENSOR(6)/PERIOD(7)/MOSAIC(8)/BAND(9)/IMAGE(10)
        if len(parts) < 10: continue
        
        # Extrai metadados do nome da imagem ou da estrutura
        # Ex: image_peru_fire_sentinel2_minnbr_blue_2024_12
        img_name = parts[-1]
        name_parts = img_name.split('_')
        
        # Tenta deduzir os componentes corretos
        sensor = parts[6].upper()
        period = parts[7].upper()
        
        # Mosaico (pode estar sujo no path, tentamos pegar do nome da imagem)
        mosaic = "MINNBR"
        if "buffer" in img_name.lower(): mosaic = "MINNBR_BUFFER"
        
        # Banda (sempre em minúsculo)
        band = "unknown"
        for b in ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayofyear']:
            if b in img_name.lower():
                band = b
                break
        
        if band == "unknown": continue
        
        new_coll = f"{BASE_PATH}/{sensor}/{period}/{mosaic}/{band}"
        new_id = f"{new_coll}/{img_name}"
        
        if old_id != new_id:
            # Antes de marcar para mover, vamos checar se é single-band (apenas em execução real ou amostra)
            # Para o plano geral, assumimos que vamos tentar mover.
            moves.append((old_id, new_id))
            needed_collections.add(new_coll)
            needed_folders.add(f"{BASE_PATH}/{sensor}")
            needed_folders.add(f"{BASE_PATH}/{sensor}/{period}")
            needed_folders.add(f"{BASE_PATH}/{sensor}/{period}/{mosaic}")

    if not moves:
        print("Nenhuma imagem precisando de resgate.")
        return

    print(f"\n--- PLANO DE RESGATE ---")
    print(f"Imagens a serem movidas: {len(moves)}")
    print(f"Novas coleções a criar: {len(needed_collections)}")
    
    if DRY_RUN:
        print("\n--- AMOSTRA DE MOVIMENTAÇÃO (Simulação) ---")
        for old, new in moves[:10]:
            print(f"  [MOVE] {old.replace(BASE_PATH, '')} \n         -> {new.replace(BASE_PATH, '')}")
    else:
        # 1. Cria Estrutura
        for f in sorted(list(needed_folders)):
            try: ee.data.createAsset({'type': 'FOLDER'}, f); print(f"  [OK] Folder: {f}")
            except: pass
        for c in sorted(list(needed_collections)):
            try: ee.data.createAsset({'type': 'IMAGE_COLLECTION'}, c); print(f"  [OK] Coll: {c}")
            except: pass

        # 2. Move Imagens
        for old, new in moves:
            try:
                # Checa se é multibanda antes de mover (opcional, mas seguro)
                # band_count = len(ee.Image(old).bandNames().getInfo())
                # if band_count > 1:
                #     print(f"  [SKIP] Imagem multibanda ignorada: {old}")
                #     continue
                
                ee.data.renameAsset(old, new)
                print(f"  [OK] Resgatado: {new.split('/')[-1]}")
            except Exception as e:
                print(f"  [ERR] Erro ao mover {old}: {e}")

    print("\n[FINISH] Resgate concluído. Agora você pode rodar a faxina para apagar as pastas vazias.")

if __name__ == "__main__":
    rescue()
