/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M9_02
Promover a PRE_PUBLIC

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 O QUE FAZ:
Promove candidato aprovado para PRE_PUBLIC/{campanha}/
Registra metadata completa de proveniencia.
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;

// ═══ CONFIG ═══
var CAMPANHA = 'monitor_01';
var COLLECTION_BASE = 'propose_a';
var PERIOD = '2025_08';
var APROVADOR = '';
var FASE_FILTROS = '-ft00,-ft01,-ft02,-ft03,-ft04';
// ═══════════════

var PATH_CANDIDATES = CLASSIFICATIONS_ROOT + 'CANDIDATES/';
var PATH_PRE_PUBLIC = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/PRE_PUBLIC/';

var SRC = PATH_CANDIDATES + COLLECTION_BASE + '/' + PERIOD;
var DEST_COLL = PATH_PRE_PUBLIC + CAMPANHA;
var DEST = DEST_COLL + '/' + PERIOD;

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

print('=== M9_02 — Promote to PRE_PUBLIC ===');
print('Source: ' + SRC);
print('Target: ' + DEST);

ensureFolder('PRE_PUBLIC');
ensureFolder('PRE_PUBLIC/'+CAMPANHA);

try {
    ee.data.getAsset(SRC);
} catch (e) {
    print('ERRO: Source not found: ' + SRC);
}

try {
    ee.data.getAsset(DEST);
    print('Already exists: ' + DEST);
} catch (e) {
    var img = ee.Image(SRC);
    var approvalDate = new Date().toISOString().split('T')[0];

    var promoted = img.set({
        'source': 'mapbiomas-fuego-monitor',
        'campaign': CAMPANHA,
        'source_candidate': SRC,
        'filter_stages': FASE_FILTROS,
        'approver': APROVADOR || 'nao_informado',
        'approval_date': approvalDate,
        'status': 'PRE_PUBLIC',
    });

    Export.image.toAsset({
        image: promoted.toInt16(),
        description: ('prepub_' + PERIOD).substring(0, 80),
        assetId: DEST,
        pyramidingPolicy: 'mode',
        region: REGIONS.geometry().bounds(),
        scale: SCALE,
        maxPixels: 1e13,
    });

    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
    Map.addLayer(img.select('probability').selfMask(), { min: 0, max: 1000, palette: ['00ff00'] }, 'PRE_PUBLIC: ' + PERIOD, false);
    Map.centerObject(REGIONS);

    print('Export task created. Check Tasks tab.');
    print('Metadata:');
    print('  approver: ' + (APROVADOR || 'nao_informado'));
    print('  approval_date: ' + approvalDate);
    print('  filter_stages: ' + FASE_FILTROS);
}
print('=== M9_02 done ===');
