"""
Script de Migração GCS - MapBiomas Fire Monitor
Organiza arquivos que foram salvos na estrutura de pastas invertida.

Estrutura Antiga (Errada): .../monthly/cog/2025/06/
Estrutura Nova (Certa):    .../monthly/2025/06/cog/
"""

import os
import sys

# Adiciona o diretório atual ao path para importar M0 e M_cache
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from M0_auth_config import CONFIG
from M_cache import _get_fs

def migrate():
    fs = _get_fs()
    bucket = CONFIG['bucket']
    base_prefix = f"sudamerica/{CONFIG['country']}/monitor/{CONFIG['version']}/library_images"
    
    print(f"🔍 Iniciando escaneamento em: gs://{bucket}/{base_prefix}")
    
    # 1. Buscar todos os arquivos recursivamente
    all_files = fs.find(f"{bucket}/{base_prefix}")
    
    moved_count = 0
    
    for f in all_files:
        # Detectar estrutura invertida para 'cog'
        # Ex: .../monthly/cog/2025/06/file.tif -> .../monthly/2025/06/cog/file.tif
        if '/monthly/cog/' in f:
            parts = f.split('/')
            # Encontrar o índice de 'monthly'
            try:
                idx = parts.index('monthly')
                # parts[idx] = 'monthly'
                # parts[idx+1] = 'cog'
                # parts[idx+2] = '2025'
                # parts[idx+3] = '06'
                if parts[idx+1] == 'cog':
                    year = parts[idx+2]
                    month = parts[idx+3]
                    filename = parts[-1]
                    
                    # Nova estrutura
                    new_parts = parts[:idx+1] + [year, month, 'cog', filename]
                    new_path = '/'.join(new_parts)
                    
                    print(f"🚚 Movendo COG: {f} -> {new_path}")
                    fs.mv(f, new_path)
                    moved_count += 1
            except (ValueError, IndexError):
                continue

        # Detectar estrutura invertida para 'chunks'
        # Ex: .../monthly/chunks/2025/06/file.tif -> .../monthly/2025/06/chunks/file.tif
        elif '/monthly/chunks/' in f:
            parts = f.split('/')
            try:
                idx = parts.index('monthly')
                if parts[idx+1] == 'chunks':
                    year = parts[idx+2]
                    month = parts[idx+3]
                    filename = parts[-1]
                    
                    new_parts = parts[:idx+1] + [year, month, 'chunks', filename]
                    new_path = '/'.join(new_parts)
                    
                    print(f"🚚 Movendo Chunk: {f} -> {new_path}")
                    fs.mv(f, new_path)
                    moved_count += 1
            except (ValueError, IndexError):
                continue

    print(f"\n✅ Migração concluída! {moved_count} arquivos reorganizados.")

if __name__ == "__main__":
    migrate()
