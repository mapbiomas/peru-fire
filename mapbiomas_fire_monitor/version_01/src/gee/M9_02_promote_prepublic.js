/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M9_02
Promover a PRE_PUBLIC

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Recebe candidato aprovado pelo M9_01
2. Copia para ImageCollection M9_PRE_PUBLIC/
3. Registra metadata completa de proveniencia
4. Plota resultado no mapa

🔧 CONFIGURACAO:
   Altere CANDIDATO_ID e metadados de aprovacao.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var M8_CANDIDATES = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M8_CANDIDATES';
var M9_PRE_PUBLIC = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M9_PRE_PUBLIC';
var SCALE = 10;
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var GEOMETRY = REGIONS.geometry().bounds();

// ═══ EDITE AQUI ═══
var CANDIDATO_ID = M8_CANDIDATES + '/training_0001_selva_region3_2025_08_candidate';
var APROVADOR = '';  // Nome ou email de quem aprovou
var FASE_M7 = 'fase_agosto_v1';
var ETAPAS_FILTRO = ['m7_00', 'm7_01', 'm7_02', 'm7_03', 'm7_04'];
// ═══════════════════

// ─── FUNCOES ─────────────────────────────────────────────────────────────────

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

function _shortName(fullId) { return fullId.split('/').pop(); }

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M9_02 — Promover a PRE_PUBLIC ===');
print('Candidato: ' + CANDIDATO_ID);
print('');

// Verifica se candidato existe
try {
    ee.data.getAsset(CANDIDATO_ID);
} catch (e) {
    print('ERRO: Candidato nao encontrado: ' + CANDIDATO_ID);
    print('=== M9_02 abortado ===');
}

// Cria pasta de destino
createAssetIfNotExists(M9_PRE_PUBLIC);

var name = _shortName(CANDIDATO_ID);
var prePublicName = name.replace('_candidate', '_prepublic');
var destAsset = M9_PRE_PUBLIC + '/' + prePublicName;

// Verifica se ja existe
try {
    ee.data.getAsset(destAsset);
    print('Ja existe em PRE_PUBLIC: ' + destAsset);
    print('Para substituir, delete o asset manualmente e rode novamente.');
} catch (e) {
    print('Promovendo: ' + prePublicName);
    print('Origem: ' + CANDIDATO_ID);
    print('Destino: ' + destAsset);

    var img = ee.Image(CANDIDATO_ID);
    var approvalDate = new Date().toISOString().split('T')[0];

    // Metadata completa de proveniencia
    var metadata = {
        'source': 'mapbiomas-fuego-monitor',
        'campaign': CAMPAIGN,
        'source_candidate': CANDIDATO_ID,
        'm7_phase': FASE_M7,
        'm7_filters': ETAPAS_FILTRO.join(','),
        'approver': APROVADOR || 'nao_informado',
        'approval_date': approvalDate,
        'status': 'PRE_PUBLIC',
        'pipeline_version': '1.0',
    };

    var exportedImg = img.set(metadata).toByte();

    Export.image.toAsset({
        image: exportedImg,
        description: prePublicName.substring(0, 80),
        assetId: destAsset,
        pyramidingPolicy: 'mode',
        region: GEOMETRY,
        scale: SCALE,
        maxPixels: 1e13,
    });

    print('');
    print('Metadata registrada:');
    Object.keys(metadata).forEach(function (k) {
        print('  ' + k + ': ' + metadata[k]);
    });

    // Plota no mapa
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regioes');
    Map.addLayer(img.selfMask(), { min: 0, max: 1, palette: ['00ff00'] }, 'PRE_PUBLIC: ' + prePublicName, false);
    Map.centerObject(REGIONS);

    print('');
    print('Tarefa de export criada. Va para a aba Tasks e execute.');
}

print('');
print('=== M9_02 concluido ===');
