/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - ft01
Filtros Morfologicos (Abertura/Fechamento)

📅 DATA: julho 2026
🏷️ VERSAO: 4.6
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;

var COLLECTION_BASE = 'propose_a';
var inputStage  = '-ft00';
var outputStage = '-ft01';
var CAMPAIGN = 'MONITOR_01';
var openingRadius = 1;   // pixels (1px = 10m)
var closingRadius = 2;   // pixels (2px = 20m)

var filteredPath = CLASSIFICATIONS_ROOT + 'FILTERED/';
var inputCollection  = filteredPath + COLLECTION_BASE + inputStage;
var outputCollection = filteredPath + COLLECTION_BASE + outputStage;

function ensureFolder(pathName) {
    var parts = pathName.split('/');
    var current = CLASSIFICATIONS_ROOT;
    for (var i = 0; i < parts.length; i++) {
        current += parts[i];
        try { ee.data.getAsset(current); }
        catch (e) {
            var isImageCollection = (i === parts.length - 1 && parts[i].indexOf('-ft') !== -1);
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

print('=== ft01 — Morphology ===');
print('Input:  ' + inputCollection);
print('Output: ' + outputCollection);
print('Opening: ' + openingRadius + 'px / Closing: ' + closingRadius + 'px');

ensureFolder('FILTERED/' + COLLECTION_BASE + inputStage);
ensureFolder('FILTERED/' + COLLECTION_BASE + outputStage);

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

            // Abertura: erode -> dilate (remove ruido isolado)
            var opened = sourceImage.focalMin({ radius: openingRadius, kernelType: 'circle', units: 'pixels' });
            opened = opened.focalMax({ radius: openingRadius, kernelType: 'circle', units: 'pixels' });

            // Fechamento: dilate -> erode (fecha buracos)
            var closed = opened.focalMax({ radius: closingRadius, kernelType: 'circle', units: 'pixels' });
            closed = closed.focalMin({ radius: closingRadius, kernelType: 'circle', units: 'pixels' });

            closed = ee.Image(closed.selfMask().copyProperties(sourceImage));
            closed = closed.set('filter_stage', 'ft01');

            var destAsset = outputCollection + '/' + periodName;

            Map.addLayer(ee.Image(sourceImage).select(0).selfMask(), { min: 0, max: 1000, palette: ['888888'] }, periodName + ' | BEFORE', false);
            Map.addLayer(ee.Image(closed).select(0).selfMask(), { min: 0, max: 1000, palette: ['0044ff'] }, periodName + ' | AFTER', false);

            try {
                ee.data.getAsset(destAsset);
                print('  OK: ' + periodName);
            } catch (e) {
                exportCount++;
                print('  Export: ' + periodName);
                Export.image.toAsset({
                    image: closed.toInt16(),
                    description: (CAMPAIGN + '_ft01_' + COLLECTION_BASE + '_' + periodName).substring(0, 80).replace(/[^a-zA-Z0-9_]/g, '_'),
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
print('=== ft01 done ===');
