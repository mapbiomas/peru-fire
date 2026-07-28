/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8_02
Rastreabilidade dos Filtros (Ganho/Perda por Etapa)

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Para uma fase do M7, carrega todas as etapas (_m7_00 a _m7_04)
2. Compara pares consecutivos (00vs01, 01vs02, etc.)
3. Calcula area ganha e perdida em cada transicao
4. Gera tabela CSV de rastreabilidade

🔧 CONFIGURACAO:
   Altere FASE conforme necessario.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var M7_BASE = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M7_FILTERED';
var SCALE = 10;
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';

// ═══ EDITE AQUI ═══
var FASE = 'fase_agosto_v1';
// ═══════════════════

var PASTA = M7_BASE + '/' + FASE;

// ─── FUNCOES ─────────────────────────────────────────────────────────────────

function _shortName(fullId) { return fullId.split('/').pop(); }

function _extractRegion(name) {
    var parts = name.split('_');
    for (var i = 0; i < parts.length; i++) {
        if (parts[i].indexOf('region') === 0) return parts[i];
    }
    return null;
}

// ─── CALCULAR AREA QUEIMADA ─────────────────────────────────────────────────

function calcBurnedArea(image, regionName) {
    var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
    var areaImage = ee.Image.pixelArea().divide(10000);

    var stats = image.selfMask()
        .gt(0)
        .selfMask()
        .multiply(areaImage)
        .reduceRegion({
            reducer: ee.Reducer.sum(),
            geometry: regionGeom.geometry(),
            scale: SCALE,
            maxPixels: 1e13,
        });

    return stats;
}

// ─── COMPARAR DUAS ETAPAS ───────────────────────────────────────────────────

function compareStages(imgBefore, imgAfter, regionName) {
    var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
    var areaImage = ee.Image.pixelArea().divide(10000);

    // Area queimada antes
    var burnedBefore = imgBefore.selfMask().gt(0).selfMask();
    var areaBefore = areaImage.updateMask(burnedBefore).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: regionGeom.geometry(),
        scale: SCALE,
        maxPixels: 1e13,
    });

    // Area queimada depois
    var burnedAfter = imgAfter.selfMask().gt(0).selfMask();
    var areaAfter = areaImage.updateMask(burnedAfter).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: regionGeom.geometry(),
        scale: SCALE,
        maxPixels: 1e13,
    });

    // Pixels perdidos (estavam antes, nao estao depois)
    var lost = burnedBefore.updateMask(burnedAfter.mask().not());
    var areaLost = areaImage.updateMask(lost).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: regionGeom.geometry(),
        scale: SCALE,
        maxPixels: 1e13,
    });

    // Pixels ganhos (nao estavam antes, estao depois)
    var gained = burnedAfter.updateMask(burnedBefore.mask().not());
    var areaGained = areaImage.updateMask(gained).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: regionGeom.geometry(),
        scale: SCALE,
        maxPixels: 1e13,
    });

    return {
        areaBefore: areaBefore,
        areaAfter: areaAfter,
        areaLost: areaLost,
        areaGained: areaGained,
    };
}

// ─── ENCONTRAR PARES DE ETAPAS ──────────────────────────────────────────────

function findStagePairs(allImages) {
    var baseMap = {};
    allImages.forEach(function (img) {
        var name = img.name;
        var match = name.match(/(.*?)(_m7_(\d+))?(\.tif)?$/);
        if (!match) return;

        var baseName = match[1];
        var suffixNum = match[3] ? parseInt(match[3], 10) : 0;

        if (!baseMap[baseName]) baseMap[baseName] = {};
        baseMap[baseName][suffixNum] = img.id;
    });

    // Para cada base, ordena stages e cria pares consecutivos
    var pairs = [];
    Object.keys(baseMap).forEach(function (baseName) {
        var stages = Object.keys(baseMap[baseName]).map(function (s) { return parseInt(s, 10); }).sort(function (a, b) { return a - b; });
        for (var i = 0; i < stages.length - 1; i++) {
            pairs.push({
                baseName: baseName,
                from: stages[i],
                to: stages[i + 1],
                assetBefore: baseMap[baseName][stages[i]],
                assetAfter: baseMap[baseName][stages[i + 1]],
            });
        }
    });

    return pairs;
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M8_02 — Rastreabilidade dos Filtros ===');
print('Fase: ' + FASE);
print('');

var allImages = ee.data.listAssets(PASTA).assets
    .filter(function (a) { return a.type === 'IMAGE'; })
    .map(function (a) { return { id: a.id, name: _shortName(a.id) }; });

print('Assets na fase: ' + allImages.length);

var pairs = findStagePairs(allImages);
print('Pares de etapas para comparar: ' + pairs.length);

if (pairs.length === 0) {
    print('Nenhum par encontrado. Execute mais de uma etapa M7 para ter comparacao.');
} else {
    var csv = ['fase,base,regiao,etapa_antes,etapa_depois,area_antes_ha,area_depois_ha,ganho_ha,perda_ha,delta_ha,delta_pct'];

    pairs.forEach(function (pair) {
        var region = _extractRegion(pair.baseName);
        var imgBefore = ee.Image(pair.assetBefore);
        var imgAfter = ee.Image(pair.assetAfter);

        print('');
        print('Comparando: ' + pair.baseName);
        print('  m7_0' + pair.from + ' -> m7_0' + pair.to);

        var comparison = compareStages(imgBefore, imgAfter, region);

        var areaBefore = 0;
        var areaAfter = 0;
        var areaLost = 0;
        var areaGained = 0;

        // Extrai valores dos reducers
        var bKey = comparison.areaBefore.keys().get(0);
        var aKey = comparison.areaAfter.keys().get(0);
        var lKey = comparison.areaLost.keys().get(0);
        var gKey = comparison.areaGained.keys().get(0);

        if (bKey) areaBefore = ee.Number(comparison.areaBefore.get(bKey)).getInfo() || 0;
        if (aKey) areaAfter = ee.Number(comparison.areaAfter.get(aKey)).getInfo() || 0;
        if (lKey) areaLost = ee.Number(comparison.areaLost.get(lKey)).getInfo() || 0;
        if (gKey) areaGained = ee.Number(comparison.areaGained.get(gKey)).getInfo() || 0;

        var delta = areaAfter - areaBefore;
        var deltaPct = areaBefore > 0 ? ((delta / areaBefore) * 100).toFixed(1) : '0.0';

        print('  Area antes: ' + areaBefore.toFixed(1) + ' ha');
        print('  Area depois: ' + areaAfter.toFixed(1) + ' ha');
        print('  Ganho: ' + areaGained.toFixed(1) + ' ha');
        print('  Perda: ' + areaLost.toFixed(1) + ' ha');
        print('  Delta: ' + delta.toFixed(1) + ' ha (' + deltaPct + '%)');

        csv.push([
            FASE,
            pair.baseName,
            region || 'unknown',
            'm7_0' + pair.from,
            'm7_0' + pair.to,
            areaBefore.toFixed(1),
            areaAfter.toFixed(1),
            areaGained.toFixed(1),
            areaLost.toFixed(1),
            delta.toFixed(1),
            deltaPct,
        ].join(','));
    });

    print('');
    print('--- CSV de Rastreabilidade (copie para Google Sheets / Looker Studio) ---');
    print(csv.join('\n'));
}

print('');
print('=== M8_02 concluido ===');
