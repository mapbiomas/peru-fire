import sys
import os
import pandas as pd

# Configurar path do core
core_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core'
if core_path not in sys.path:
    sys.path.insert(0, core_path)

from M0_auth_config import CONFIG
from M_cache import _get_fs

fs = _get_fs()
bucket_base = f"{CONFIG['bucket']}/{CONFIG['gcs_library_images']}/sentinel2/monthly"

# Lista de pastas identificadas como incompletas na auditoria
# minnbr_buffer: de 2025_09 ate 2026_03 (faltando dayOfYear ou tamanho baixo)
# minnbr: meses residuais (menos o 2026_04 que esta OK)
folders_to_clean = [
    # Mosaico: minnbr_buffer
    "minnbr_buffer/2025_09",
    "minnbr_buffer/2025_10",
    "minnbr_buffer/2025_11",
    "minnbr_buffer/2025_12",
    "minnbr_buffer/2026_01",
    "minnbr_buffer/2026_02",
    "minnbr_buffer/2026_03",
    
    # Mosaico: minnbr (Limpando resíduos de meses incompletos)
    "minnbr/2025_09",
    "minnbr/2025_10",
    "minnbr/2025_11",
    "minnbr/2025_12",
    "minnbr/2026_01",
    "minnbr/2026_02",
    "minnbr/2026_03",
]

print(f"Limpando pastas de COG (/cog) em: {bucket_base}...\n")

for rel_path in folders_to_clean:
    cog_folder = f"{bucket_base}/{rel_path}/cog"
    
    if fs.exists(cog_folder):
        print(f"Removendo mosaicos incompletos: {rel_path}/cog")
        try:
            fs.rm(cog_folder, recursive=True)
            print(f"  -> Sucesso.")
        except Exception as e:
            print(f"  -> Erro ao remover: {e}")
    else:
        print(f"Ignorado: {rel_path}/cog (nao existe)")

print("\nLimpeza de COGs finalizada! O bucket esta pronto para novas montagens (M2).")
