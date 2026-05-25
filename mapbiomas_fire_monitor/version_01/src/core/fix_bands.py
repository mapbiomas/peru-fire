"""Fix band names on existing GCS mosaics: band_0/1 -> classification/probability."""
import os, sys, tempfile, rasterio
from google.cloud import storage

sys.path.insert(0, os.path.dirname(__file__))
from M0_auth_config import CONFIG

bucket_name = CONFIG['bucket']
base_prefix = f"{CONFIG['gcs_library_classifications']}/"

client = storage.Client()
bucket = client.bucket(bucket_name)

blobs = list(bucket.list_blobs(prefix=base_prefix))
mosaics = sorted((b for b in blobs if '/CLASSIFIED_REGION/' in b.name and b.name.endswith('.tif')), key=lambda b: b.name)

print(f"Found {len(mosaics)} mosaics")
fixed = 0
tmpdir = tempfile.mkdtemp('fix_bands')

try:
    for i, blob in enumerate(mosaics):
        name = os.path.basename(blob.name)
        print(f"  [{i+1}/{len(mosaics)}] {name} ... ", end='', flush=True)
        local = os.path.join(tmpdir, name)
        try:
            blob.download_to_filename(local)
            with rasterio.open(local, 'r+') as src:
                src.descriptions = ('classification', 'probability')
            blob.upload_from_filename(local)
            fixed += 1
            print("OK")
        except Exception as e:
            print(f"FAIL: {e}")
        finally:
            if os.path.exists(local):
                os.remove(local)
finally:
    os.rmdir(tmpdir)

print(f"\nDone. {fixed}/{len(mosaics)} fixed.")
