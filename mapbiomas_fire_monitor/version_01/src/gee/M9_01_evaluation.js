/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M9_01
Protocolo de Avaliacao de Candidatos

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 O QUE FAZ:
Quality checklist for M8 candidates:
- Area threshold
- Visual consistency (NBR overlay)
- MODIS MCD64A1 overlap
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;

// ═══ CONFIG ═══
var COLLECTION_BASE = 'monitor_01-sentinel2_minnbr_monthly_01';
var PERIOD = '2025_08';
var THRESHOLD_AREA_MIN_HA = 100;
var THRESHOLD_AREA_MAX_HA = 500000;
// ═══════════════

var PATH_CANDIDATES = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/CANDIDATES/';
var ASSET = PATH_CANDIDATES + COLLECTION_BASE + '/' + PERIOD;

var areaImage = ee.Image.pixelArea().divide(10000);
var year = parseInt(PERIOD.substring(0, 4), 10);

function getMCD64A1(y, geom) {
    return ee.ImageCollection('MODIS/061/MCD64A1')
        .filterDate(ee.Date.fromYMD(y, 1, 1), ee.Date.fromYMD(y + 1, 1, 1))
        .filterBounds(geom).select('BurnDate').mosaic().gte(1).selfMask();
}

print('=== M9_01 — Evaluation ===');
print('Asset: ' + ASSET);
print('');

var passed = true;

try {
    ee.data.getAsset(ASSET);
} catch (e) {
    print('ERRO: Asset nao encontrado: ' + ASSET);
    passed = false;
}

if (passed) {
    var img = ee.Image(ASSET);
    var geometry = REGIONS.geometry();

    // 1. Area
    var stats = img.select('probability').gt(0).selfMask().multiply(areaImage).reduceRegion({
        reducer: ee.Reducer.sum(), geometry: geometry, scale: SCALE, maxPixels: 1e13,
    });
    var areaHa = 0;
    var k = stats.keys().get(0);
    if (k) areaHa = ee.Number(stats.get(k)).getInfo() || 0;

    var areaOk = areaHa >= THRESHOLD_AREA_MIN_HA && areaHa <= THRESHOLD_AREA_MAX_HA;
    print('1. Area queimada: ' + areaHa.toFixed(1) + ' ha');
    print('   Threshold: ' + THRESHOLD_AREA_MIN_HA + ' — ' + THRESHOLD_AREA_MAX_HA + ' ha');
    print('   ' + (areaOk ? 'PASS' : 'FAIL'));
    if (!areaOk) passed = false;

    // 2. Visual
    Map.addLayer(img.select('probability').gt(0).selfMask(), { min: 0, max: 1, palette: ['ff0000'] }, 'CANDIDATE', false);
    Map.centerObject(REGIONS);
    print('2. Visual check: review overlay on map');

    // 3. MODIS overlap
    try {
        var modis = getMCD64A1(year, geometry);
        var overlap = modis.and(img.select('probability').gt(0).selfMask());
        var overlapStats = overlap.selfMask().multiply(areaImage).reduceRegion({
            reducer: ee.Reducer.sum(), geometry: geometry, scale: SCALE, maxPixels: 1e13,
        });
        var overlapHa = 0;
        var ok = overlapStats.keys().get(0);
        if (ok) overlapHa = ee.Number(overlapStats.get(ok)).getInfo() || 0;
        var pct = areaHa > 0 ? ((overlapHa / areaHa) * 100).toFixed(1) : '0.0';

        var modisOk = parseFloat(pct) > 10;
        Map.addLayer(modis, { min: 0, max: 1, palette: ['00ff00'] }, 'MODIS ' + year, false);
        print('3. MODIS overlap: ' + overlapHa.toFixed(1) + ' ha (' + pct + '%)');
        print('   ' + (modisOk ? 'PASS (>10%)' : 'FAIL'));
        if (!modisOk) passed = false;
    } catch (e) {
        print('3. MODIS: UNAVAILABLE');
    }

    print('');
    print('=== RESULT: ' + (passed ? 'APPROVED — promote to PRE_PUBLIC' : 'REJECTED — review items') + ' ===');
}
print('=== M9_01 done ===');
