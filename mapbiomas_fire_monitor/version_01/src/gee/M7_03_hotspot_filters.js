/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - ft03
Isencao por Buffer de Focos de Calor

📅 DATA: julho 2026
🏷️ VERSAO: 4.6
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;

var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');
var hotspotsBase = 'projects/workspace-ipam/assets/FOGO/monthly-focus-sul-america';

var COLLECTION_BASE = 'propose_a';
var inputStage  = '-ft02';
var outputStage = '-ft03';
var CAMPAIGN = 'MONITOR_01';
var bufferMeters  = 5000;
var exemptionRegions = ['region1', 'region2', 'region3', 'region4'];
var exemptClasses   = [66, 12, 13];  // 66 = mosaico agro, 12 = pasto, 13 = formacao natural nao florestal

var filteredPath = CLASSIFICATIONS_ROOT + 'FILTERED/';
var inputCollection  = filteredPath + COLLECTION_BASE + inputStage;
var outputCollection = filteredPath + COLLECTION_BASE + outputStage;
var hotspotCache = {};

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

function extractYear(name) {
    var match = name.match(/^(\d{4})/);
    return match ? parseInt(match[1], 10) : new Date().getFullYear();
}

function buildHotspotBuffer(imageYear, geometry) {
    if (hotspotCache[imageYear]) return hotspotCache[imageYear];

    var buffer = ee.Image(0);
    for (var month = 1; month <= 12; month++) {
        var monthStr = month < 10 ? '0' + month : '' + month;
        try {
            var hotspots = ee.FeatureCollection(hotspotsBase + '/focus_' + imageYear + '-' + monthStr).filterBounds(geometry);
            var hotspotBuffer = hotspots.map(function (h) {
                return ee.Feature(h.geometry().buffer(bufferMeters));
            });
            var bufferImage = ee.Image().paint(hotspotBuffer).eq(0);
            buffer = buffer.where(bufferImage.eq(1), 1);
        } catch (e) { /* month may not exist */ }
    }
    hotspotCache[imageYear] = buffer;
    return buffer;
}

print('=== ft03 — Hotspot Exemption ===');
print('Input:  ' + inputCollection);
print('Output: ' + outputCollection);
print('Buffer: ' + (bufferMeters / 1000) + 'km, Regions: ' + exemptionRegions.join(','));

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
            var imageYear = extractYear(periodName);
            var geometry   = REGIONS.geometry();

            // Build accumulated hotspot buffer for the year
            var hotspotBuffer = buildHotspotBuffer(imageYear, geometry);

            // LULC classes eligible for exemption
            var lulcExempt = landcover.select('classification_' + imageYear).eq(exemptClasses).reduce(ee.Reducer.sum()).gte(1);

            // Build exemption mask for target regions only
            var exemption = ee.Image(0);
            exemptionRegions.forEach(function (regionName) {
                var regionGeometry = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
                var regionRaster   = ee.Image(0).paint(regionGeometry, 1);
                var regionExemption = hotspotBuffer.multiply(lulcExempt).multiply(regionRaster);
                exemption = exemption.where(regionExemption.eq(1), 1);
            });
            exemption = exemption.selfMask();

            // Restore fire pixels where exemption applies
            var outputImage = sourceImage.unmask(0);
            outputImage = outputImage.where(exemption.eq(1).and(sourceImage.mask().not()), sourceImage.unmask(0));
            outputImage = outputImage.updateMask(sourceImage.mask().or(exemption.eq(1))).selfMask();
            outputImage = outputImage.copyProperties(sourceImage).set('filter_stage', 'ft03');

            var destAsset = outputCollection + '/' + periodName;

            Map.addLayer(hotspotBuffer.selfMask(), { min: 0, max: 1, palette: ['ff8800'] }, 'Hotspot buffer ' + imageYear, false);
            Map.addLayer(exemption, { min: 0, max: 1, palette: ['00ff00'] }, periodName + ' | EXEMPT', false);
            Map.addLayer(ee.Image(sourceImage).select(0).selfMask(), { min: 0, max: 1000, palette: ['888888'] }, periodName + ' | BEFORE', false);
            Map.addLayer(ee.Image(outputImage).select(0).selfMask(), { min: 0, max: 1000, palette: ['ff00ff'] }, periodName + ' | AFTER', false);

            try {
                ee.data.getAsset(destAsset);
                print('  OK: ' + periodName);
            } catch (e) {
                exportCount++;
                print('  Export: ' + periodName);
                Export.image.toAsset({
                    image: outputImage.toInt16(),
                    description: (CAMPAIGN + '_ft03_' + COLLECTION_BASE + '_' + periodName).substring(0, 80).replace(/[^a-zA-Z0-9_]/g, '_'),
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
print('=== ft03 done ===');
