/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_02
Filtros Morfologicos (Abertura/Fechamento)

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 O QUE FAZ:
1. Carrega imagens nacionais da collection -ft01
2. Aplica abertura (focalMin) e fechamento (focalMax)
3. Exporta para -ft02
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;

// ═══ CONFIG ═══
var COLLECTION_BASE = 'propose_a';
var STAGE_IN = '-ft00';
var STAGE_OUT = '-ft01';
var RAIO_ABERTURA = 1;    // pixels (1px = 10m)
var RAIO_FECHAMENTO = 2;  // pixels (2px = 20m)
// ═══════════════

var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var PATH_FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var COLL_IN = PATH_FILTERED + COLLECTION_BASE + STAGE_IN;
var COLL_OUT = PATH_FILTERED + COLLECTION_BASE + STAGE_OUT;

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

print('=== M7_02 — Morphology ===');
print('Collection IN:  ' + COLL_IN);
print('Collection OUT: ' + COLL_OUT);
print('Abertura: ' + RAIO_ABERTURA + 'px / Fechamento: ' + RAIO_FECHAMENTO + 'px');

ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_OUT);

var images = ee.data.listAssets(COLL_IN).assets.filter(function (a) { return a.type === 'IMAGE'; });

if (images.length === 0) {
    print('Nenhuma imagem encontrada.');
} else {
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
    Map.centerObject(REGIONS);

    var total = 0;
    images.forEach(function (img) {
        var name = img.id.split('/').pop();
        var eeImg = ee.Image(img.id);

        // Opening (erode then dilate): remove isolated noise
        var opened = eeImg.focalMin({ radius: RAIO_ABERTURA, kernelType: 'circle', units: 'pixels' });
        opened = opened.focalMax({ radius: RAIO_ABERTURA, kernelType: 'circle', units: 'pixels' });

        // Closing (dilate then erode): fill small holes
        var closed = opened.focalMax({ radius: RAIO_FECHAMENTO, kernelType: 'circle', units: 'pixels' });
        closed = closed.focalMin({ radius: RAIO_FECHAMENTO, kernelType: 'circle', units: 'pixels' });

        closed = closed.selfMask().copyProperties(eeImg);
        closed = closed.set('filter_stage', 'ft02');

        var destAsset = COLL_OUT + '/' + name;

        Map.addLayer(eeImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['888888'] }, name + ' | BEFORE', false);
        Map.addLayer(closed.select('probability').selfMask(), { min: 0, max: 1000, palette: ['0044ff'] }, name + ' | AFTER', false);

        try {
            ee.data.getAsset(destAsset);
            print('  OK: ' + name);
        } catch (e) {
            total++;
            print('  Export: ' + name);
            Export.image.toAsset({
                image: closed.toInt16(),
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
print('=== M7_02 done ===');
