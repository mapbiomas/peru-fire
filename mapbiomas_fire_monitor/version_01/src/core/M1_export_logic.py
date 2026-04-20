"""
M1 - Exportação GEE Multi-sensor (Lógica)
Converte generate_quality_mosaic_for_multisensors.js para a Python API do Earth Engine.
"""
import ee
import time

def ensure_asset_path(asset_id, type_at_end='IMAGE_COLLECTION'):
    """
    Garante que todo o caminho de pastas e a coleção final existam no GEE.
    """
    parts = asset_id.split('/')
    # Índice onde começam os assets após o prefixo do projeto
    # Ex: projects/mapbiomas-mosaics/assets/FIRE/SENTINEL2...
    start_index = 4 if parts[0] == 'projects' else 1
    
    for i in range(start_index, len(parts) + 1):
        partial_path = '/'.join(parts[:i])
        try:
            ee.data.getAsset(partial_path)
        except ee.EEException:
            is_last = (i == len(parts))
            asset_type = type_at_end if is_last else 'FOLDER'
            try:
                print(f"[GEE] Criando {asset_type}: {partial_path}")
                ee.data.createAsset({'type': asset_type}, partial_path)
            except Exception:
                pass

# ─── FUNÇÕES DE SUPORTE ────────────────────────────────────────────────────────

def clip_board_landsat(image):
    return image.updateMask(ee.Image().paint(image.geometry().buffer(-3000), 0).eq(0))

def bitwise_extract(value, from_bit, to_bit=None):
    if to_bit is None:
        to_bit = from_bit
    maskSize = ee.Number(1).add(to_bit).subtract(from_bit)
    mask = ee.Number(1).leftShift(maskSize).subtract(1)
    return value.rightShift(from_bit).bitwiseAnd(mask)

def add_band_nbr(image):
    exp = '( b("nir") - b("swir2") ) / ( b("nir") + b("swir2") )'
    minimo_nbr = image.expression(exp).multiply(-1).add(1).multiply(1000).toInt16().rename("nbr")
    return image.addBands(minimo_nbr)

def add_doy(image):
    doy = ee.Image(ee.Number.parse(image.date().format('D'))).toInt16().rename('dayOfYear')
    return image.addBands(doy)

# ─── CORREÇÕES RADIOMÉTRICAS ───────────────────────────────────────────────────

def corrections_ls57_col2(image):
    opticalBands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    image = image.addBands(opticalBands, None, True).addBands(thermalBands, None, True)

    cloudShadowBitMask = (1 << 3)
    cloudsBitMask = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))

    clear = bitwise_extract(qa, 6)
    water = bitwise_extract(qa, 7)
    radsatQA = image.select('QA_RADSAT')
    anySaturated = bitwise_extract(radsatQA, 0, 6)
    mask_saturation = clear.Or(water).And(anySaturated.Not())

    negative_mask = image.select(['SR_B1']).gt(0).And(image.select(['SR_B2']).gt(0)) \
        .And(image.select(['SR_B3']).gt(0)).And(image.select(['SR_B4']).gt(0)) \
        .And(image.select(['SR_B5']).gt(0)).And(image.select(['SR_B7']).gt(0))

    image = image.updateMask(mask).updateMask(mask_saturation).updateMask(negative_mask)
    oldBands = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7']
    newBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    return image.select(oldBands, newBands)

def corrections_ls89_col2(image):
    opticalBands = image.select('SR_B.*').multiply(0.0000275).add(-0.2)
    opticalBands = opticalBands.multiply(10000).subtract(0.0000275 * 0.2 * 1e5 * 100).round().divide(10000)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    image = image.addBands(opticalBands, None, True).addBands(thermalBands, None, True)

    qa = image.select('QA_PIXEL')
    cloud = qa.bitwiseAnd(1 << 3).And(qa.bitwiseAnd(1 << 9)).Or(qa.bitwiseAnd(1 << 4))
    good_pixel = qa.bitwiseAnd(1 << 6).Or(qa.bitwiseAnd(1 << 7))
    radsatQA = image.select('QA_RADSAT')
    saturated = radsatQA.bitwiseAnd(1 << 0).Or(radsatQA.bitwiseAnd(1 << 1)) \
        .Or(radsatQA.bitwiseAnd(1 << 2)).Or(radsatQA.bitwiseAnd(1 << 3)) \
        .Or(radsatQA.bitwiseAnd(1 << 4)).Or(radsatQA.bitwiseAnd(1 << 5)) \
        .Or(radsatQA.bitwiseAnd(1 << 6))

    negative_mask = image.select(['SR_B2']).gt(0).And(image.select(['SR_B3']).gt(0)) \
        .And(image.select(['SR_B4']).gt(0)).And(image.select(['SR_B5']).gt(0)) \
        .And(image.select(['SR_B6']).gt(0)).And(image.select(['SR_B7']).gt(0))

    image = image.updateMask(cloud.Not()).updateMask(good_pixel).updateMask(saturated.Not()).updateMask(negative_mask)
    oldBands = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']
    newBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    return image.select(oldBands, newBands).toFloat()

def modis_corrections(image):
    oldBands = ['sur_refl_b03', 'sur_refl_b04', 'sur_refl_b01', 'sur_refl_b02', 'sur_refl_b06', 'sur_refl_b07']
    newBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    return image.select(oldBands, newBands)

# ─── PIPELINES DE PROCESSAMENTO ────────────────────────────────────────────────

def process_ls57(image):
    return add_doy(add_band_nbr(corrections_ls57_col2(clip_board_landsat(image))))

def process_ls89(image):
    return add_doy(add_band_nbr(corrections_ls89_col2(clip_board_landsat(image))))

def process_s2(img):
    mask = img.select('cs').gte(0.40)
    optical = img.updateMask(mask).select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12'], ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])
    return add_doy(add_band_nbr(optical))

def process_modis(image):
    return add_doy(add_band_nbr(modis_corrections(image)))

def process_hls_s30(img):
    mask = img.select('Fmask').bitwiseAnd(1 << 1).eq(0)
    optical = img.updateMask(mask).select(['B2', 'B3', 'B4', 'B8A', 'B11', 'B12'], ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])
    out = add_band_nbr(optical).set({'system:time_start': img.get('system:time_start'), 'system:time_end': img.get('system:time_end')})
    return add_doy(out)

def process_hls_l30(img):
    mask = img.select('Fmask').bitwiseAnd(1 << 1).eq(0)
    optical = img.updateMask(mask).select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7'], ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'])
    out = add_band_nbr(optical).set({'system:time_start': img.get('system:time_start'), 'system:time_end': img.get('system:time_end')})
    return add_doy(out)

# ─── LÓGICA DE COLEÇÃO E REDUÇÃO ───────────────────────────────────────────────

def get_landsat_constellation(year):
    if year < 1999: return ['L5']
    elif year <= 2012: return ['L5', 'L7']
    elif year <= 2021: return ['L7', 'L8']
    else: return ['L8', 'L9']

def get_quality_mosaic(sensor, year, start_date, end_date, bounds):
    """
    Gera o mosaico de qualidade para a constelação escolhida.
    """
    multiplier = 1
    collection = None
    
    if sensor == 'landsat':
        constellation = get_landsat_constellation(year)
        lst_collects = []
        if 'L9' in constellation:
            lst_collects.append(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterDate(start_date, end_date).filterBounds(bounds).map(process_ls89))
        if 'L8' in constellation:
            lst_collects.append(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(start_date, end_date).filterBounds(bounds).map(process_ls89))
        if 'L7' in constellation:
            lst_collects.append(ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterDate(start_date, end_date).filterBounds(bounds).map(process_ls57))
        if 'L5' in constellation:
            lst_collects.append(ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterDate(start_date, end_date).filterBounds(bounds).map(process_ls57))
        
        collection = lst_collects[0]
        for c in lst_collects[1:]:
            collection = collection.merge(c)
        multiplier = 100

    elif sensor == 'sentinel2':
        collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate(start_date, end_date).filterBounds(bounds) \
            .linkCollection(ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED'), ['cs']).map(process_s2)
        multiplier = 0.01

    elif sensor == 'hls':
        s30_col = ee.ImageCollection("NASA/HLS/HLSS30/v002").filterDate(start_date, end_date).filterBounds(bounds).map(process_hls_s30)
        l30_col = ee.ImageCollection("NASA/HLS/HLSL30/v002").filterDate(start_date, end_date).filterBounds(bounds).map(process_hls_l30)
        collection = s30_col.merge(l30_col)
        multiplier = 100

    elif sensor == 'modis':
        mod_col1 = ee.ImageCollection("MODIS/061/MOD09A1")
        mod_col2 = ee.ImageCollection("MODIS/061/MYD09A1")
        collection = mod_col1.merge(mod_col2).filterDate(start_date, end_date).filterBounds(bounds).map(process_modis)
        multiplier = 0.01

    else:
        raise ValueError(f"Sensor desconhecido: {sensor}")

    # Redução (Quality Mosaic NBR)
    mosaic = collection.qualityMosaic('nbr')
    
    spectral = mosaic.select(['blue', 'green', 'red', 'nir', 'swir1', 'swir2']).multiply(multiplier).toByte()
    doy = mosaic.select('dayOfYear').toInt16()
    
    return spectral.addBands(doy).clip(bounds)

# ─── FUNÇÕES DE EXPORTAÇÃO ─────────────────────────────────────────────────────

def export_to_asset(mosaic, name, year, month=None, period='monthly', config=None, band=None):
    country_geom = config.get_country_geometry() if config else mosaic.geometry()
    if period == 'monthly':
        t_start = ee.Date(f'{year}-{month:02d}-01').millis()
        t_end = ee.Date(f'{year}-{month:02d}-01').advance(1, 'month').millis()
    else:
        t_start = ee.Date(f'{year}-01-01').millis()
        t_end = ee.Date(f'{year+1}-01-01').millis()

    img = mosaic.clip(country_geom).set({
        'system:time_start': t_start, 'system:time_end': t_end,
        'year': year, 'month': month or 0,
        'period': period, 'name': name,
    })

    from M0_auth_config import get_asset_mosaic_collection
    collection_id = get_asset_mosaic_collection(period=period, band=band)
    
    # Garante que a estrutura de pastas e a ImageCollection existam
    ensure_asset_path(collection_id, 'IMAGE_COLLECTION')

    asset_id = f"{collection_id}/{name}"

    task = ee.batch.Export.image.toAsset(
        image=img, description=f'ASSET_{name}', assetId=asset_id,
        region=country_geom.bounds(), scale=10, maxPixels=1e13,
        pyramidingPolicy={'.default': 'median'},
    )
    task.start()
    return task


def export_to_gcs(mosaic, name, year, month=None, period='monthly', bands=None, config_module=None):
    from M0_auth_config import CONFIG, monthly_chunk_path, yearly_chunk_path
    geometry = config_module.get_country_geometry() if config_module else mosaic.geometry()
    
    if period == 'monthly' and month is not None:
        folder = monthly_chunk_path(year, month)
    else:
        folder = yearly_chunk_path(year)

    if not bands:
        bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear']
        
    for band in bands:
        band_name = f"{name}_{band}"
        task = ee.batch.Export.image.toCloudStorage(
            image=mosaic.select(band).clip(geometry),
            description=f'GCS_{band_name}', bucket=CONFIG['bucket'],
            fileNamePrefix=f"{folder}/{band_name}", region=geometry.bounds(),
            scale=10, maxPixels=1e13, fileFormat='GeoTIFF',
            formatOptions={'cloudOptimized': True},
        )
        task.start()
