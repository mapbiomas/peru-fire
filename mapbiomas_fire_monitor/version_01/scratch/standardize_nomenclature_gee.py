import ee
import concurrent.futures

# Inicializa GEE
ee.Initialize(project='mapbiomas-peru')

BANDS = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear']
SENSORS = ['SENTINEL2', 'SENTINEL2_BUFFER']
PERIODS = ['MONTHLY', 'YEARLY']

def fix_name(name):
    if name.startswith("minnbr_"):
        return name
    # Remove qualquer menção a minnbr (que colocamos antes)
    temp = name.replace("_minnbr", "")
    temp = temp.replace("minnbr_", "")
    # Adiciona no começo
    return "minnbr_" + temp

def rename_gee_asset(old_id, new_id):
    try:
        ee.data.renameAsset(old_id, new_id)
        print(f"[GEE] OK: {old_id.split('/')[-1]} -> {new_id.split('/')[-1]}")
    except Exception as e:
        print(f"[GEE] ERROR on {old_id.split('/')[-1]}: {e}")

print("=== PADRONIZANDO NOMENCLATURA GEE (PREFIXO) ===")
tasks = []
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    for sensor in SENSORS:
        for period in PERIODS:
            for band in BANDS:
                col_id = f"projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/LIBRARY_IMAGES/{sensor}/{period}/MINNBR/{band}"
                try:
                    assets = ee.data.getList({'id': col_id})
                    for a in assets:
                        if a['type'].upper() != 'IMAGE': continue
                        old_id = a['id']
                        img_name = old_id.split('/')[-1]
                        
                        new_name = fix_name(img_name)
                        
                        if new_name != img_name:
                            new_id = f"{col_id}/{new_name}"
                            tasks.append(executor.submit(rename_gee_asset, old_id, new_id))
                except Exception as e:
                    # Ignora coleções vazias ou inexistentes
                    pass

    concurrent.futures.wait(tasks)
print("GEE Renaming completed!")
