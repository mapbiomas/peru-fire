import sys
import os
import pandas as pd
from collections import defaultdict

# Configurar path do core
core_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core'
if core_path not in sys.path:
    sys.path.insert(0, core_path)

from M0_auth_config import CONFIG
from M_cache import _get_fs

fs = _get_fs()
bucket_base = f"{CONFIG['bucket']}/{CONFIG['gcs_library_images']}/sentinel2/monthly"

print(f"Auditoria de Mosaicos (COG) em: {bucket_base}...\n")
mosaics = fs.ls(bucket_base)

data = []

for m_path in mosaics:
    m_name = m_path.split('/')[-1]
    periods = fs.ls(m_path)
    
    for p_path in periods:
        p_name = p_path.split('/')[-1]
        cog_path = f"{p_path}/cog"
        
        if fs.exists(cog_path):
            print(f"  Verificando COGs: {m_name} -> {p_name}...")
            # Listar apenas os arquivos _cog.tif
            files = fs.ls(cog_path, detail=True)
            
            for f in files:
                filename = os.path.basename(f['name'])
                if filename.endswith('_cog.tif'):
                    # Extrair banda do nome: image_peru_fire_sentinel2_minnbr_swir1_2026_03_cog.tif
                    parts = filename.replace('_cog.tif', '').split('_')
                    # Localizar o ano para pegar a banda anterior
                    date_idx = -1
                    for i, part in enumerate(parts):
                        if part.isdigit() and len(part) == 4:
                            date_idx = i
                            break
                    
                    if date_idx > 0:
                        band = parts[date_idx-1]
                        size_mb = f['size'] / (1024 * 1024) # Bytes para MB
                        
                        data.append({
                            'mosaic': m_name,
                            'period': p_name,
                            'band': band,
                            'size_mb': round(size_mb, 2)
                        })

df = pd.DataFrame(data)

if not df.empty:
    print("\nRelatorio de Tamanho dos COGs (MB):\n")
    pivot = df.pivot_table(index=['mosaic', 'period'], columns='band', values='size_mb', fill_value=0)
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    print(pivot)
    
    csv_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\scratch\cog_sizes_audit.csv'
    pivot.to_csv(csv_path)
    print(f"\nRelatorio salvo em: {csv_path}")
else:
    print("\nNenhum arquivo COG encontrado.")
