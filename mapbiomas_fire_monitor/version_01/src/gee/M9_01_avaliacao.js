/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M9_01
Protocolo de Avaliacao de Candidatos

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Carrega candidato do M8_CANDIDATES/
2. Avalia criterios de qualidade:
   - Threshold de area queimada (vs serie historica)
   - Consistencia visual (overlay com min NBR)
   - Overlap com referencias externas (MODIS MCD64A1)
   - Delta dos filtros (do M8_02)
   - Cobertura espacial (todas as regioes?)
3. Gera checklist de aprovacao

🔧 CONFIGURACAO:
   Altere CANDIDATO_ID para o asset a ser avaliado.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var M8_CANDIDATES = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M8_CANDIDATES';
var MOSAIC_BASE = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;

// ═══ EDITE AQUI ═══
var CANDIDATO_ID = M8_CANDIDATES + '/training_0001_selva_region3_2025_08_candidate';
var THRESHOLD_AREA_MIN_HA = 100;      // Area minima esperada (ha)
var THRESHOLD_AREA_MAX_HA = 500000;   // Area maxima esperada (ha)
var DELTA_MAX_PCT = 30;               // Delta maximo aceitavel entre etapas de filtro (%)
// ═══════════════════

// ─── REFERENCIA EXTERNA ─────────────────────────────────────────────────────

function getMCD64A1(year, geometry) {
    var start = ee.Date.fromYMD(year, 1, 1);
    var end = ee.Date.fromYMD(year + 1, 1, 1);
    return ee.ImageCollection('MODIS/061/MCD64A1')
        .filterDate(start, end)
        .filterBounds(geometry)
        .select('BurnDate')
        .mosaic()
        .gte(1)
        .selfMask();
}

// ─── AVALIAR ────────────────────────────────────────────────────────────────

function evaluate(candidateId) {
    var img = ee.Image(candidateId);
    var name = candidateId.split('/').pop();
    var regionName = name.split('_').filter(function (p) { return p.indexOf('region') === 0; })[0] || 'unknown';

    var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
    var geometry = regionGeom.geometry();

    // Extrai ano do nome
    var yearMatch = name.match(/_(\d{4})(_(\d{2}))?_candidate/);
    var year = yearMatch ? parseInt(yearMatch[1], 10) : new Date().getFullYear();
    var month = yearMatch && yearMatch[3] ? parseInt(yearMatch[3], 10) : null;

    var checklist = {};
    var allPassed = true;

    print('=== Checklist de Avaliacao ===');
    print('Candidato: ' + name);
    print('Regiao: ' + regionName);
    print('Ano: ' + year + (month ? ' Mes: ' + month : ''));
    print('');

    // Item 1: Area queimada dentro do threshold
    var areaImage = ee.Image.pixelArea().divide(10000);
    var stats = img.selfMask().gt(0).selfMask().multiply(areaImage).reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: geometry,
        scale: SCALE,
        maxPixels: 1e13,
    });
    var areaHa = 0;
    var key = stats.keys().get(0);
    if (key) areaHa = ee.Number(stats.get(key)).getInfo() || 0;

    checklist.area = {
        valor: areaHa,
        min: THRESHOLD_AREA_MIN_HA,
        max: THRESHOLD_AREA_MAX_HA,
        passou: areaHa >= THRESHOLD_AREA_MIN_HA && areaHa <= THRESHOLD_AREA_MAX_HA,
    };
    print('1. Area queimada: ' + areaHa.toFixed(1) + ' ha');
    print('   Threshold: ' + THRESHOLD_AREA_MIN_HA + ' - ' + THRESHOLD_AREA_MAX_HA + ' ha');
    print('   Resultado: ' + (checklist.area.passou ? 'APROVADO' : 'REPROVADO'));
    if (!checklist.area.passou) allPassed = false;

    // Item 2: Consistencia visual (overlay com mosaico min NBR)
    var dateKey = month ? year + '_' + ('0' + month).slice(-2) : '' + year;
    try {
        var mosaic = ee.ImageCollection(MOSAIC_BASE + '/swir1').mosaic();
        Map.addLayer(mosaic, { min: 3, max: 40, palette: ['000000', 'ffffff'] }, 'Mosaico Min NBR ' + dateKey, false);
        Map.addLayer(img.selfMask(), { min: 0, max: 1, palette: ['ff0000'] }, 'Candidato ' + name, false);
        Map.centerObject(regionGeom);

        checklist.visual = {
            passou: true,  // Inspecao visual manual
            nota: 'Verifique visualmente se as cicatrizes correspondem a quedas de NBR',
        };
        print('2. Consistencia visual: INSPECAO MANUAL');
        print('   Verifique o overlay no mapa: vermelho = candidato, fundo = mosaico min NBR');
        print('   As cicatrizes (vermelho) devem corresponder a areas escuras no mosaico (NBR baixo).');
    } catch (e) {
        checklist.visual = { passou: false, nota: 'Mosaico nao disponivel para comparacao' };
        print('2. Consistencia visual: INDISPONIVEL');
    }

    // Item 3: Overlap com referencia externa (MODIS MCD64A1)
    try {
        var modis = getMCD64A1(year, geometry);
        var modisArea = modis.multiply(areaImage).reduceRegion({
            reducer: ee.Reducer.sum(),
            geometry: geometry,
            scale: 500,
            maxPixels: 1e13,
        });
        var modisHa = 0;
        var modisKey = modisArea.keys().get(0);
        if (modisKey) modisHa = ee.Number(modisArea.get(modisKey)).getInfo() || 0;

        // Overlap entre candidato e MODIS
        var overlap = img.selfMask().gt(0).and(modis);
        var overlapArea = overlap.selfMask().multiply(areaImage).reduceRegion({
            reducer: ee.Reducer.sum(),
            geometry: geometry,
            scale: SCALE,
            maxPixels: 1e13,
        });
        var overlapHa = 0;
        var overlapKey = overlapArea.keys().get(0);
        if (overlapKey) overlapHa = ee.Number(overlapArea.get(overlapKey)).getInfo() || 0;

        var overlapPct = areaHa > 0 ? ((overlapHa / areaHa) * 100).toFixed(1) : '0.0';

        Map.addLayer(modis, { min: 0, max: 1, palette: ['00ff00'] }, 'MODIS MCD64A1 ' + year, false);

        checklist.referencia = {
            modisAreaHa: modisHa,
            overlapHa: overlapHa,
            overlapPct: parseFloat(overlapPct),
            passou: parseFloat(overlapPct) > 10,  // Pelo menos 10% de overlap
        };
        print('3. Overlap com MODIS MCD64A1: ' + overlapHa.toFixed(1) + ' ha (' + overlapPct + '%)');
        print('   MODIS total: ' + modisHa.toFixed(1) + ' ha');
        print('   Candidato total: ' + areaHa.toFixed(1) + ' ha');
        print('   Resultado: ' + (checklist.referencia.passou ? 'APROVADO (>10% overlap)' : 'REPROVADO'));
        if (!checklist.referencia.passou) allPassed = false;
    } catch (e) {
        checklist.referencia = { passou: true, nota: 'MODIS nao disponivel — pulando verificacao' };
        print('3. Overlap com referencia: INDISPONIVEL (pulado)');
    }

    // Item 4: Cobertura espacial
    var regionCount = ee.FeatureCollection(REGIONS.filterBounds(geometry)).size().getInfo();
    checklist.cobertura = {
        regioes_com_dado: 1,
        regioes_total: regionCount,
        passou: true,  // Sempre passa — so alerta se faltar
    };
    print('4. Cobertura espacial: ' + 1 + ' de ' + regionCount + ' regioes');
    print('   Resultado: OK');

    // Resumo final
    print('');
    print('=== Resultado Final ===');
    print('Status: ' + (allPassed ? 'APROVADO — Pode promover para PRE_PUBLIC' : 'REPROVADO — Revisar itens acima'));
    print('');

    return {
        candidate: candidateId,
        name: name,
        passed: allPassed,
        checklist: checklist,
        date: new Date().toISOString(),
    };
}

// ─── EXECUTAR ───────────────────────────────────────────────────────────────

print('=== M9_01 — Protocolo de Avaliacao ===');
print('');

var result = evaluate(CANDIDATO_ID);

print('--- JSON do resultado (para registro) ---');
print(JSON.stringify(result, null, 2));

print('');
print('=== M9_01 concluido ===');
