/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_01
Merge de Classificacoes
 
📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM
   Wallace Silva, Vera Arruda

📌 O QUE FAZ:
1. Carrega imagens de uma pasta do M7_FILTERED
2. Para cada regiao com 2+ classificacoes, faz merge pixel-level
3. Salva resultado com sufixo _m7_01
4. Plota antes (versoes originais) e depois (unificado) no mapa

🔧 CONFIGURACAO:
   Altere as variaveis abaixo conforme necessario.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONAL_FOLDER = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/REGIONAL';
var M7_BASE = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M7_FILTERED';
var SCALE = 10;
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';

// ═══ EDITE AQUI ═══
var FASE = 'fase_agosto_v1';  // Nome da pasta em M7_FILTERED
// ═══════════════════

var PASTA_ENTRADA = M7_BASE + '/' + FASE;
var GEOMETRY = REGIONS.geometry().bounds();

// ─── PALETA DE CLASSIFICACAO ───────────────────────────────────────────────
var CLASS_PALETTE = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
    '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
];

// ─── FUNCOES ─────────────────────────────────────────────────────────────────

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try {
        ee.data.getAsset(assetId);
    } catch (e) {
        ee.data.createAsset({ type: type }, assetId);
    }
}

function _shortName(fullId) {
    return fullId.split('/').pop();
}

function _extractRegion(name) {
    var parts = name.split('_');
    for (var i = 0; i < parts.length; i++) {
        if (parts[i].indexOf('region') === 0) return parts[i];
    }
    return null;
}

function _removeSuffix(name) {
    // Remove sufixos _m7_0N se existirem
    return name.replace(/_m7_\d+$/, '');
}

// ─── LISTAR IMAGENS ──────────────────────────────────────────────────────────

function listImages(folderPath) {
    var assets = ee.data.listAssets(folderPath).assets;
    return assets.filter(function (a) {
        return a.type === 'IMAGE';
    }).map(function (a) {
        var name = _shortName(a.id);
        var region = _extractRegion(name);
        return {
            id: a.id,
            name: name,
            region: region,
        };
    });
}

// ─── AGRUPAR POR REGIAO ─────────────────────────────────────────────────────

function groupByRegion(images) {
    var groups = {};
    images.forEach(function (img) {
        var region = img.region;
        if (!region) return;
        // Ignora imagens que ja tem sufixo de filtro
        if (img.name.indexOf('_m7_') !== -1) return;
        if (!groups[region]) groups[region] = [];
        groups[region].push(img);
    });
    return groups;
}

// ─── MERGE ──────────────────────────────────────────────────────────────────

function mergeImages(imageList, region) {
    var base = ee.Image(0).rename('b1');
    imageList.forEach(function (img) {
        var eeImg = ee.Image(img.id);
        // Preserva pixels queimados (> 0) de cada versao
        base = base.where(eeImg.gt(0), eeImg);
    });
    base = base.selfMask();

    var firstImg = ee.Image(imageList[0].id);
    base = base.copyProperties(firstImg);

    var outName = 'merged_' + region + '_' + _removeSuffix(_shortName(imageList[0].id));
    return { image: base, outName: outName };
}

// ─── PLOT ───────────────────────────────────────────────────────────────────

function plotResults(groups) {
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regioes');
    Map.centerObject(REGIONS);

    var layerIdx = 0;
    Object.keys(groups).sort().forEach(function (region) {
        var imgs = groups[region];
        if (imgs.length < 2) return;

        print('--- ' + region + ' (' + imgs.length + ' versoes) ---');

        // Plota versoes originais (tons de cinza/laranja)
        imgs.forEach(function (img, i) {
            var label = region + ' | original ' + (i + 1) + ': ' + img.name;
            Map.addLayer(ee.Image(img.id).selfMask(), {
                min: 0, max: 1,
                palette: [i === 0 ? '#555555' : '#ffaa00']
            }, label, false);
            print('  Original ' + (i + 1) + ': ' + img.name);
        });

        // Faz o merge
        var merged = mergeImages(imgs, region);
        Map.addLayer(merged.image, { min: 0, max: 1, palette: ['ff0000'] }, region + ' | MERGEADO', false);
        print('  Mergeado: ' + merged.outName);

        layerIdx++;
    });

    // Legenda
    var legend = ui.Panel({
        style: { position: 'bottom-left', padding: '8px', backgroundColor: 'rgba(255,255,255,0.9)' }
    });
    legend.add(ui.Label('Legenda:', { fontWeight: 'bold', fontSize: '12px' }));
    legend.add(ui.Label('Cinza = Original v1', { color: '#555555', fontSize: '11px' }));
    legend.add(ui.Label('Laranja = Original v2', { color: '#ffaa00', fontSize: '11px' }));
    legend.add(ui.Label('Vermelho = Mergeado', { color: '#ff0000', fontSize: '11px', fontWeight: 'bold' }));
    Map.add(legend);
}

// ─── EXPORT ─────────────────────────────────────────────────────────────────

function exportMerged(groups) {
    var total = 0;
    Object.keys(groups).forEach(function (region) {
        var imgs = groups[region];
        if (imgs.length < 2) return;

        var merged = mergeImages(imgs, region);
        var destAsset = M7_BASE + '/' + FASE + '/' + merged.outName + '_m7_01';

        try {
            ee.data.getAsset(destAsset);
            print('  Ja existe: ' + destAsset);
        } catch (e) {
            total++;
            print('  Exportando: ' + destAsset);
            Export.image.toAsset({
                image: merged.image.toByte(),
                description: merged.outName.substring(0, 80),
                assetId: destAsset,
                pyramidingPolicy: 'mode',
                region: GEOMETRY,
                scale: SCALE,
                maxPixels: 1e13,
            });
        }
    });

    if (total === 0) {
        print('Nenhuma regiao com 2+ versoes para mergear.');
    } else {
        print('Total de tarefas de export: ' + total);
    }
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M7_01 — Merge de Classificacoes ===');
print('Pasta: ' + PASTA_ENTRADA);
print('');

// 1. Lista imagens da pasta
var allImages = listImages(PASTA_ENTRADA);
print('Imagens encontradas: ' + allImages.length);

// 2. Agrupa por regiao
var groups = groupByRegion(allImages);
var mergeCount = 0;
Object.keys(groups).forEach(function (r) {
    if (groups[r].length >= 2) mergeCount++;
});

print('Regioes com 2+ versoes (merge necessario): ' + mergeCount);

if (mergeCount === 0) {
    print('Nada a mergear. Script concluido.');
} else {
    // 3. Plota resultados no mapa
    plotResults(groups);

    // 4. Exporta
    print('');
    print('--- Export ---');
    exportMerged(groups);
}

print('');
print('=== M7_01 concluido ===');
