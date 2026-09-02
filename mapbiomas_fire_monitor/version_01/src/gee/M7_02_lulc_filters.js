/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - ft02
Filtros LULC (MapBiomas Peru Collection 3)

📅 DATA: julho 2026
🏷️ VERSAO: 4.7
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;

var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');
// Add missing year bands (duplicate 2024 for years beyond collection range)
var currentYear = new Date().getFullYear();
for (var year = 2025; year <= currentYear; year++) {
    landcover = landcover.addBands(landcover.select('classification_2024').rename('classification_' + year));
}

var COLLECTION_BASE = 'propuesta_a';
var inputStage  = 'ft01';
var outputStage = 'ft02';
var CAMPAIGN = 'MONITOR_01';

var waterClasses = [26, 31, 33];
var noVegClasses = [22, 23, 24, 25, 32, 61, 68];
var lulcMasks = {
    'region1':  waterClasses.concat(noVegClasses),
    'region2':  waterClasses.concat(noVegClasses),
    'region3':  [24, 29],
    'region4':  [24, 68, 25, 29],
    'region5':  [29, 24, 68],
    'region6':  waterClasses.concat(noVegClasses),
    'region7':  waterClasses.concat(noVegClasses),
    'region8':  waterClasses.concat(noVegClasses),
    'region9':  [25],
    'region10': [25],
};

var LULC_PALETTE = require('users/mapbiomas/modules:Palettes.js').get('brazil');

var filteredPath = CLASSIFICATIONS_ROOT + 'FILTERED/';
var inputCollection  = filteredPath + COLLECTION_BASE + '/' + inputStage;
var outputCollection = filteredPath + COLLECTION_BASE + '/' + outputStage;

function setTimeProperties(image, periodName) {
    var parts = periodName.split('_');
    var y = parseInt(parts[0], 10);
    var m = parseInt(parts[1], 10);
    var start = ee.Date.fromYMD(y, m, 1);
    var end = start.advance(1, 'month');
    return image.set({
        'system:time_start': start.millis(),
        'system:time_end': end.millis()
    });
}

function ensureFolder(pathName) {
    var parts = pathName.split('/');
    var current = CLASSIFICATIONS_ROOT;
    for (var i = 0; i < parts.length; i++) {
        current += parts[i];
        try { ee.data.getAsset(current); }
        catch (e) {
            var isImageCollection = (i === parts.length - 1 && /^ft\d\d$/.test(parts[i]));
            ee.data.createAsset({ type: isImageCollection ? 'IMAGE_COLLECTION' : 'FOLDER' }, current);
        }
        current += '/';
    }
}

function buildLayerPanel(images, layerFactory) {
    var panel = ui.Panel({
        layout: ui.Panel.Layout.flow('vertical'),
        style: {
            position: 'bottom-left',
            maxHeight: '60%',
            width: '200px',
            padding: '4px',
            backgroundColor: 'rgba(255,255,255,0.92)',
            border: '1px solid #ccc',
            borderRadius: '4px'
        }
    });
    panel.add(ui.Label('PERIODOS', { fontWeight: 'bold', fontSize: '11px', margin: '2px' }));
    var activeLayers = [];

    images.forEach(function (img, idx) {
        var periodName = img.id.split('/').pop();
        var checkbox = ui.Checkbox({ label: periodName, value: idx === 0, style: { fontSize: '10px', margin: '1px 2px' } });
        checkbox.onChange(function (checked) {
            if (!checked) return;
            for (var w = 0; w < panel.widgets().length(); w++) {
                var widget = panel.widgets().get(w);
                if (widget !== checkbox && widget.setValue) try { widget.setValue(false); } catch (e) {}
            }
            activeLayers.forEach(function (layer) { Map.layers().remove(layer); });
            activeLayers = [];
            var newLayers = layerFactory(img);
            newLayers.forEach(function (entry) {
                Map.layers().add(entry.layer);
                activeLayers.push(entry.layer);
            });
        });
        panel.add(checkbox);
    });

    if (images.length > 0) {
        var firstLayers = layerFactory(images[0]);
        firstLayers.forEach(function (entry) {
            Map.layers().add(entry.layer);
            activeLayers.push(entry.layer);
        });
    }
    Map.add(panel);
    return panel;
}

function extractYear(name) {
    var match = name.match(/^(\d{4})/);
    return match ? parseInt(match[1], 10) : new Date().getFullYear();
}

print('=== ft02 — LULC Filters ===');
print('Input:  ' + inputCollection);
print('Output: ' + outputCollection);

ensureFolder('FILTERED/' + COLLECTION_BASE + '/' + inputStage);
ensureFolder('FILTERED/' + COLLECTION_BASE + '/' + outputStage);

ee.data.listAssets(inputCollection, {}, function (result) {
    var images = [];
    if (result && result.assets) {
        images = result.assets.filter(function (a) { return a.type === 'IMAGE'; });
    }

    if (images.length === 0) {
        print('Nenhuma imagem encontrada.');
    } else {
        Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
        Map.centerObject(REGIONS);
        Map.addLayer(landcover.select('classification_2024').selfMask(), { min: 0, max: 72, palette: LULC_PALETTE }, 'LULC Peru', false);

        buildLayerPanel(images, function (img) {
            var periodName = img.id.split('/').pop();
            var beforeLayer = ui.Map.Layer(ee.Image(img.id).select(0).selfMask(), { min: 0, max: 1000, palette: ['888888'] }, periodName + ' | BEFORE');
            var mosaicLayer;
            try {
                var mosaicPath = CATALOG_ROOT + '/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR/swir1';
                var mosaicImage = ee.ImageCollection(mosaicPath).filter(ee.Filter.eq('system:index', 'image_peru_fire_sentinel2_minnbr_swir1_' + periodName)).mosaic();
                mosaicLayer = ui.Map.Layer(mosaicImage, { min: 3, max: 40 }, periodName + ' | Min NBR');
            } catch (e) { mosaicLayer = ui.Map.Layer(ee.Image(), {}, ''); }
            return [{ layer: beforeLayer }, { layer: mosaicLayer }];
        });

        var exportCount = 0;
        images.forEach(function (img) {
            var periodName = img.id.split('/').pop();
            var sourceImage = ee.Image(img.id);
            var imageYear = extractYear(periodName);

            var maskedImage = sourceImage;
            var removedPixels = ee.Image(0);

            Object.keys(lulcMasks).forEach(function (regionName) {
                var regionMaskClasses = lulcMasks[regionName];
                var regionGeometry = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
                var regionRaster = ee.Image(0).paint(regionGeometry, 1);

                // Build LULC mask: 1 where classes to remove exist
                var lulcMask = landcover.select('classification_' + imageYear).eq(regionMaskClasses).reduce(ee.Reducer.sum()).gte(1);

                // Restrict to region boundaries
                lulcMask = lulcMask.multiply(regionRaster);

                // Final mask: 0 = keep, 1 = remove
                var finalMask = lulcMask.neq(1);
                maskedImage = maskedImage.updateMask(finalMask);

                // Track removed pixels for visualization
                removedPixels = removedPixels.where(regionRaster.eq(1), lulcMask);
            });

            // Remove solitary pixels (<= 6 connected)
            var connections = maskedImage.select('probability').gt(0).connectedPixelCount({ maxSize: 100, eightConnected: false });
            maskedImage = maskedImage.where(connections.lte(6), 0).selfMask();
            maskedImage = setTimeProperties(maskedImage.copyProperties(sourceImage).set('filter_stage', 'ft02'), periodName);

            var destAsset = outputCollection + '/' + periodName;

            Map.addLayer(ee.Image(sourceImage).select(0).selfMask(), { min: 0, max: 1000, palette: ['888888'] }, periodName + ' | BEFORE', false);
            Map.addLayer(ee.Image(removedPixels).selfMask(), { min: 0, max: 1, palette: ['ff0000'] }, periodName + ' | REMOVED', false);
            Map.addLayer(ee.Image(maskedImage).select(0).selfMask(), { min: 0, max: 1000, palette: ['00cc00'] }, periodName + ' | AFTER', false);

            try {
                ee.data.getAsset(destAsset);
                print('  OK: ' + periodName);
            } catch (e) {
                exportCount++;
                print('  Export: ' + periodName);
                Export.image.toAsset({
                    image: ee.Image(maskedImage).toInt16(),
                    description: (CAMPAIGN + '_ft02_' + COLLECTION_BASE + '_' + periodName).substring(0, 80).replace(/[^a-zA-Z0-9_]/g, '_'),
                    assetId: destAsset,
                    pyramidingPolicy: 'mode',
                    region: REGIONS.geometry().bounds(),
                    scale: SCALE,
                    maxPixels: 1e13,
                });
            }
        });
        print('Total export: ' + exportCount);
    }
});
print('=== ft02 done ===');