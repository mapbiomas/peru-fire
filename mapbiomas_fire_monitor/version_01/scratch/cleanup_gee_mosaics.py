import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate

BASE_PATH = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES'

DRY_RUN = True # Mude para False para DELETAR

def cleanup():
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO REAL] '} Iniciando limpeza de coleções consolidadas...")
    authenticate(project='ee-ipam')
    
    # Pastas que sabemos que foram criadas incorretamente (minúsculas no nível do mosaico)
    wrong_collections = [
        f"{BASE_PATH}/SENTINEL2/MONTHLY/minnbr",
        f"{BASE_PATH}/SENTINEL2/MONTHLY/minnbr_buffer"
    ]
    
    for coll_id in wrong_collections:
        print(f"\nAnalisando: {coll_id}")
        try:
            assets = ee.data.listAssets({'parent': coll_id}).get('assets', [])
            print(f"  Encontrados {len(assets)} assets dentro.")
            
            if DRY_RUN:
                for a in assets[:5]:
                    print(f"  [SIM] Deletaria imagem: {a['id']}")
                print(f"  [SIM] Deletaria coleção: {coll_id}")
            else:
                for a in assets:
                    try:
                        ee.data.deleteAsset(a['id'])
                        print(f"  [OK] Deletado: {a['id'].split('/')[-1]}")
                    except: pass
                try:
                    ee.data.deleteAsset(coll_id)
                    print(f"  [OK] Coleção removida: {coll_id}")
                except: pass
        except Exception as e:
            print(f"  Coleção não encontrada ou erro: {e}")

    print("\n--- FIM DA LIMPEZA ---")

if __name__ == "__main__":
    cleanup()
