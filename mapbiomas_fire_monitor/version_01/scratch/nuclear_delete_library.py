import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate

BASE_PATH = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES'

DRY_RUN = False # Mude para False para APAGAR TUDO RECURSIVAMENTE

def nuclear_delete():
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO REAL] '} Iniciando DELEÇÃO TOTAL da LIBRARY_IMAGES...")
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

    print(f"Escaneando {BASE_PATH} para deleção total...")
    all_assets = list_recursive(BASE_PATH)
    
    # Ordena por profundidade (imagens primeiro, depois coleções, depois pastas)
    to_delete = sorted([a['id'] for a in all_assets], key=lambda x: x.count('/'), reverse=True)

    if not to_delete:
        print("A pasta já está vazia ou não existe.")
        return

    print(f"Total de assets a serem removidos: {len(to_delete)}")

    if DRY_RUN:
        print("\n--- AMOSTRA DE DELEÇÃO (Modo Simulação) ---")
        for asset_id in to_delete[:20]:
            print(f"  [KILL] {asset_id}")
        if len(to_delete) > 20:
            print(f"  ... e outros {len(to_delete)-20} assets.")
        print("\nPara executar de verdade, mude DRY_RUN = False no script.")
    else:
        print(f"\n☢️ EXECUTANDO DELEÇÃO NUCLEAR EM 5 SEGUNDOS... (Pressione Ctrl+C para cancelar)")
        import time
        time.sleep(5)
        
        for asset_id in to_delete:
            try:
                ee.data.deleteAsset(asset_id)
                print(f"  [DELETED] {asset_id.replace(BASE_PATH, '')}")
            except Exception as e:
                print(f"  [ERR] Falha ao deletar {asset_id}: {e}")
        
        print(f"\n[FINISH] A pasta {BASE_PATH} agora deve estar vazia.")

if __name__ == "__main__":
    nuclear_delete()
