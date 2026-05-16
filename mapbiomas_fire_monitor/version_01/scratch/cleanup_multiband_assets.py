import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate

BASE_PATH = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES'

DRY_RUN = False # Mude para False para DELETAR

def cleanup_multiband():
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO REAL] '} Iniciando busca por imagens multibanda em coleções singleband...")
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

    print(f"Escaneando {BASE_PATH} (isso pode levar um tempo)...")
    all_assets = list_recursive(BASE_PATH)
    images = [a for a in all_assets if a['type'] == 'IMAGE']
    
    print(f"Analisando {len(images)} imagens...")
    
    to_delete = []
    
    for i, img in enumerate(images):
        asset_id = img['id']
        try:
            # Verifica o numero de bandas
            band_names = ee.Image(asset_id).bandNames().getInfo()
            if len(band_names) > 1:
                print(f"  [FOUND] Multibanda ({len(band_names)}): {asset_id}")
                to_delete.append(asset_id)
            
            if i % 50 == 0 and i > 0:
                print(f"  ... processadas {i}/{len(images)} imagens")
        except Exception as e:
            print(f"  [ERR] Erro ao analisar {asset_id}: {e}")

    print(f"\n--- RESUMO DO DIAGNOSTICO ---")
    print(f"Total de imagens analisadas: {len(images)}")
    print(f"Imagens multibanda encontradas: {len(to_delete)}")
    
    if not to_delete:
        print("Nenhuma imagem irregular encontrada.")
        return

    if DRY_RUN:
        print("\n--- MODO SIMULAÇÃO: Nada será deletado ---")
    else:
        print(f"\nDeletando {len(to_delete)} imagens...")
        for asset_id in to_delete:
            try:
                ee.data.deleteAsset(asset_id)
                print(f"  [OK] Deletado: {asset_id}")
            except Exception as e:
                print(f"  [ERR] Falha ao deletar {asset_id}: {e}")

    print("\n[FINISH] Processo concluido.")

if __name__ == "__main__":
    cleanup_multiband()
