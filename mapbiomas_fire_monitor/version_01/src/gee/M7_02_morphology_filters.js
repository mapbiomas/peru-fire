/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_02
Filtros Morfologicos (Abertura/Fechamento)

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Carrega imagens de uma fase do M7_FILTERED
2. Aplica abertura (focalMin) e fechamento (focalMax)
3. Remove ruido isolado e fecha buracos
4. Salva com sufixo _m7_02
5. Plota antes (cinza) e depois (colorido) no mapa

🔧 CONFIGURACAO:
   Altere as variaveis abaixo conforme necessario.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var M7_BASE = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M7_FILTERED';
var SCALE = 10;
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var GEOMETRY = REGIONS.geometry().bounds();

// ═══ EDITE AQUI ═══
var FASE = 'fase_agosto_v1';          // Nome da pasta em M7_FILTERED
var SUFIXO_ENTRADA = '_m7_01';        // Sufixo da etapa anterior ('' para pegar do M7_00)
var RAIO_ABERTURA = 1;                // Raio em pixels para focalMin (remove ruido) — 1 pixel = 10m
var RAIO_FECHAMENTO = 2;              // Raio em pixels para focalMax (fecha buracos) — 2 pixels = 20m
var POR_REGIAO = false;               // true = aplica mascara por regiao, false = nacional
// ═══════════════════

var PASTA = M7_BASE + '/' + FASE;

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

// ─── LISTAR IMAGENS ──────────────────────────────────────────────────────────

function listImages(folderPath, suffix) {
    var assets = ee.data.listAssets(folderPath).assets;
    return assets.filter(function (a) {
        var name = _shortName(a.id);
        if (a.type !== 'IMAGE') return false;

        if (suffix === '') {
            // Pega imagens sem sufixo _m7_ (do M7_00)
            return name.indexOf('_m7_') === -1;
        } else {
            // Pega imagens com o sufixo especifico
            return name.indexOf(suffix + '.') !== -1 || name.indexOf(suffix + '_') !== -1 || name.lastIndexOf(suffix) === name.length - suffix.length;
        }
    }).map(function (a) {
        return { id: a.id, name: _shortName(a.id) };
    });
}

// ─── MORFOLOGIA ──────────────────────────────────────────────────────────────

function applyMorphology(image) {
    var openRadius = RAIO_ABERTURA;
    var closeRadius = RAIO_FECHAMENTO;

    // Abertura: focalMin (erosao) -> focalMax (dilatacao)
    var opened = image.focalMin({ radius: openRadius, kernelType: 'circle', units: 'pixels' });
    opened = opened.focalMax({ radius: openRadius, kernelType: 'circle', units: 'pixels' });

    // Fechamento: focalMax (dilatacao) -> focalMin (erosao)
    var closed = opened.focalMax({ radius: closeRadius, kernelType: 'circle', units: 'pixels' });
    closed = closed.focalMin({ radius: closeRadius, kernelType: 'circle', units: 'pixels' });

    return closed.selfMask().copyProperties(image);
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M7_02 — Filtros Morfologicos ===');
print('Fase: ' + FASE);
print('Sufixo entrada: ' + (SUFIXO_ENTRADA || '(M7_00)'));
print('Raio abertura: ' + RAIO_ABERTURA + 'px | Raio fechamento: ' + RAIO_FECHAMENTO + 'px');
print('');

var images = listImages(PASTA, SUFIXO_ENTRADA);
print('Imagens encontradas: ' + images.length);

if (images.length === 0) {
    print('Nenhuma imagem encontrada. Verifique FASE e SUFIXO_ENTRADA.');
} else {
    var total = 0;

    // Mapa base
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regioes');
    Map.centerObject(REGIONS);

    images.forEach(function (img, idx) {
        var eeImg = ee.Image(img.id);
        var region = _extractRegion(img.name);

        // Aplica morfologia
        var filtered;

        if (POR_REGIAO && region) {
            var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, region));
            var regionMask = ee.Image(0).paint(regionGeom, 1);
            // Aplica filtro apenas dentro da regiao
            var masked = eeImg.updateMask(regionMask);
            filtered = applyMorphology(masked);
            // Reaplica mascara da regiao
            filtered = filtered.updateMask(regionMask);
        } else {
            filtered = applyMorphology(eeImg);
        }

        // Nome de saida
        var outName = img.name.replace('.tif', '') + '_m7_02';
        var destAsset = PASTA + '/' + outName;

        // Plota: antes (cinza) e depois (azul)
        Map.addLayer(eeImg.selfMask(), { min: 0, max: 1, palette: ['888888'] }, img.name + ' | ANTES', false);
        Map.addLayer(filtered, { min: 0, max: 1, palette: ['0044ff'] }, outName + ' | DEPOIS', false);

        // Exporta
        try {
            ee.data.getAsset(destAsset);
            print('  Ja existe: ' + outName);
        } catch (e) {
            total++;
            print('  Exportando: ' + outName);
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
print('=== M7_02 concluido ===');
print('Legenda do mapa: Cinza = ANTES | Azul = DEPOIS');
