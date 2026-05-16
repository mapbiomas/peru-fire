import os
import sys
import json

# Adiciona o caminho do core para herdar a autenticação do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

try:
    from M0_auth_config import _get_fs
except ImportError:
    print(f"Erro: Não foi possível encontrar M0_auth_config.py em {core_path}")
    sys.exit(1)

# CONFIGURAÇÃO
BUCKET = "mapbiomas-fire"
OLD_PREFIX = "sudamerica/peru/monitor/version_01"
NEW_PREFIX = "sudamerica/peru/CATALOG_01"
DRY_RUN = False # Mude para False para EXECUTAR

def migrate_gcs():
    print("="*80)
    print(f"{' [DRY RUN] ' if DRY_RUN else ' [EXECUÇÃO] '} Iniciando migração GCS via GCSFS...")
    print("="*80)
    
    fs = _get_fs()
    base_path = f"{BUCKET}/{OLD_PREFIX}"
    
    print(f"Escaneando arquivos em gs://{base_path} ...")
    try:
        # find() é recursivo e traz todos os arquivos dentro da árvore
        all_files = fs.find(base_path)
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
        return

    if not all_files:
        print("Nenhum arquivo encontrado na pasta de origem.")
        return

    moves = []
    for f in all_files:
        # O gcsfs retorna caminhos sem o prefixo gs:// (ex: bucket/path/file.tif)
        # Normaliza barras para evitar problemas no Windows
        f_norm = f.replace('\\', '/')
        
        relative = f_norm.replace(f"{BUCKET}/{OLD_PREFIX}/", "")
        parts = relative.split('/')
        
        # Pastas em MAIÚSCULO, Arquivo mantém original
        new_parts = [p.upper() for p in parts[:-1]] + [parts[-1]]
        new_path = f"{BUCKET}/{NEW_PREFIX}/{'/'.join(new_parts)}"
        
        moves.append((f_norm, new_path))

    print(f"\nEncontrados {len(moves)} arquivos para mover.")
    
    # Amostra das primeiras mudanças
    for old, new in moves[:5]:
        print(f"  [PLANEJADO] gs://{old}\n              --> gs://{new}")

    if DRY_RUN:
        print("\n" + "="*80)
        print("FIM DA SIMULAÇÃO (Modo DRY_RUN ativo)")
        print("Para executar de verdade, altere 'DRY_RUN = False' no topo do script.")
        print("="*80)
        return

    confirm = input("\n⚠️ VOCÊ TEM CERTEZA QUE DESEJA EXECUTAR A MOVIMENTAÇÃO REAL? (digite 'sim'): ")
    if confirm.lower() != 'sim':
        print("Operação cancelada pelo usuário.")
        return
    
    print(f"\nIniciando movimentação de {len(moves)} arquivos...")
    success_count = 0
    error_count = 0
    
    for i, (old, new) in enumerate(moves, 1):
        if i % 100 == 0 or i == len(moves):
            print(f"  Progresso: {i}/{len(moves)} arquivos processados...")
            
        try:
            # fs.mv faz a cópia e o delete internamente de forma otimizada
            fs.mv(old, new)
            success_count += 1
        except Exception as e:
            print(f"❌ Erro ao mover {old}: {e}")
            error_count += 1
    
    print(f"\n✅ Concluído!")
    print(f"   - Sucesso: {success_count}")
    print(f"   - Erros:   {error_count}")
    print(f"\nOs arquivos agora estão em gs://{BUCKET}/{NEW_PREFIX}/")

if __name__ == "__main__":
    migrate_gcs()
