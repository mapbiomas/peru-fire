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

print(f"Investigando GCS em: {bucket_base}...\n")
mosaics = fs.ls(bucket_base)

data = []

# Iterar sobre os tipos de mosaico (ex: minnbr, minnbr_buffer)
for m_path in mosaics:
    m_name = m_path.split('/')[-1]
    
    # Listar os períodos (ex: 2025_10, 2025_11)
    periods = fs.ls(m_path)
    for p_path in periods:
        p_name = p_path.split('/')[-1]
        chunks_path = f"{p_path}/chunks"
        
        if fs.exists(chunks_path):
            try:
                # Usar recursividade direta na pasta de chunks para evitar problemas de paginação
                print(f"  Avaliando {m_name} -> {p_name}...")
                files = fs.ls(chunks_path)
                
                band_counts = defaultdict(int)
                for f in files:
                    if f.endswith('.tif'):
                        basename = os.path.basename(f)
                        parts = basename.replace('.tif', '').split('_')
                        
                        # Localizar onde está o ano (ex: 2025) para descobrir qual parte é a banda
                        date_idx = -1
                        for i, part in enumerate(parts):
                            if part.isdigit() and len(part) == 4 and i+1 < len(parts) and parts[i+1].isdigit():
                                date_idx = i
                                break
                        
                        if date_idx > 0:
                            band = parts[date_idx-1]
                            band_counts[band] += 1
                
                # Se não houver nada, registrar 0
                if not band_counts:
                    data.append({
                        'mosaic': m_name,
                        'period': p_name,
                        'band': 'ALL',
                        'chunks_count': 0
                    })
                
                for band, count in band_counts.items():
                    data.append({
                        'mosaic': m_name,
                        'period': p_name,
                        'band': band,
                        'chunks_count': count
                    })
            except Exception as e:
                print(f"Erro ao listar {chunks_path}: {e}")

df = pd.DataFrame(data)

if not df.empty:
    print("\nResumo de Chunks por Mosaico, Periodo e Banda:\n")
    # Tabela pivot para melhor visualização (Bandas nas colunas, Meses nas linhas)
    pivot = df.pivot_table(index=['mosaic', 'period'], columns='band', values='chunks_count', fill_value=0)
    
    # Exibir a tabela no terminal
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(pivot)
    
    # Salvar para o usuário abrir no Excel/VS Code se quiser
    csv_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\scratch\chunks_summary.csv'
    pivot.to_csv(csv_path)
    print(f"\nRelatorio completo salvo em: {csv_path}")
else:
    print("\nNenhum chunk encontrado no diretorio especificado.")
