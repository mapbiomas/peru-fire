import os
from google.cloud import storage

# Initialize GCS client
client = storage.Client(project='mapbiomas-peru')
bucket = client.bucket('mapbiomas-fire')

BANDS = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear']
base_prefix = 'sudamerica/peru/monitor/version_01/library_images'

print("=== FIXING GCS STRUCTURE AND RENAMING (FAST API) ===")

# Process all blobs in the library_images prefix
blobs = bucket.list_blobs(prefix=base_prefix)

count = 0
for blob in blobs:
    if not blob.name.endswith('.tif'): continue
    
    parts = blob.name.split('/')
    if len(parts) < 10: continue
    
    basename = parts[-1]
    if '_minnbr_' in basename: continue
    
    is_chunk = '/chunks/' in blob.name
    is_cog = '/cog/' in blob.name
    if not (is_chunk or is_cog): continue
    
    new_basename = None
    for b in BANDS:
        needle = f"_{b}"
        if needle in basename:
            new_basename = basename.replace(needle, f"_minnbr{needle}", 1)
            break
            
    if not new_basename: continue
    
    try:
        monthly_idx = parts.index('monthly')
        year_part = parts[monthly_idx + 1]
        
        if year_part.isdigit() and len(year_part) == 4:
            month_part = parts[monthly_idx + 2]
            type_part = parts[monthly_idx + 3]
            
            if type_part in ['chunks', 'cog']:
                new_parts = parts[:monthly_idx + 1]
                new_parts.append('minnbr')
                new_parts.append(f"{year_part}_{month_part}")
                new_parts.append(type_part)
                new_parts.append(new_basename)
                
                new_name = '/'.join(new_parts)
                print(f"Renaming: {blob.name} -> {new_name}", flush=True)
                bucket.rename_blob(blob, new_name)
                count += 1
    except Exception as e:
        print(f"Failed on {blob.name}: {e}", flush=True)

print(f"\nGCS Structure Fix Completed! Renamed {count} files.", flush=True)
