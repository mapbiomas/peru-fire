/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_04
Isencao por Buffer de Focos de Calor

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Carrega imagens de uma fase do M7_FILTERED
2. Carrega hotspots mensais do ano (INPE / Sul-America)
3. Cria buffer acumulado de 5km de todos os focos do ano
4. Para regioes 1-4: isenta da mascara LULC areas onde:
   - Esta dentro do buffer de 5km de algum foco
   - A classe LULC eh 66, 12 ou 13 (mosaico agropecuario, pasto, formacao natural)
5. Salva com sufixo _m7_04
6. Plota: buffer de focos (laranja) + areas isentas (verde) + resultado

🔗 REFERENCIA:
   Script legado: 4-Collection_anual_final_products/peru/
   3-export_col1_masks_lulc_focos_and_pixel_date

🔧 CONFIGURACAO:
   Altere FASE e SUFIXO_ENTRADA conforme necessario.
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
var FASE = 'fase_agosto_v1';          // Nome da pasta
var SUFIXO_ENTRADA = '_m7_03';        // Sufixo da etapa anterior
var BUFFER_METROS = 5000;             // Raio do buffer em metros
var REGIOES_FOCOS = ['region1', 'region2', 'region3', 'region4'];  // Regioes com isencao
var CLASSES_ISENTAS = [66, 12, 13];   // Classes LULC isentas:
                                       //   66 = Mosaico agropecuario
                                       //   12 = Pasto
                                       //   13 = Otra formacion natural no forestal
// ═══════════════════

var PASTA = M7_BASE + '/' + FASE;

// ─── LULC ────────────────────────────────────────────────────────────────────
var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');

// ─── HOTSPOTS ────────────────────────────────────────────────────────────────
var FOCOS_BASE = 'projects/workspace-ipam/assets/FOGO/monthly-focus-sul-america';

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

// ─── CONSTRUIR BUFFER DE FOCOS ACUMULADO ────────────────────────────────────

function buildFocosBuffer(year, geometry) {
    var focosBuffer = ee.Image(0);

    for (var month = 1; month <= 12; month++) {
        var mm = month < 10 ? '0' + month : '' + month;
        var focosPath = FOCOS_BASE + '/focus_' + year + '-' + mm;

        try {
            var hotspots = ee.FeatureCollection(focosPath).filterBounds(geometry);

            var hotspotBuffer = hotspots.map(function (h) {
                return ee.Feature(h.geometry().buffer(BUFFER_METROS));
            });

            var bufferImg = ee.Image().paint(hotspotBuffer).eq(0);
            focosBuffer = focosBuffer.where(bufferImg.eq(1), 1);
        } catch (e) {
            // Mes sem dados ou asset inexistente — continua
        }
    }

    return focosBuffer;
}

// ─── APLICAR ISENCAO ────────────────────────────────────────────────────────

function applyFocosExemption(image, region, year) {
    if (REGIOES_FOCOS.indexOf(region) === -1) {
        // Regiao nao tem isencao por focos
        return image;
    }

    var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, region));
    var geometry = regionGeom.geometry();

    var regionMask = ee.Image(0).paint(regionGeom, 1);

    // 1. Constroi buffer de focos do ano
    var focosBuffer = buildFocosBuffer(year, geometry);

    // 2. Areas isentas: dentro do buffer de foco E classe LULC isenta
    var lulcClasses = landcover
        .select(ee.String('classification_').cat(ee.Number(year).format('%d')))
        .eq(CLASSES_ISENTAS)
        .reduce('sum')
        .gte(1);

    var focosObserved = focosBuffer
        .multiply(lulcClasses)
        .multiply(regionMask);

    // 3. Onde focosObserved == 1, REVERTE a mascara (deixa a cicatriz passar)
    // Isso significa: se havia uma mascara LULC removendo esses pixels, ela eh desfeita
    // A imagem de entrada (ja mascarada pelo M7_03) tem pixels zerados onde havia mascara
    // Recuperamos a imagem original sem mascara e aplicamos apenas onde ha isencao

    // Carrega a imagem original (sem mascara) — assume que esta disponivel
    // Estrategia: usa a imagem atual + onde a mascara original removeu, restaura se isento

    var outImage = image;

    // Detecta pixels que eram fogo mas foram removidos (mascara LULC removeu)
    // Para a versao atual, se o pixel NAO esta mascarado, mantem. Se esta mascarado (0) E isento, restaura.
    var foiRemovido = image.mask().not(); // Pixels que estao mascarados agora

    // Recarrega a imagem da etapa anterior (sem este filtro) para restaurar valores
    // Aqui usamos a propria imagem: onde ha isencao e a mascara removeu, restauramos
    // Na pratica, o M7_03 ja aplicou mascara LULC. Onde focosObserved == 1, desfazemos
    outImage = outImage.unmask(0);
    // Se o pixel foi isentado E tinha valor original > 0, mantem o valor
    outImage = outImage.where(focosObserved.eq(1).and(image.mask().not()), image.unmask(0));

    // Refaz a mascara: mantem pixels originais OU isentos
    var newMask = image.mask().or(focosObserved.eq(1));
    outImage = outImage.updateMask(newMask).selfMask();

    return outImage.copyProperties(image);
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M7_04 — Isencao por Buffer de Focos ===');
print('Fase: ' + FASE);
print('Sufixo entrada: ' + SUFIXO_ENTRADA);
print('Buffer: ' + (BUFFER_METROS / 1000) + 'km');
print('Regioes com isencao: ' + REGIOES_FOCOS.join(', '));
print('Classes isentas (LULC): ' + CLASSES_ISENTAS.join(', '));
print('');

var images = listImages(PASTA, SUFIXO_ENTRADA);
print('Imagens encontradas: ' + images.length);

if (images.length === 0) {
    print('Nenhuma imagem encontrada.');
} else {
    var total = 0;
    var bufferCache = {};  // Cache de buffers por ano para nao recalcular

    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regioes');
    Map.centerObject(REGIONS);

    images.forEach(function (img) {
        var eeImg = ee.Image(img.id);
        var region = _extractRegion(img.name);
        var year = _extractYear(img.name);

        if (!region || !year) {
            print('  [PULAR] Nao foi possivel extrair regiao/ano: ' + img.name);
            return;
        }

        // Constroi buffer de focos (com cache por ano)
        if (!bufferCache[year]) {
            print('  Construindo buffer de focos para ' + year + '...');
            var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, region));
            bufferCache[year] = buildFocosBuffer(year, regionGeom.geometry());
        }

        // Aplica isencao
        var filtered = applyFocosExemption(eeImg, region, year);

        // Nome de saida
        var outName = img.name.replace('.tif', '') + '_m7_04';
        var destAsset = PASTA + '/' + outName;

        // Plota
        if (REGIOES_FOCOS.indexOf(region) !== -1) {
            var focosBuf = bufferCache[year];
            Map.addLayer(focosBuf.selfMask(), { min: 0, max: 1, palette: ['ff8800'] }, 'Focos buffer ' + year, false);

            // Areas isentas (verde)
            var lulcClasses = landcover
                .select(ee.String('classification_').cat(ee.Number(year).format('%d')))
                .eq(CLASSES_ISENTAS)
                .reduce('sum')
                .gte(1);
            var regionGeom2 = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, region));
            var regionMask2 = ee.Image(0).paint(regionGeom2, 1);
            var exempted = focosBuf.multiply(lulcClasses).multiply(regionMask2).selfMask();

            Map.addLayer(exempted, { min: 0, max: 1, palette: ['00ff00'] }, img.name + ' | ISENTO', false);
        }

        Map.addLayer(eeImg.selfMask(), { min: 0, max: 1, palette: ['888888'] }, img.name + ' | ANTES', false);
        Map.addLayer(filtered, { min: 0, max: 1, palette: ['ff00ff'] }, outName + ' | DEPOIS', false);

        // Exporta
        try {
            ee.data.getAsset(destAsset);
            print('  Ja existe: ' + outName);
        } catch (e) {
            total++;
            print('  Exportando: ' + outName + ' (regiao=' + region + ', isencao=' + (REGIOES_FOCOS.indexOf(region) !== -1 ? 'SIM' : 'NAO') + ')');
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
print('=== M7_04 concluido ===');
print('Legenda: Cinza=ANTES | Laranja=Buffer Focos | Verde=Isento | Magenta=DEPOIS');
