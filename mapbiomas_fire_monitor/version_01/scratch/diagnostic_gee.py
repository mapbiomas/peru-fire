import ee
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
core_path = os.path.abspath(os.path.join(current_dir, '..', 'src', 'core'))
sys.path.append(core_path)

from M0_auth_config import authenticate
authenticate(project='ee-ipam')

def list_recursive(parent):
    try:
        items = ee.data.listAssets({'parent': parent}).get('assets', [])
        for item in items:
            print(f"[{item['type']}] {item['id']}")
            if item['type'] in ['FOLDER', 'IMAGE_COLLECTION']:
                list_recursive(item['id'])
    except: pass

print("\n--- LISTAGEM LIBRARY_IMAGES ---")
list_recursive('projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES')
