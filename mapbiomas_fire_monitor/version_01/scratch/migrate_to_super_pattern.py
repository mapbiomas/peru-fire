import ee
import os
import re
import datetime
from google.cloud import storage
import concurrent.futures

# --- CONFIGURAÇÃO ---
PROJECT_ID_GCS = "mapbiomas-peru"
PROJECT_ID_GEE = "mapbiomas-peru"
BUCKET_NAME = "mapbiomas-fire"
COUNTRY = "peru"

# Inicialização
try:
    ee.Initialize(project=PROJECT_ID_GEE)
except:
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID_GEE)

client = storage.Client(project=PROJECT_ID_GCS)
bucket = client.bucket(BUCKET_NAME)

BANDS = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear', 'nbr']

def mega_parse(full_path):
    """
    Identifica metadados priorizando a estrutura de pastas para periodicidade.
    """
    name = full_path.split('/')[-1]
    
    # 1. Determina Periodicidade pela PASTA
    period = "monthly" if "/monthly/" in full_path.lower() else "yearly"
    
    # 2. Identifica se é CHUNK ou COG
    is_cog = '_cog' in name.lower() or '/cog/' in name.lower()
    suffix_match = re.search(r'(\d{10}-\d{10})', name)
    suffix = suffix_match.group(1) if suffix_match else None
    
    # 3. Extrai a DATA (YYYY/MM ou YYYY_MM ou YYYY)
    # Procura no caminho completo para garantir que pega o mês se estiver em pasta separada
    date_parts = None
    # Tenta padrão YYYY/MM ou YYYY_MM
    match_ym = re.search(r'(\d{4})[/_](\d{2})', full_path)
    if match_ym:
        date_parts = f"{match_ym.group(1)}_{match_ym.group(2)}"
    else:
        # Tenta apenas o ano
        match_y = re.search(r'(\d{4})', full_path)
        if match_y:
            date_parts = match_y.group(1)
            
    if not date_parts: return None

    # 4. Identifica Banda, Sensor e Mosaic
    clean = name.lower()
    found_band = None
    for b in sorted(BANDS, key=len, reverse=True):
        if f"_{b}" in clean:
            found_band = b
            break
    if not found_band: return None

    sensor = 'landsat' if 'landsat' in clean else 'sentinel2'
    mosaic = 'minnbr_buffer' if 'buffer' in clean else 'minnbr'

    return {
        'sensor': sensor,
        'period': period,
        'mosaic': mosaic,
        'band': found_band,
        'temporal_id': date_parts,
        'country': COUNTRY,
        'suffix': suffix,
        'is_cog': is_cog,
        'original_path': full_path
    }

def build_new_name(meta):
    base = f"image_{meta['country']}_fire_{meta['sensor']}_{meta['mosaic']}_{meta['band']}_{meta['temporal_id']}"
    if meta['is_cog']: base += "_cog"
    if meta['suffix']: base += "_" + meta['suffix']
    return base

def migrate_gcs():
    print("\n=== [GCS] INICIANDO MIGRAÇÃO (FIX PERIODICIDADE) ===")
    base_prefix = 'sudamerica/peru/monitor/version_01'
    blobs = bucket.list_blobs(prefix=base_prefix)
    count = 0
    
    for blob in blobs:
        if not blob.name.endswith('.tif'): continue
        # Pula se já estiver no padrão final correto (incluindo a pasta certa)
        if '/library_images/' in blob.name and blob.name.split('/')[-1].startswith('image_'):
            # Verifica se o período na pasta condiz com o conteúdo
            meta = mega_parse(blob.name)
            if meta and f"/{meta['period']}/" in blob.name:
                continue
        
        meta = mega_parse(blob.name)
        if not meta: continue
        
        new_basename = build_new_name(meta) + ".tif"
        
        # Define subpasta (chunks)
        is_chunk = meta['suffix'] is not None or "/chunks/" in blob.name.lower()
        subfolder = "chunks" if is_chunk else ""
        
        # Monta o novo caminho respeitando o período detectado
        dest_path = f"sudamerica/peru/monitor/version_01/library_images/{meta['sensor']}/{meta['period']}/{meta['mosaic']}/{meta['temporal_id']}"
        if subfolder: dest_path += f"/{subfolder}"
        
        new_path = f"{dest_path}/{new_basename}"
        
        if blob.name == new_path: continue
        
        print(f"Movendo GCS: {blob.name.split('/')[-1]} -> {new_path}")
        try:
            bucket.rename_blob(blob, new_path)
            count += 1
        except Exception as e:
            print(f"Erro GCS: {e}")
            
    print(f"MIGRAÇÃO GCS CONCLUÍDA! {count} arquivos organizados.")

if __name__ == "__main__":
    # Focando apenas no GCS para corrigir a bagunça
    migrate_gcs()
