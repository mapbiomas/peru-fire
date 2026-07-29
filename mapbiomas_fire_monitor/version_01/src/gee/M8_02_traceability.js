/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8_02
Rastreabilidade dos Filtros (Ganho/Perda por Etapa)

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 O QUE FAZ:
Compara etapas de filtro consecutivas e calcula ganho/perda de area.
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;

// ═══ CONFIG ═══
var COLLECTION_BASE = 'propose_a';
var STAGES = ['-ft00', '-ft01', '-ft02', '-ft03'];
var PERIOD = '2025_08';
// ═══════════════

var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var PATH_FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var areaImage = ee.Image.pixelArea().divide(10000);

function calcBurnedArea(assetId) {
    var img = ee.Image(assetId).select('probability').gt(0).selfMask();
    var stats = img.multiply(areaImage).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: REGIONS.geometry(),
        scale: SCALE,
        maxPixels: 1e13,
    });
    var k = stats.keys().get(0);
    return k ? ee.Number(stats.get(k)).getInfo() || 0 : 0;
}

print('=== M8_02 — Traceability ===');
print('Collection: ' + COLLECTION_BASE);
print('Period: ' + PERIOD);
print('');

var csv = ['etapa_antes,etapa_depois,area_antes_ha,area_depois_ha,ganho_ha,perda_ha,delta_ha,delta_pct'];

for (var i = 0; i < STAGES.length - 1; i++) {
    var assetBefore = PATH_FILTERED + COLLECTION_BASE + STAGES[i] + '/' + PERIOD;
    var assetAfter = PATH_FILTERED + COLLECTION_BASE + STAGES[i + 1] + '/' + PERIOD;

    var areaBefore = 0;
    var areaAfter = 0;

    try {
        ee.data.getAsset(assetBefore);
        areaBefore = calcBurnedArea(assetBefore);
    } catch (e) {
        print('  [SKIP] Not found: ' + STAGES[i]);
        continue;
    }

    try {
        ee.data.getAsset(assetAfter);
        areaAfter = calcBurnedArea(assetAfter);
    } catch (e) {
        print('  [SKIP] Not found: ' + STAGES[i + 1]);
        continue;
    }

    var delta = areaAfter - areaBefore;
    var deltaPct = areaBefore > 0 ? ((delta / areaBefore) * 100).toFixed(1) : '0.0';

    print(STAGES[i] + ' -> ' + STAGES[i + 1]);
    print('  ' + areaBefore.toFixed(1) + ' ha -> ' + areaAfter.toFixed(1) + ' ha | delta: ' + delta.toFixed(1) + ' ha (' + deltaPct + '%)');

    csv.push([STAGES[i], STAGES[i + 1], areaBefore.toFixed(1), areaAfter.toFixed(1), '-', '-', delta.toFixed(1), deltaPct].join(','));
}

print('');
print('--- CSV ---');
print(csv.join('\n'));
print('=== M8_02 done ===');
