import os
from google.cloud import storage

# Initialize GCS client
client = storage.Client(project='mapbiomas-peru')
bucket = client.bucket('mapbiomas-fire')

base_prefix = 'sudamerica/peru/monitor/version_01/library_images'

print("=== PADRONIZANDO NOMENCLATURA GCS (PREFIXO) ===")

def fix_name(name):
    if name.startswith("minnbr_"):
        return name
    # Remove qualquer menção a minnbr que esteja no meio
    temp = name.replace("_minnbr", "")
    temp = temp.replace("minnbr_", "")
    # Adiciona no começo
    return "minnbr_" + temp

blobs = bucket.list_blobs(prefix=base_prefix)

count = 0
for blob in blobs:
    if not blob.name.endswith('.tif'): continue
    
    parts = blob.name.split('/')
    if len(parts) < 10: continue
    
    basename = parts[-1]
    
    is_chunk = '/chunks/' in blob.name
    is_cog = '/cog/' in blob.name
    if not (is_chunk or is_cog): continue
    
    new_basename = fix_name(basename)
    
    if new_basename != basename:
        parts[-1] = new_basename
        new_name = '/'.join(parts)
        
        try:
            print(f"Renaming: {basename} -> {new_basename}", flush=True)
            bucket.rename_blob(blob, new_name)
            count += 1
        except Exception as e:
            print(f"Failed on {blob.name}: {e}", flush=True)

print(f"\nGCS Renaming Completed! Renamed {count} files.", flush=True)
