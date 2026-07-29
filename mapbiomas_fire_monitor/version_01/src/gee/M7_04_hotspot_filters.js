/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_04
Isencao por Buffer de Focos de Calor

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 O QUE FAZ:
1. Carrega imagens nacionais da collection -ft03
2. Para regioes 1-4: isenta da mascara LULC areas onde:
   - Esta dentro do buffer de 5km de algum foco de calor
   - A classe LULC eh 66, 12 ou 13
3. Exporta para -ft04

🔗 REF: Collection 1 script 3-export_col1_masks_lulc_focos_and_pixel_date
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;

var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');
var FOCOS_BASE = 'projects/workspace-ipam/assets/FOGO/monthly-focus-sul-america';

// ═══ CONFIG ═══
var COLLECTION_BASE = 'example_propose';
var STAGE_IN = '-ft03';
var STAGE_OUT = '-ft04';
var BUFFER_M = 5000;
var REGIOES_FOCOS = ['region1', 'region2', 'region3', 'region4'];
var CLASSES_ISENTAS = [66, 12, 13];  // Mosaico agro, Pasto, Formacao natural nao florestal
// ═══════════════

var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var PATH_FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var COLL_IN = PATH_FILTERED + COLLECTION_BASE + STAGE_IN;
var COLL_OUT = PATH_FILTERED + COLLECTION_BASE + STAGE_OUT;

var _focosCache = {};

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

function extractYear(name) {
    var match = name.match(/^(\d{4})/);
    return match ? parseInt(match[1], 10) : new Date().getFullYear();
}

function buildFocosBuffer(year, geometry) {
    if (_focosCache[year]) return _focosCache[year];

    var buffer = ee.Image(0);
    for (var m = 1; m <= 12; m++) {
        var mm = m < 10 ? '0' + m : '' + m;
        try {
            var hotspots = ee.FeatureCollection(FOCOS_BASE + '/focus_' + year + '-' + mm).filterBounds(geometry);
            var hb = hotspots.map(function (h) { return ee.Feature(h.geometry().buffer(BUFFER_M)); });
            var img = ee.Image().paint(hb).eq(0);
            buffer = buffer.where(img.eq(1), 1);
        } catch (e) { /* month may not exist */ }
    }
    _focosCache[year] = buffer;
    return buffer;
}

print('=== M7_04 — Hotspot Exemption ===');
print('Collection IN:  ' + COLL_IN);
print('Collection OUT: ' + COLL_OUT);
print('Buffer: ' + (BUFFER_M / 1000) + 'km, Regions: ' + REGIOES_FOCOS.join(','));

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
        var year = extractYear(name);

        var geometry = REGIONS.geometry();
        var focosBuf = buildFocosBuffer(year, geometry);

        // Build exemption: hotspot buffer AND LULC class in [66,12,13]
        var lulcIsentas = landcover
            .select(ee.String('classification_').cat(ee.Number(year).format('%d')))
            .eq(CLASSES_ISENTAS)
            .reduce('sum')
            .gte(1);

        var exemption = ee.Image(0);
        REGIOES_FOCOS.forEach(function (regionName) {
            var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
            var regionRaster = ee.Image(0).paint(regionGeom, 1);
            var regExemption = focosBuf.multiply(lulcIsentas).multiply(regionRaster);
            exemption = exemption.where(regExemption.eq(1), 1);
        });
        exemption = exemption.selfMask();

        // Restore fire pixels where exemption applies
        var outImg = eeImg.unmask(0);
        outImg = outImg.where(exemption.eq(1).and(eeImg.mask().not()), eeImg.unmask(0));
        outImg = outImg.updateMask(eeImg.mask().or(exemption.eq(1))).selfMask();

        outImg = outImg.copyProperties(eeImg);
        outImg = outImg.set('filter_stage', 'ft04');

        var destAsset = COLL_OUT + '/' + name;

        Map.addLayer(focosBuf.selfMask(), { min: 0, max: 1, palette: ['ff8800'] }, 'Hotspot buffer ' + year, false);
        Map.addLayer(exemption, { min: 0, max: 1, palette: ['00ff00'] }, name + ' | EXEMPT', false);
        Map.addLayer(eeImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['888888'] }, name + ' | BEFORE', false);
        Map.addLayer(outImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['ff00ff'] }, name + ' | AFTER', false);

        try {
            ee.data.getAsset(destAsset);
            print('  OK: ' + name);
        } catch (e) {
            total++;
            print('  Export: ' + name);
            Export.image.toAsset({
                image: outImg.toInt16(),
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
print('=== M7_04 done ===');
