/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_03
Filtros baseados em Classes LULC (Uso e Cobertura do Solo)

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Carrega imagens de uma fase do M7_FILTERED
2. Aplica mascara LULC por regiao (MapBiomas Peru Collection 3)
3. Remove classes nao-queimaveis (agua, area sem vegetacao, afloramento rochoso)
4. Buffer 90m em corpos d'agua
5. Remove pixels solitarios (<= 6 pixels conectados)
6. Salva com sufixo _m7_03
7. Plota: mapa LULC + mascara removida (vermelho) + resultado (verde)

🔧 CONFIGURACAO:
   Altere FASE e SUFIXO_ENTRADA conforme necessario.
   O dicionario 'masks' define classes removidas por regiao.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var M7_BASE = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M7_FILTERED';
var SCALE = 10;
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var ID_PROPERTY = 'id_region';
var GEOMETRY = REGIONS.geometry().bounds();

// ═══ EDITE AQUI ═══
var FASE = 'fase_agosto_v1';          // Nome da pasta
var SUFIXO_ENTRADA = '_m7_02';        // Sufixo da etapa anterior
// ═══════════════════

var PASTA = M7_BASE + '/' + FASE;

// ─── LULC ────────────────────────────────────────────────────────────────────
// MapBiomas Peru Collection 3
var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');

// Classes LULC de interesse:
//  33: Rio, lago u oceano
//  31: Acuicultura
//  34: Glaciar
//  23: Playa
//  24: Infraestructura urbana
//  32: Salina costera
//  61: Salar
//  68: Otra area natural sin vegetacion
//  25: Otra area sin vegetacion
//  29: Afloramiento rocoso

var CLASSES_AGUA = [33, 31, 34];
var CLASSES_SEM_VEG = [23, 24, 32, 61, 68, 25];

// Dicionario de mascaras por regiao
// Classes a serem REMOVIDAS em cada regiao
var masks = {
    'region1':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),          // Todas
    'region2':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),          // Todas
    'region3':  [24, 29],                                       // Apenas infra urbana e afloramento rochoso
    'region4':  [24, 68, 25, 29],                               // Infra urbana + sem veg + afloramento
    'region5':  [29, 24, 68],                                   // Afloramento + infra + sem veg
    'region6':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),          // Todas
    'region7':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),          // Todas
    'region8':  CLASSES_AGUA.concat(CLASSES_SEM_VEG),          // Todas
    'region9':  [25],                                           // Apenas outras areas sem veg
    'region10': [25],                                           // Apenas outras areas sem veg
};

// ─── PALETA LULC (Collection 3) ─────────────────────────────────────────────
var LULC_PALETTE = [
    'ffffff', '32a65e', '32a65e', '1f8d49', '7dc975', '04381d', '026975', '000000',
    '000000', '7a6c00', 'ad975a', '519799', 'd6bc74', 'd89f5c', 'ffffb2', 'edde8e',
    '000000', '000000', 'f5b3c8', 'c27ba0', 'db7093', 'ffefc3', 'db4d4f', 'ffa07a',
    'd4271e', 'db4d4f', '0000ff', 'bcbcbc', '000000', 'ffaa5f', '9c0027', '091077',
    'fc8114', '2532e4', '93dfe6', '9065d0', 'd082de',
];

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

function _extractYear(name) {
    var parts = name.split('_');
    for (var i = 0; i < parts.length; i++) {
        if (/^\d{4}$/.test(parts[i]) && parts[i].length === 4) {
            return parseInt(parts[i], 10);
        }
    }
    return null;
}

// ─── LISTAR IMAGENS ──────────────────────────────────────────────────────────

function listImages(folderPath, suffix) {
    var assets = ee.data.listAssets(folderPath).assets;
    return assets.filter(function (a) {
        var name = _shortName(a.id);
        if (a.type !== 'IMAGE') return false;
        return name.indexOf(suffix + '.') !== -1 ||
               name.indexOf(suffix + '_') !== -1 ||
               name.lastIndexOf(suffix) === name.length - suffix.length;
    }).map(function (a) {
        return { id: a.id, name: _shortName(a.id) };
    });
}

// ─── APLICAR MASCARA LULC ───────────────────────────────────────────────────

function applyLulcMask(image, region, year) {
    var maskClasses = masks[region];
    if (!maskClasses) return image;

    var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, region));
    var regionRaster = ee.Image(0).paint(regionGeom, 1);

    // Mascara LULC base
    var lulcMask = landcover
        .select(ee.String('classification_').cat(ee.Number(year).format('%d')))
        .eq(maskClasses)
        .reduce('sum')
        .gte(1);

    // Buffer de 90m em corpos d'agua
    CLASSES_AGUA.forEach(function (classeAgua) {
        var waterBuffer = landcover
            .select(ee.String('classification_').cat(ee.Number(year).format('%d')))
            .eq(classeAgua)
            .selfMask()
            .focalMax({ radius: 90, units: 'meters' })
            .gte(1);
        lulcMask = lulcMask.blend(waterBuffer);
    });

    // Restringe mascara a regiao
    lulcMask = lulcMask.multiply(regionRaster);

    var finalMask = lulcMask.neq(1);
    var masked = image.updateMask(finalMask);

    // Remove pixels solitarios (<= 6 pixels conectados)
    var connections = masked.connectedPixelCount({ maxSize: 100, eightConnected: false });
    var solitaryPixels = connections.lte(6);
    masked = masked.where(solitaryPixels, 0).selfMask();

    return masked.copyProperties(image);
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M7_03 — Filtros LULC ===');
print('Fase: ' + FASE);
print('Sufixo entrada: ' + SUFIXO_ENTRADA);
print('');

var images = listImages(PASTA, SUFIXO_ENTRADA);
print('Imagens encontradas: ' + images.length);

if (images.length === 0) {
    print('Nenhuma imagem encontrada.');
} else {
    var total = 0;

    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regioes');
    Map.centerObject(REGIONS);

    images.forEach(function (img, idx) {
        var eeImg = ee.Image(img.id);
        var region = _extractRegion(img.name);
        var year = _extractYear(img.name);

        if (!region || !year) {
            print('  [PULAR] Nao foi possivel extrair regiao/ano: ' + img.name);
            return;
        }

        var maskClasses = masks[region];
        if (!maskClasses) {
            print('  [PULAR] Regiao sem configuracao de mascara: ' + region);
            return;
        }

        // Aplica mascara
        var filtered = applyLulcMask(eeImg, region, year);

        // Nome de saida
        var outName = img.name.replace('.tif', '') + '_m7_03';
        var destAsset = PASTA + '/' + outName;

        // Plota
        if (idx === 0) {
            // Plota LULC apenas uma vez
            Map.addLayer(
                landcover.select('classification_' + year).selfMask(),
                { min: 0, max: 72, palette: LULC_PALETTE },
                'LULC ' + year,
                false
            );
        }

        // Mascara removida (onde era fogo e foi removido)
        var pixelsRemovidos = eeImg.updateMask(filtered.mask().not());

        Map.addLayer(eeImg.selfMask(), { min: 0, max: 1, palette: ['888888'] }, img.name + ' | ANTES', false);
        Map.addLayer(pixelsRemovidos, { min: 0, max: 1, palette: ['ff0000'] }, img.name + ' | REMOVIDO', false);
        Map.addLayer(filtered, { min: 0, max: 1, palette: ['00cc00'] }, outName + ' | DEPOIS', false);

        // Exporta
        try {
            ee.data.getAsset(destAsset);
            print('  Ja existe: ' + outName);
        } catch (e) {
            total++;
            print('  Exportando: ' + outName + ' (regiao=' + region + ', classes removidas=' + maskClasses.join(',') + ')');
            Export.image.toAsset({
                image: filtered.toByte(),
                description: outName.substring(0, 80),
                assetId: destAsset,
                pyramidingPolicy: 'mode',
                region: GEOMETRY,
                scale: SCALE,
                maxPixels: 1e13,
            });
        }
    });

    if (total === 0) {
        print('Todos os assets ja existem.');
    } else {
        print('Total de tarefas de export: ' + total);
    }
}

print('');
print('=== M7_03 concluido ===');
print('Legenda: Cinza=ANTES | Vermelho=REMOVIDO | Verde=DEPOIS');
