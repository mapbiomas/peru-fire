"""
Script de Migração GEE: MONITOR/VERSION_01 → MONITOR_01
========================================================
Move todos os assets de:
  projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/...
Para:
  projects/mapbiomas-peru/assets/FIRE/MONITOR_01/...

Uso:
  Cole este script em uma célula do notebook e execute-o.
  
IMPORTANTE:
  - Este script lê e recria os assets NO LUGAR (copy + delete original).
  - Não há rollback automático. Faça uma cópia de segurança antes se necessário.
  - Execute com dry_run=True primeiro para apenas LISTAR os assets sem mover.
"""

import ee
import os
import sys

# Adiciona o caminho do src para importar o config
sys.path.append(os.path.join(os.getcwd(), 'peru-fire', 'mapbiomas_fire_monitor', 'version_01', 'src', 'core'))
from M0_auth_config import CONFIG

# Inicializa com o projeto correto
ee.Initialize(project='mapbiomas-peru')

SRC_BASE  = 'projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01'
DEST_BASE = 'projects/mapbiomas-peru/assets/FIRE/MONITOR_01'

def list_all_assets(folder_id, result=None):
    """Recursivamente lista todos os assets em uma pasta."""
    if result is None:
        result = []
    try:
        items = ee.data.listAssets({'parent': folder_id})
        for asset in items.get('assets', []):
            result.append(asset)
            if asset.get('type') in ['FOLDER', 'IMAGE_COLLECTION']:
                list_all_assets(asset['name'], result)
    except Exception as e:
        print(f"  ⚠️ Erro ao listar {folder_id}: {e}")
    return result

def ensure_folder(path):
    """Garante que uma pasta exista no GEE, criando os pais recursivamente."""
    try:
        ee.data.getAsset(path)
    except Exception:
        # Tenta garantir o pai primeiro
        parent = '/'.join(path.split('/')[:-1])
        if 'assets' in parent:
            ensure_folder(parent)
        
        try:
            ee.data.createAsset({'type': 'FOLDER'}, path)
            print(f"  [+] Pasta criada: {path}")
        except Exception as e:
            # Se já existir (race condition), ignoramos
            if 'already exists' not in str(e).lower():
                print(f"  ⚠️ Erro ao criar pasta {path}: {e}")

def ensure_collection(path):
    """Garante que uma ImageCollection exista no GEE, criando os pais recursivamente."""
    try:
        ee.data.getAsset(path)
    except Exception:
        # Garante o pai primeiro
        parent = '/'.join(path.split('/')[:-1])
        if 'assets' in parent:
            ensure_folder(parent)
            
        try:
            ee.data.createAsset({'type': 'IMAGE_COLLECTION'}, path)
            print(f"  [+] Coleção criada: {path}")
        except Exception as e:
            if 'already exists' not in str(e).lower():
                print(f"  ⚠️ Erro ao criar coleção {path}: {e}")

def migrate_assets(dry_run=True):
    """
    Migra os assets do caminho antigo para o novo.
    
    dry_run=True  → apenas lista o que seria feito (SEM mover nada)
    dry_run=False → executa a migração real (move e deleta o original)
    """
    print(f"{'🔍 DRY RUN' if dry_run else '🚀 MIGRAÇÃO REAL'}: {SRC_BASE} → {DEST_BASE}\n")
    
    # 1. Listar todos os assets na origem
    print("Listando assets na origem...")
    all_assets = list_all_assets(SRC_BASE)
    
    if not all_assets:
        print("  ⚠️ Nenhum asset encontrado na origem. Verifique o caminho.")
        return

    # Separar pastas/coleções de imagens
    folders     = [a for a in all_assets if a.get('type') == 'FOLDER']
    collections = [a for a in all_assets if a.get('type') == 'IMAGE_COLLECTION']
    images      = [a for a in all_assets if a.get('type') == 'IMAGE']
    
    print(f"Encontrado: {len(folders)} pastas, {len(collections)} coleções, {len(images)} imagens\n")
    
    if dry_run:
        print("--- O QUE SERIA MIGRADO ---")
        for a in all_assets:
            src  = a['name']
            dest = src.replace(SRC_BASE, DEST_BASE)
            print(f"  {a['type']}: {src.split('assets/')[-1]}")
            print(f"           → {dest.split('assets/')[-1]}")
        print(f"\n{len(all_assets)} assets seriam migrados.")
        print("\nPara executar a migração real, chame: migrate_assets(dry_run=False)")
        return
    
    # 2. Criar estrutura de pastas na DEST
    print("Criando estrutura de pastas no destino...")
    for f in folders:
        dest_path = f['name'].replace(SRC_BASE, DEST_BASE)
        ensure_folder(dest_path)
    
    # 3. Criar coleções na DEST
    print("Criando ImageCollections no destino...")
    for c in collections:
        dest_path = c['name'].replace(SRC_BASE, DEST_BASE)
        ensure_collection(dest_path)
    
    # 4. Copiar imagens para a DEST
    print(f"\nCopiando {len(images)} imagens...")
    ok = 0
    errors = 0
    for i, img in enumerate(images, 1):
        src_id  = img['name']
        dest_id = src_id.replace(SRC_BASE, DEST_BASE)
        try:
            ee.data.copyAsset(src_id, dest_id, allowOverwrite=True)
            print(f"  [{i}/{len(images)}] ✅ {src_id.split('assets/')[-1]}")
            ok += 1
        except Exception as e:
            print(f"  [{i}/{len(images)}] ❌ ERRO: {src_id.split('assets/')[-1]}: {e}")
            errors += 1
    
    print(f"\n{'='*60}")
    print(f"Migração concluída: {ok} copiadas, {errors} erros")
    
    if errors == 0:
        confirm = input("\nDeseja DELETAR os assets ORIGINAIS em MONITOR/VERSION_01? (s/N): ")
        if confirm.strip().lower() == 's':
            print("\nDeletando assets originais...")
            for img in images:
                try:
                    ee.data.deleteAsset(img['name'])
                    print(f"  🗑️  Deletado: {img['name'].split('assets/')[-1]}")
                except Exception as e:
                    print(f"  ⚠️  Erro ao deletar {img['name'].split('assets/')[-1]}: {e}")
            print("\n✅ Limpeza concluída!")
        else:
            print("\nOriginais mantidos. Você pode deletá-los manualmente depois.")
    else:
        print(f"\n⚠️  {errors} erros ocorreram. Originais NÃO deletados por segurança.")


# ── EXECUÇÃO ──────────────────────────────────────────────────────────────────
# Passo 1: Ver o que será migrado (sem mover nada)
# migrate_assets(dry_run=True)

# Passo 2: Quando estiver pronto, descomente a linha abaixo para migrar de verdade:
migrate_assets(dry_run=False)
