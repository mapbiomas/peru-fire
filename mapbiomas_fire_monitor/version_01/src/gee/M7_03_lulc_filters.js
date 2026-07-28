/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_03
Filtros LULC (MapBiomas Peru Collection 3)

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 O QUE FAZ:
1. Carrega imagens nacionais da collection -ft02
2. Aplica mascara LULC por regiao: remove classes nao-queimaveis
3. Buffer 90m em corpos d'agua, remove pixels solitarios
4. Exporta para -ft03

🔧 LULC classes removidas:
   Agua: [33,31,34] — rio/lago/oceano, aquicultura, glaciar
   Sem veg: [23,24,32,61,68,25] — praia, infra urbana, salina, salar, sem veg
   Rochoso: [29] — afloramento rochoso
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;

var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');

// ═══ CONFIG ═══
var COLLECTION_BASE = 'monitor_01-sentinel2_minnbr_monthly_01';
var STAGE_IN = '-ft02';
var STAGE_OUT = '-ft03';

var CLASSES_AGUA = [33, 31, 34];
var CLASSES_SEM_VEG = [23, 24, 32, 61, 68, 25];

var masks = {
    'region1':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),
    'region2':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),
    'region3':  [24, 29],
    'region4':  [24, 68, 25, 29],
    'region5':  [29, 24, 68],
    'region6':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),
    'region7':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),
    'region8':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),
    'region9':  [25],
    'region10': [25],
};
// ═══════════════

var PATH_FILTERED = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/FILTERED/';
var COLL_IN = PATH_FILTERED + COLLECTION_BASE + STAGE_IN;
var COLL_OUT = PATH_FILTERED + COLLECTION_BASE + STAGE_OUT;

var LULC_PALETTE = [
    'ffffff', '32a65e', '32a65e', '1f8d49', '7dc975', '04381d', '026975', '000000',
    '000000', '7a6c00', 'ad975a', '519799', 'd6bc74', 'd89f5c', 'ffffb2', 'edde8e',
    '000000', '000000', 'f5b3c8', 'c27ba0', 'db7093', 'ffefc3', 'db4d4f', 'ffa07a',
    'd4271e', 'db4d4f', '0000ff', 'bcbcbc', '000000', 'ffaa5f', '9c0027', '091077',
    'fc8114', '2532e4', '93dfe6', '9065d0', 'd082de',
];

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

function extractYear(name) {
    var match = name.match(/^(\d{4})/);
    return match ? parseInt(match[1], 10) : new Date().getFullYear();
}

print('=== M7_03 — LULC Filters ===');
print('Collection IN:  ' + COLL_IN);
print('Collection OUT: ' + COLL_OUT);

createAssetIfNotExists(COLL_OUT);

var images = ee.data.listAssets(COLL_IN).assets.filter(function (a) { return a.type === 'IMAGE'; });

if (images.length === 0) {
    print('Nenhuma imagem encontrada.');
} else {
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
    Map.centerObject(REGIONS);

    // Show LULC once
    Map.addLayer(landcover.select('classification_2024').selfMask(), { min: 0, max: 72, palette: LULC_PALETTE }, 'LULC Peru', false);

    var total = 0;

    images.forEach(function (img) {
        var name = img.id.split('/').pop();
        var eeImg = ee.Image(img.id);
        var year = extractYear(name);

        // Apply LULC mask per region
        var maskedImg = eeImg;
        var removedMask = ee.Image(0);

        Object.keys(masks).forEach(function (regionName) {
            var maskClasses = masks[regionName];
            var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
            var regionRaster = ee.Image(0).paint(regionGeom, 1);

            var lulcMask = landcover
                .select(ee.String('classification_').cat(ee.Number(year).format('%d')))
                .eq(maskClasses)
                .reduce('sum')
                .gte(1);

            // Buffer 90m on water bodies
            CLASSES_AGUA.forEach(function (c) {
                var wb = landcover.select(ee.String('classification_').cat(ee.Number(year).format('%d'))).eq(c).selfMask();
                wb = wb.focalMax({ radius: 90, units: 'meters' }).gte(1);
                lulcMask = lulcMask.blend(wb);
            });

            lulcMask = lulcMask.multiply(regionRaster);
            var finalMask = lulcMask.neq(1);

            maskedImg = maskedImg.updateMask(finalMask);

            // Track removed pixels
            var wasFire = eeImg.updateMask(finalMask.not());
            removedMask = removedMask.where(regionRaster.eq(1), wasFire.select('probability'));
        });

        // Remove solitary pixels (<= 6)
        var connections = maskedImg.select('probability').gt(0).connectedPixelCount({ maxSize: 100, eightConnected: false });
        var solitary = connections.lte(6);
        maskedImg = maskedImg.where(solitary, 0).selfMask();

        maskedImg = maskedImg.copyProperties(eeImg);
        maskedImg = maskedImg.set('filter_stage', 'ft03');

        var destAsset = COLL_OUT + '/' + name;

        Map.addLayer(eeImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['888888'] }, name + ' | BEFORE', false);
        Map.addLayer(removedMask.selfMask(), { min: 0, max: 1000, palette: ['ff0000'] }, name + ' | REMOVED', false);
        Map.addLayer(maskedImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['00cc00'] }, name + ' | AFTER', false);

        try {
            ee.data.getAsset(destAsset);
            print('  OK: ' + name);
        } catch (e) {
            total++;
            print('  Export: ' + name);
            Export.image.toAsset({
                image: maskedImg.toInt16(),
                description: (COLLECTION_BASE + STAGE_OUT + '_' + name).substring(0, 80).replace(/[^a-zA-Z0-9_]/g, '_'),
                assetId: destAsset,
                pyramidingPolicy: 'mode',
                region: REGIONS.geometry().bounds(),
                scale: SCALE,
                maxPixels: 1e13,
            });
        }
    });

    print('Total export: ' + total);
}
print('=== M7_03 done ===');
