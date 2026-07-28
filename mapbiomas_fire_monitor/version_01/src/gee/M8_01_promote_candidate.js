/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8_01
Promover a Candidato

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Seleciona fase/versao do M7
2. Copia versao final (maior sufixo _m7_0N) para M8_CANDIDATES/
3. Calcula area queimada por regiao (ha)
4. Registra metadata de proveniencia

🔧 CONFIGURACAO:
   Altere FASE para indicar qual fase M7 promover.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var M7_BASE = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M7_FILTERED';
var M8_CANDIDATES = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M8_CANDIDATES';
var SCALE = 10;
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var GEOMETRY = REGIONS.geometry().bounds();

// ═══ EDITE AQUI ═══
var FASE = 'fase_agosto_v1';  // Nome da fase M7 a promover
// ═══════════════════

var PASTA_ENTRADA = M7_BASE + '/' + FASE;

// ─── FUNCOES ─────────────────────────────────────────────────────────────────

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

function _shortName(fullId) { return fullId.split('/').pop(); }

function _extractRegion(name) {
    var parts = name.split('_');
    for (var i = 0; i < parts.length; i++) {
        if (parts[i].indexOf('region') === 0) return parts[i];
    }
    return null;
}

// ─── ENCONTRAR ULTIMA ETAPA DE FILTRO ───────────────────────────────────────

function findLatestStage(images) {
    // Agrupa por regiao+periodo (base) e encontra maior sufixo _m7_0N
    var baseMap = {};
    images.forEach(function (img) {
        var name = img.name;
        var match = name.match(/(.*?)(_m7_\d+)?(\.tif)?$/);
        if (!match) return;

        var baseName = match[1];
        var suffix = match[2] || '_m7_00';

        if (!baseMap[baseName]) {
            baseMap[baseName] = { name: img.name, suffixNum: 0, assetId: img.id };
        }

        var num = parseInt(suffix.replace('_m7_', ''), 10) || 0;
        if (num > baseMap[baseName].suffixNum) {
            baseMap[baseName] = { name: img.name, suffixNum: num, assetId: img.id };
        }
    });

    return baseMap;
}

function _extractPeriod(name) {
    // Extrai YYYY ou YYYY_MM do nome
    var parts = name.split('_');
    for (var i = 0; i < parts.length; i++) {
        if (/^\d{4}$/.test(parts[i]) && parts[i].length === 4) {
            if (i + 1 < parts.length && /^\d{2}$/.test(parts[i + 1]) && parts[i + 1].length === 2) {
                return parts[i] + '_' + parts[i + 1];
            }
            return parts[i];
        }
    }
    return 'unknown';
}

// ─── CALCULAR AREA QUEIMADA ─────────────────────────────────────────────────

function calcBurnedArea(image, regionName) {
    var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
    var areaImage = ee.Image.pixelArea().divide(10000); // m2 -> ha

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

    return ee.Number(stats.get(ee.String(stats.keys().get(0))));
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M8_01 — Promover a Candidato ===');
print('Fase M7: ' + FASE);
print('');

createAssetIfNotExists(M8_CANDIDATES);

var allImages = ee.data.listAssets(PASTA_ENTRADA).assets
    .filter(function (a) { return a.type === 'IMAGE'; })
    .map(function (a) { return { id: a.id, name: _shortName(a.id) }; });

print('Total de assets na fase: ' + allImages.length);

// Encontra ultima etapa de cada base
var latest = findLatestStage(allImages);
var latestList = Object.keys(latest).map(function (k) { return latest[k]; });

print('Assets na ultima etapa: ' + latestList.length);

if (latestList.length === 0) {
    print('Nenhum asset encontrado.');
} else {
    var total = 0;
    var statsCsv = ['model_id,region,period,area_queimada_ha,etapa_filtro,data_promocao,fase_origem'];

    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regioes');
    Map.centerObject(REGIONS);

    latestList.forEach(function (item) {
        var name = item.name;
        var region = _extractRegion(name);
        var period = _extractPeriod(name);

        // Nome do candidato: remove sufixo _m7_0N, adiciona _candidate
        var candidateName = name.replace(/_m7_\d+/, '') + '_candidate';
        var destAsset = M8_CANDIDATES + '/' + candidateName;

        var eeImg = ee.Image(item.assetId);

        // Calcula area queimada
        var areaHa = calcBurnedArea(eeImg, region);

        areaHa.evaluate(function (val) {
            areaHa = val || 0;
        });

        // Plota candidato no mapa
        Map.addLayer(eeImg.selfMask(), { min: 0, max: 1, palette: ['3355ff'] }, candidateName + ' | CANDIDATO', false);

        // Exporta copia para M8_CANDIDATES
        try {
            ee.data.getAsset(destAsset);
            print('  Ja existe: ' + candidateName);
        } catch (e) {
            total++;
            print('  Promovendo: ' + candidateName);

            var metadata = {
                'source_fase': FASE,
                'source_asset': item.assetId,
                'filtro_etapa': 'm7_0' + item.suffixNum,
                'promotion_date': new Date().toISOString().split('T')[0],
                'campaign': CAMPAIGN,
            };

            var exportedImg = eeImg.set(metadata).toByte();

            Export.image.toAsset({
                image: exportedImg,
                description: candidateName.substring(0, 80),
                assetId: destAsset,
                pyramidingPolicy: 'mode',
                region: GEOMETRY,
                scale: SCALE,
                maxPixels: 1e13,
            });
        }

        // Acumula estatisticas
        var modelId = name.split('_' + region)[0] || 'unknown';
        statsCsv.push([modelId, region, period, 'PENDING', 'm7_0' + item.suffixNum, new Date().toISOString().split('T')[0], FASE].join(','));
    });

    // Exibe CSV de estatisticas no console (para copiar para Google Sheets)
    print('');
    print('--- CSV de Area Queimada (copie para Google Sheets / Looker Studio) ---');
    print(statsCsv.join('\n'));

    if (total === 0) {
        print('');
        print('Todos os candidatos ja existem.');
    } else {
        print('');
        print('Total de tarefas de export: ' + total);
    }
}

print('');
print('=== M8_01 concluido ===');
