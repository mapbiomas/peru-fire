/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8
Statistics Generator (Universal)

📅 DATA: julho 2026
🏷️ VERSAO: 1.0

📌 O QUE FAZ:
1. Varre FILTERED/ e descobre todas as collections e estagios
2. Para cada (collection, region, period), calcula area com
   observacao e area queimada em cada estagio (ft00-ft03)
3. Cruza com land cover (MapBiomas Peru Collection 3)
4. Exporta 1 CSV por collection para GCS
5. Idempotente — roda a qualquer momento, recalcula com dados disponiveis

📌 CATALOGOS — arrays vazios = varredura automatica de tudo
   Preencha para restringir:
   - COLLECTIONS: ['propuesta_a'] = so esta colecao
   - STAGES: ['ft00','ft01'] = so estes estagios
   - LANDCOVER_LEVELS: [0, 1] = niveis de legenda a exportar
============================================================ */

// ─── CONFIGURATION ──────────────────────────────────────────────────────────

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;

var LULC = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');
var currentYear = new Date().getFullYear();
for (var year = 2025; year <= currentYear; year++) {
    LULC = LULC.addBands(LULC.select('classification_2024').rename('classification_' + year));
}

// Catalogos — vazios = descobre automaticamente
var COLLECTIONS = [];
var STAGES = [];
var CAMPAIGN = 'MONITOR_01';

// Export
var EXPORT_BUCKET = 'mapbiomas-fire';
var EXPORT_PREFIX = 'sudamerica/peru/CATALOG_01/' + CAMPAIGN + '/LIBRARY_STATISTICS/';

// ─── LEGENDAS LULC (mesmo padrao dos scripts existentes) ──────────────────

var LULC_LEVELS = {
  0: ee.Dictionary({
    1: 'Natural',
    2: 'Antropico',
    3: 'Nao Observado'
  }),
  1: ee.Dictionary({
    1: 'Floresta',
    2: 'Formacao Natural Nao Florestal',
    3: 'Agropecuaria',
    4: 'Area Nao Vegetada',
    5: 'Corpo D\'agua',
    6: 'Nao Observado'
  }),
  2: ee.Dictionary({
    1:  'Formacao Florestal',
    2:  'Formacao Savanica',
    3:  'Mangue',
    4:  'Campo Alagado e Area Pantanosa',
    5:  'Formacao Campestre',
    6:  'Outras Formacoes Nao Florestais',
    7:  'Pastagem',
    8:  'Cultura Anual e Perene',
    9:  'Mosaico de Agricultura e Pastagem',
    10: 'Praia, Duna e Areal',
    11: 'Area Urbanizada',
    12: 'Outras Areas Nao Vegetadas',
    13: 'Mineração',
    14: 'Rio, Lago e Oceano',
    15: 'Aquicultura',
    16: 'Nao Observado'
  })
};

// ─── HELPERS ────────────────────────────────────────────────────────────────

function ensureFolder(name) {
    var p = name.split('/'), cur = CLASSIFICATIONS_ROOT;
    for (var i = 0; i < p.length; i++) {
        cur += p[i];
        try { ee.data.getAsset(cur); }
        catch (e) {
            ee.data.createAsset({ type: 'FOLDER' }, cur);
        }
        cur += '/';
    }
}

function extractYear(periodName) {
    var match = periodName.match(/^(\d{4})/);
    return match ? parseInt(match[1], 10) : currentYear;
}

function buildTerritoryRaster() {
    var featureList = ee.List(REGIONS.distinct([REGION_PROPERTY]).aggregate_array(REGION_PROPERTY));
    var ids = ee.List.sequence(1, featureList.size());
    var idByRegion = ee.Dictionary.fromLists(featureList, ids);

    var territory = ee.Image(0);
    featureList.evaluate(function (regionNames) {
        regionNames.forEach(function (rn, idx) {
            var id = idx + 1;
            var regionFC = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, rn));
            var regionRaster = ee.Image(0).paint(regionFC, id);
            territory = territory.where(regionRaster.eq(id), id);
        });
    });

    // Fallback: paint each region with numeric index
    var painted = ee.Image(0);
    for (var idx = 1; idx <= featureList.size().getInfo(); idx++) {
        var regionName = featureList.get(idx - 1);
        var regionFC = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
        painted = painted.where(ee.Image(0).paint(regionFC, 1).eq(1), idx);
    }

    return { image: painted.rename('territory'), dict: idByRegion, list: featureList };
}

// ─── AREA CALCULATION ───────────────────────────────────────────────────────

function calculateArea(stageImage, territory, lulcYear, periodYear) {
    // Composite encoding: LULC * 100 + fireStatus
    //   fireStatus: 0 = sem observacao, 1 = obs sem fogo, 2 = queimado
    var obs = stageImage.select('probability').neq(-9999);
    var burned = stageImage.select('probability').gt(500);
    var fireStatus = obs.add(burned);  // 0=sem obs, 1=obs, 2=obs+queimado

    var composite = lulcYear.multiply(100).add(fireStatus).rename('class');

    var pixelArea = ee.Image.pixelArea().divide(10000);  // m² → ha

    var reducer = ee.Reducer.sum()
        .group(1, 'class')
        .group(1, 'territory');

    var data = pixelArea
        .addBands(territory)
        .addBands(composite)
        .reduceRegion({
            reducer: reducer,
            geometry: REGIONS.geometry().bounds(),
            scale: SCALE,
            maxPixels: 1e12
        });

    var rows = ee.List(data.get('groups')).map(function (terrObj) {
        terrObj = ee.Dictionary(terrObj);
        var territoryId = terrObj.getNumber('territory');
        var groups = ee.List(terrObj.get('groups'));

        return ee.FeatureCollection(groups.map(function (classObj) {
            classObj = ee.Dictionary(classObj);
            var classVal = classObj.getNumber('class');
            var lulcId = classVal.divide(100).int();
            var fireStatus = classVal.mod(100).int();

            var areaHa = ee.Number(classObj.get('sum')).multiply(10).round().divide(10);
            var obsArea = fireStatus.gte(1).multiply(areaHa);
            var burnedArea = fireStatus.eq(2).multiply(areaHa);

            var props = ee.Dictionary({
                'territory': territoryId,
                'lulc_id': lulcId,
                'area_obs_ha': obsArea,
                'area_burned_ha': burnedArea
            });

            // Enrich with LULC legend levels
            Object.keys(LULC_LEVELS).forEach(function (level) {
                props = props.set('lulc_nivel_' + level, LULC_LEVELS[level].get(lulcId, 'Desconhecido'));
            });

            return ee.Feature(null, props);
        }));
    });

    return ee.FeatureCollection(rows).flatten();
}

// ─── DISCOVERY ──────────────────────────────────────────────────────────────

function discoverCollections(cb) {
    ee.data.listAssets(FILTERED, {}, function (result) {
        if (!result || !result.assets) { cb([]); return; }
        var cols = result.assets
            .filter(function (a) { return a.type === 'FOLDER'; })
            .map(function (a) { return a.id.split('/').pop(); })
            .sort();
        cb(cols);
    });
}

function discoverStages(col, cb) {
    var path = FILTERED + col + '/';
    ee.data.listAssets(path, {}, function (result) {
        if (!result || !result.assets) { cb([]); return; }
        var stages = result.assets
            .filter(function (a) { return a.type === 'IMAGE_COLLECTION' && /^ft\d\d$/.test(a.id.split('/').pop()); })
            .map(function (a) { return a.id.split('/').pop(); })
            .sort();
        cb(stages);
    });
}

function discoverPeriods(col, stage, cb) {
    var path = FILTERED + col + '/' + stage + '/';
    ee.data.listAssets(path, {}, function (result) {
        if (!result || !result.assets) { cb([]); return; }
        var periods = result.assets
            .filter(function (a) { return a.type === 'IMAGE'; })
            .map(function (a) { return a.id.split('/').pop(); })
            .sort();
        cb(periods);
    });
}

// ─── MAIN ───────────────────────────────────────────────────────────────────

print('=== M8 — Statistics Generator ===');
print('FILTERED root: ' + FILTERED);

Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
Map.centerObject(REGIONS);

var territory = buildTerritoryRaster();

discoverCollections(function (collections) {
    var targetCols = COLLECTIONS.length > 0
        ? collections.filter(function (c) { return COLLECTIONS.indexOf(c) !== -1; })
        : collections;

    print('Collections: ' + targetCols.length + ' (' + targetCols.join(', ') + ')');

    if (targetCols.length === 0) {
        print('Nenhuma collection encontrada em FILTERED/.');
        return;
    }

    ensureFolder('FILTERED/../LIBRARY_STATISTICS');

    var totalExports = 0;

    targetCols.forEach(function (col) {
        discoverStages(col, function (stages) {
            var targetStages = STAGES.length > 0
                ? stages.filter(function (s) { return STAGES.indexOf(s) !== -1; })
                : stages;

            if (targetStages.length === 0) {
                print('  [' + col + '] Nenhum estagio encontrado.');
                return;
            }

            discoverPeriods(col, targetStages[0], function (periods) {
                if (periods.length === 0) {
                    print('  [' + col + '] Nenhum periodo encontrado em ft00.');
                    return;
                }

                print('  [' + col + '] ' + periods.length + ' periodos, ' + targetStages.length + ' estagios');

                // For each period, read all stages and compute stats
                var allRows = ee.FeatureCollection(periods.map(function (periodName) {
                    var periodYear = extractYear(periodName);
                    var lulcYear = LULC.select('classification_' + periodYear);

                    return ee.FeatureCollection(targetStages.map(function (stage) {
                        var assetPath = FILTERED + col + '/' + stage + '/' + periodName;
                        var img;
                        try {
                            img = ee.Image(assetPath);
                        } catch (e) {
                            return ee.FeatureCollection([]);
                        }

                        var stageRows = calculateArea(img, territory.image, lulcYear, periodYear);

                        return stageRows.map(function (f) {
                            return ee.Feature(f).set({
                                'period': periodName,
                                'collection': col,
                                'stage': stage,
                                'campaign': CAMPAIGN
                            });
                        });
                    }));
                })).flatten();

                // Export: one row per (period, stage, territory, lulc)
                var fileName = 'm8_' + col;
                var fullPath = EXPORT_PREFIX + fileName;

                Export.table.toCloudStorage({
                    collection: allRows,
                    description: fileName.substring(0, 80),
                    bucket: EXPORT_BUCKET,
                    fileNamePrefix: fullPath,
                    fileFormat: 'CSV',
                    selectors: ['period', 'collection', 'stage', 'campaign', 'territory',
                                'lulc_id', 'lulc_nivel_0', 'lulc_nivel_1', 'lulc_nivel_2',
                                'area_obs_ha', 'area_burned_ha']
                });

                totalExports++;
                print('    Export: gs://' + EXPORT_BUCKET + '/' + fullPath + '.csv');
            });
        });
    });

    // Also export region legend as reference
    var regionRows = ee.FeatureCollection(
        ee.List(REGIONS.aggregate_array(REGION_PROPERTY).distinct()).map(function (rn, idx) {
            return ee.Feature(null, {
                'territory': idx + 1,
                'region_name': rn
            });
        })
    );

    Export.table.toCloudStorage({
        collection: regionRows,
        description: 'm8_region_legend',
        bucket: EXPORT_BUCKET,
        fileNamePrefix: EXPORT_PREFIX + 'm8_region_legend',
        fileFormat: 'CSV'
    });

    print('');
    print('=== M8 done. ' + totalExports + ' exports submitted. ===');
    print('Region legend: gs://' + EXPORT_BUCKET + '/' + EXPORT_PREFIX + 'm8_region_legend.csv');
});