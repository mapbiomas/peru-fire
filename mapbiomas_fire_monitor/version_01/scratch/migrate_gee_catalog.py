import ee
import sys
import os

# Adiciona o caminho do core para herdar a autenticação do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

try:
    from M0_auth_config import authenticate, CONFIG
except ImportError:
    print(f"Erro: Não foi possível encontrar M0_auth_config.py em {core_path}")
    sys.exit(1)

# CONFIGURAÇÃO
OLD_BASE = 'projects/mapbiomas-peru/assets/FIRE/MONITOR_01'
NEW_BASE = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01'
DRY_RUN = False # Mude para False para EXECUTAR

def migrate_gee():
    print("="*80)
    print("AUTENTICANDO GEE...")
    try:
        authenticate(project='ee-ipam')
    except Exception as e:
        print(f"Erro crítico na autenticação: {e}")
        return

    print("\n" + "="*80)
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO] '} Iniciando migração GEE...")
    print("="*80)
    
    # 1. Listar todos os assets recursivamente
    def list_recursive(parent):
        assets = []
        try:
            items = ee.data.listAssets({'parent': parent}).get('assets', [])
            for item in items:
                assets.append(item)
                if item['type'] in ['FOLDER', 'IMAGE_COLLECTION']:
                    assets.extend(list_recursive(item['id']))
        except Exception as e:
            pass
        return assets

    print(f"Escaneando assets em {OLD_BASE}...")
    all_assets = list_recursive(OLD_BASE)
    
    if not all_assets:
        print("Nenhum asset encontrado na pasta de origem ou pasta não existe.")
        return

    # Ordenar por profundidade (arquivos primeiro, depois pastas)
    all_assets.sort(key=lambda x: x['id'].count('/'), reverse=True)

    moves = []
    deletes = []

    for asset in all_assets:
        old_id = asset['id']
        relative = old_id.replace(OLD_BASE + '/', '')
        parts = relative.split('/')
        
        if asset['type'] in ['FOLDER', 'IMAGE_COLLECTION']:
            new_relative = '/'.join([p.upper() for p in parts])
            deletes.append(old_id)
        else:
            new_relative = '/'.join([p.upper() for p in parts[:-1]] + [parts[-1]])

        new_id = f"{NEW_BASE}/{new_relative}"
        moves.append((old_id, new_id, asset['type']))

    print(f"\nEncontrados {len(moves)} assets para mover.")
    # Mostra do topo para baixo (reverse=True) para ser mais legível
    for old, new, atype in sorted(moves, key=lambda x: x[0].count('/')): 
        print(f"  [{atype}] {old} \n       --> {new}")

    if DRY_RUN:
        print("\n" + "="*80)
        print("FIM DA SIMULAÇÃO (Modo DRY_RUN ativo)")
        print("Para executar de verdade, altere 'DRY_RUN = False' no arquivo.")
        print("="*80)
        return

    confirm = input("\n⚠️ EXECUTAR MOVIMENTAÇÃO REAL? (digite 'sim'): ")
    if confirm.lower() != 'sim': 
        print("Cancelado.")
        return

    try: ee.data.createAsset({'type': 'FOLDER'}, NEW_BASE)
    except: pass

    for old, new, atype in moves:
        try:
            dest_parts = new.split('/')
            for i in range(len(dest_parts) - 1):
                parent_path = '/'.join(dest_parts[:i+1])
                if parent_path.startswith(NEW_BASE):
                    try: ee.data.createAsset({'type': 'FOLDER'}, parent_path)
                    except: pass
            
            ee.data.renameAsset(old, new)
            print(f"✅ Movido: {new}")
        except Exception as e:
            print(f"❌ Erro ao mover {old}: {e}")

    deletes.append(OLD_BASE)
    for old_id in deletes:
        try:
            ee.data.deleteAsset(old_id)
            print(f"🗑️ Deletado (vazio): {old_id}")
        except: pass

    print("\n✅ Migração GEE Concluída.")

if __name__ == "__main__":
    migrate_gee()
