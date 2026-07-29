/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8_01
Promover a Candidato

📅 DATA: julho 2026
🏷️ VERSAO: 4.5

📌 O QUE FAZ:
1. Copia ultima etapa de filtro (-ft03) para CANDIDATES/
2. Calcula area queimada (ha) por periodo
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;

var COLLECTION_BASE = 'propose_a';
var STAGE_SRC = '-ft03';
var CAMPAIGN = 'MONITOR_01';

var PATH_FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var PATH_CANDIDATES = CLASSIFICATIONS_ROOT + 'CANDIDATES/';
var COLL_IN = PATH_FILTERED + COLLECTION_BASE + STAGE_SRC;
var COLL_OUT = PATH_CANDIDATES + COLLECTION_BASE;

function ensureFolder(name){
    var p=name.split('/'), cur=CLASSIFICATIONS_ROOT;
    for(var i=0;i<p.length;i++){cur+=p[i];try{ee.data.getAsset(cur)}catch(e){ee.data.createAsset({type:(i===p.length-1&&p[i].indexOf('-ft')!==-1)?'IMAGE_COLLECTION':'FOLDER'},cur)}cur+='/';}
}

print('=== M8_01 — Promote Candidate ===');
print('Source:  ' + COLL_IN);
print('Target:  ' + COLL_OUT);

ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_SRC);
ensureFolder('CANDIDATES');
ensureFolder('CANDIDATES/'+COLLECTION_BASE);

var images = ee.data.listAssets(COLL_IN).assets.filter(function (a) { return a.type === 'IMAGE'; });
if (images.length === 0) {
    print('Nenhuma imagem em ' + COLL_IN);
} else {
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
    Map.centerObject(REGIONS);
    var total = 0;
    var areaImage = ee.Image.pixelArea().divide(10000);

    images.forEach(function (img) {
        var name = img.id.split('/').pop();
        var eeImg = ee.Image(img.id);
        var destAsset = COLL_OUT + '/' + name;
        var stats = eeImg.select('probability').gt(0).selfMask().multiply(areaImage).reduceRegion({reducer: ee.Reducer.sum(), geometry: REGIONS.geometry(), scale: SCALE, maxPixels: 1e13});
        var areaHa = 0; var k = stats.keys().get(0); if (k) areaHa = Math.round(ee.Number(stats.get(k)).getInfo()) || 0;
        var promoted = eeImg.set({'burned_area_ha': areaHa, 'promotion_date': new Date().toISOString().split('T')[0], 'source_collection': COLL_IN});

        Map.addLayer(eeImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['3355ff'] }, 'CANDIDATE ' + name, false);
        try {
            ee.data.getAsset(destAsset);
            print('  OK: ' + name + ' | area: ' + areaHa + ' ha');
        } catch (e) {
            total++;
            print('  Promote: ' + name + ' | area: ' + areaHa + ' ha');
            Export.image.toAsset({image: promoted.toInt16(), description: (CAMPAIGN + '_candidate_' + COLLECTION_BASE + '_' + name).substring(0, 80).replace(/[^a-zA-Z0-9_]/g, '_'), assetId: destAsset, pyramidingPolicy: 'mode', region: REGIONS.geometry().bounds(), scale: SCALE, maxPixels: 1e13});
        }
    });
    print('Total export: ' + total);
}
print('=== M8_01 done ===');
