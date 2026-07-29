/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_02
Filtros LULC (MapBiomas Peru Collection 3)

📅 DATA: julho 2026
🏷️ VERSAO: 4.5
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;
var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');

var COLLECTION_BASE = 'propose_a';
var STAGE_IN = '-ft01';
var STAGE_OUT = '-ft02';

var CLASSES_AGUA = [33, 31, 34];
var CLASSES_SEM_VEG = [23, 24, 32, 61, 68, 25];
var masks = {
    'region1':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region2':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region3':[24,29],'region4':[24,68,25,29],'region5':[29,24,68],'region6':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region7':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region8':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region9':[25],'region10':[25]
};

var LULC_PALETTE = ['ffffff','32a65e','1f8d49','7dc975','04381d','026975','000000','000000','7a6c00','ad975a','519799','d6bc74','d89f5c','ffffb2','edde8e','000000','000000','f5b3c8','c27ba0','db7093','ffefc3','db4d4f','ffa07a','d4271e','db4d4f','0000ff','bcbcbc','000000','ffaa5f','9c0027','091077','fc8114','2532e4','93dfe6','9065d0','d082de'];

var PATH_FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var COLL_IN = PATH_FILTERED + COLLECTION_BASE + STAGE_IN;
var COLL_OUT = PATH_FILTERED + COLLECTION_BASE + STAGE_OUT;

function ensureFolder(name){
    var p=name.split('/'), cur=CLASSIFICATIONS_ROOT;
    for(var i=0;i<p.length;i++){cur+=p[i];try{ee.data.getAsset(cur)}catch(e){ee.data.createAsset({type:(i===p.length-1&&p[i].indexOf('-ft')!==-1)?'IMAGE_COLLECTION':'FOLDER'},cur)}cur+='/';}
}

function extractYear(name) { var m=name.match(/^(\d{4})/); return m?parseInt(m[1],10):new Date().getFullYear(); }

print('=== M7_02 — LULC Filters ===');
print('Collection IN:  ' + COLL_IN);
print('Collection OUT: ' + COLL_OUT);

ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_OUT);

var images = ee.data.listAssets(COLL_IN).assets.filter(function(a){return a.type==='IMAGE';});

if(images.length===0){
    print('Nenhuma imagem encontrada.');
}else{
    Map.addLayer(REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}),{},'Regions');
    Map.centerObject(REGIONS);
    Map.addLayer(landcover.select('classification_2024').selfMask(),{min:0,max:72,palette:LULC_PALETTE},'LULC Peru',false);

    var total=0;
    images.forEach(function(img){
        var name=img.id.split('/').pop(), eeImg=ee.Image(img.id), year=extractYear(name);
        var maskedImg=eeImg, removedMask=ee.Image(0);

        Object.keys(masks).forEach(function(rn){
            var mc=masks[rn], rg=REGIONS.filter(ee.Filter.eq(REGION_PROPERTY,rn)), rr=ee.Image(0).paint(rg,1);
            var lm=landcover.select(ee.String('classification_').cat(ee.Number(year).format('%d'))).eq(mc).reduce('sum').gte(1);
            CLASSES_AGUA.forEach(function(c){var wb=landcover.select(ee.String('classification_').cat(ee.Number(year).format('%d'))).eq(c).selfMask().focalMax({radius:90,units:'meters'}).gte(1);lm=lm.blend(wb);});
            lm=lm.multiply(rr);var fm=lm.neq(1);maskedImg=maskedImg.updateMask(fm);removedMask=removedMask.where(rr.eq(1),eeImg.updateMask(fm.not()).select('probability'));
        });

        var conn=maskedImg.select('probability').gt(0).connectedPixelCount({maxSize:100,eightConnected:false});
        maskedImg=maskedImg.where(conn.lte(6),0).selfMask();
        maskedImg=maskedImg.copyProperties(eeImg).set('filter_stage','ft02');

        var dest=COLL_OUT+'/'+name;
        Map.addLayer(eeImg.selfMask(),{min:0,max:1000,palette:['888888']},name+' | BEFORE',false);
        Map.addLayer(removedMask.selfMask(),{min:0,max:1000,palette:['ff0000']},name+' | REMOVED',false);
        Map.addLayer(maskedImg.selfMask(),{min:0,max:1000,palette:['00cc00']},name+' | AFTER',false);

        try{ee.data.getAsset(dest);print('  OK: '+name);}catch(e){total++;print('  Export: '+name);Export.image.toAsset({image:maskedImg.toInt16(),description:(COLLECTION_BASE+STAGE_OUT+'_'+name).substring(0,80).replace(/[^a-zA-Z0-9_]/g,'_'),assetId:dest,pyramidingPolicy:'mode',region:REGIONS.geometry().bounds(),scale:SCALE,maxPixels:1e13});}
    });
    print('Total export: '+total);
}
print('=== M7_02 done ===');
