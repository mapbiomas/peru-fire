import json
import os

notebook_path = r'c:\Users\wallace.silva\OneDrive - IPAM-Amazonia\Área de Trabalho\projetos\fire_monitor\peru-fire\mapbiomas_fire_monitor\version_01\notebooks\mapbiomas_fire_sentinel_peru.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code' and any('# M0 — SETUP MESTRE' in line for line in cell.get('source', [])):
        new_source = []
        for line in cell['source']:
            if 'subprocess.run(["apt-get", "update", "-qq"])' in line:
                new_source.append('        subprocess.run(["apt-get", "update", "-qq"])\n')
            elif 'subprocess.run(["apt-get", "install", "-y", "-qq", "gdal-bin"' in line:
                new_source.append('        subprocess.run(["apt-get", "install", "-y", "-qq", "gdal-bin", "python3-gdal"])\n')
            elif 'subprocess.run(["pip", "install", "-q", "earthengine-api"' in line:
                new_source.append('        subprocess.run(["pip", "install", "-q", "earthengine-api", "gcsfs", "rasterio", "scipy", "tqdm"])\n')
            elif 'print("Nota: Rodar comandos !apt' in line:
                # We can keep or remove this print
                pass
            else:
                new_source.append(line)
        cell['source'] = new_source
        break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
    
print("Notebook atualizado com sucesso!")
