import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate

BASE_PATH = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES'

DRY_RUN = True # Mude para False para EXECUTAR A FAXINA

def deep_cleanup():
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO REAL] '} Iniciando FAXINA PROFUNDA no GEE...")
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
    
    to_delete = [] # Lista de IDs para deletar
    
    # 1. Identifica coleções temporárias e seu conteúdo
    temp_assets = [a['id'] for a in all_assets if '_temp' in a['id'].lower()]
    to_delete.extend(temp_assets)
    
    # 2. Identifica pastas em minúsculo nos níveis errados
    # Padrão correto: .../SENTINEL2(6)/MONTHLY(7)/MINNBR(8)/band(9)
    for a in all_assets:
        if a['id'] in to_delete: continue
        
        parts = a['id'].split('/')
        if len(parts) <= 5: continue
        
        # Nível 6, 7, 8 devem ser uppercase
        for i in [6, 7, 8]:
            if len(parts) > i:
                folder_name = parts[i]
                if folder_name != folder_name.upper() and i < 9:
                    to_delete.append(a['id'])
                    break

    # 3. Identifica coleções consolidadas (aquelas que criamos por engano no nível 8)
    # Ex: .../MONTHLY/minnbr (em vez de MINNBR/band)
    for a in all_assets:
        if a['id'] in to_delete: continue
        if a['type'] == 'IMAGE_COLLECTION':
            parts = a['id'].split('/')
            if len(parts) == 9 and parts[8] != parts[8].upper():
                to_delete.append(a['id'])

    # Filtra duplicatas e ordena (imagens primeiro, depois coleções)
    to_delete = sorted(list(set(to_delete)), key=lambda x: x.count('/'), reverse=True)

    print(f"\n--- RELATÓRIO DE FAXINA ---")
    print(f"Total de assets marcados para remoção: {len(to_delete)}")
    
    if not to_delete:
        print("Catálogo já está limpo!")
        return

    if DRY_RUN:
        print("\n--- AMOSTRA DE DELEÇÃO (Modo Simulação) ---")
        for asset_id in to_delete[:20]:
            print(f"  [DELETAR] {asset_id}")
        if len(to_delete) > 20:
            print(f"  ... e outros {len(to_delete)-20} assets.")
    else:
        print(f"\nExecutando deleção de {len(to_delete)} assets...")
        for asset_id in to_delete:
            try:
                ee.data.deleteAsset(asset_id)
                print(f"  [OK] Removido: {asset_id.replace(BASE_PATH, '')}")
            except Exception as e:
                print(f"  [ERR] Falha ao remover {asset_id}: {e}")

    print("\n[FINISH] Faxina concluída.")

if __name__ == "__main__":
    deep_cleanup()
