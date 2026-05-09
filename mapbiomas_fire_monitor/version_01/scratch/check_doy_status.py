import sys
import os

# Configurar path do core
sys.path.insert(0, r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core')

from M_cache import _get_fs
from M0_auth_config import CONFIG

fs = _get_fs()
base = f"gs://{CONFIG['bucket']}/sudamerica/peru/monitor/version_01/library_images/sentinel2/monthly"

print("Auditoria Especial: Banda [dayOfYear]")
print("="*60)

for m in ['minnbr', 'minnbr_buffer']:
    print(f"\nMOSAICO: {m}")
    print(f"{'Periodo':<12} | {'Chunks (DOY)':<15} | {'COG (DOY)':<10}")
    print("-" * 45)
    
    m_path = f"{base}/{m}"
    try:
        periods = fs.ls(m_path)
        for p in periods:
            period_name = os.path.basename(p.rstrip('/'))
            
            # Contar chunks de dayOfYear
            doy_chunks = 0
            chunks_dir = f"{p}/chunks"
            if fs.exists(chunks_dir):
                files = fs.ls(chunks_dir)
                doy_chunks = len([f for f in files if 'dayOfYear' in f])
            
            # Verificar se existe COG de dayOfYear
            doy_cog = "NAO"
            cog_dir = f"{p}/cog"
            if fs.exists(cog_dir):
                cog_files = fs.ls(cog_dir)
                if any('dayOfYear' in f and f.endswith('_cog.tif') for f in cog_files):
                    doy_cog = "SIM"
            
            print(f"{period_name:<12} | {doy_chunks:<15} | {doy_cog:<10}")
    except Exception as e:
        print(f"Erro em {m}: {e}")

print("\nNota: O ideal para dayOfYear no Peru e ter 20 chunks.")
