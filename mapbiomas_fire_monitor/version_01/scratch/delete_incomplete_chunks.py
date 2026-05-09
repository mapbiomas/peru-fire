import sys
import pandas as pd

# Configurar path do core
core_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\src\core'
if core_path not in sys.path:
    sys.path.insert(0, core_path)

from M0_auth_config import CONFIG
from M_cache import _get_fs

fs = _get_fs()
bucket_base = f"{CONFIG['bucket']}/{CONFIG['gcs_library_images']}/sentinel2/monthly"

csv_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\scratch\chunks_summary.csv'
df = pd.read_csv(csv_path)

spectral_bands = ['blue', 'green', 'nir', 'red', 'swir1', 'swir2']
to_delete = []

for index, row in df.iterrows():
    mosaic = row['mosaic']
    period = str(row['period'])
    
    is_incomplete = False
    
    # Checar bandas espectrais (devem ser 12)
    for band in spectral_bands:
        if band in df.columns:
            if row[band] != 12.0:
                is_incomplete = True
                break
        else:
            is_incomplete = True # Faltou a coluna inteira
            
    # Checar dayOfYear (deve ser 20)
    if 'dayOfYear' in df.columns:
        if row['dayOfYear'] != 20.0:
            is_incomplete = True
    else:
        is_incomplete = True

    if is_incomplete:
        # Apontar para a pasta do mosaico/periodo
        path = f"{bucket_base}/{mosaic}/{period}/chunks"
        to_delete.append(path)

print(f"Encontradas {len(to_delete)} pastas incompletas para limpar no GCS.")

for path in to_delete:
    print(f"Deletando: {path}")
    if fs.exists(path):
        fs.rm(path, recursive=True)
        print("  -> Deletado.")
    else:
        print("  -> Pasta não encontrada.")

print("\nLimpeza de chunks incompletos finalizada!")
