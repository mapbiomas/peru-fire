/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M7_03
Isencao por Buffer de Focos de Calor

📅 DATA: julho 2026
🏷️ VERSAO: 4.5
============================================================ */

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;
var landcover = ee.Image('projects/mapbiomas-public/assets/peru/collection3/mapbiomas_peru_collection3_integration_v1');
var FOCOS_BASE = 'projects/workspace-ipam/assets/FOGO/monthly-focus-sul-america';

var COLLECTION_BASE = 'propose_a';
var STAGE_IN = '-ft02';
var STAGE_OUT = '-ft03';
var CAMPAIGN = 'MONITOR_01';
var BUFFER_M = 5000;
var REGIOES_FOCOS = ['region1','region2','region3','region4'];
var CLASSES_ISENTAS = [66,12,13];

var PATH_FILTERED = CLASSIFICATIONS_ROOT + 'FILTERED/';
var COLL_IN = PATH_FILTERED + COLLECTION_BASE + STAGE_IN;
var COLL_OUT = PATH_FILTERED + COLLECTION_BASE + STAGE_OUT;
var _focosCache = {};

function ensureFolder(name){
    var p=name.split('/'), cur=CLASSIFICATIONS_ROOT;
    for(var i=0;i<p.length;i++){cur+=p[i];try{ee.data.getAsset(cur)}catch(e){ee.data.createAsset({type:(i===p.length-1&&p[i].indexOf('-ft')!==-1)?'IMAGE_COLLECTION':'FOLDER'},cur)}cur+='/';}
}

function extractYear(name){var m=name.match(/^(\d{4})/);return m?parseInt(m[1],10):new Date().getFullYear();}

function buildFocosBuffer(year,geometry){
    if(_focosCache[year])return _focosCache[year];
    var buffer=ee.Image(0);
    for(var m=1;m<=12;m++){var mm=m<10?'0'+m:''+m;try{var hs=ee.FeatureCollection(FOCOS_BASE+'/focus_'+year+'-'+mm).filterBounds(geometry);var hb=hs.map(function(h){return ee.Feature(h.geometry().buffer(BUFFER_M));});buffer=buffer.where(ee.Image().paint(hb).eq(0),1);}catch(e){}}
    _focosCache[year]=buffer;return buffer;
}

print('=== M7_03 — Hotspot Exemption ===');
print('Collection IN:  ' + COLL_IN);
print('Collection OUT: ' + COLL_OUT);
print('Buffer: '+(BUFFER_M/1000)+'km, Regions: '+REGIOES_FOCOS.join(','));

ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_IN);
ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_OUT);

var images=ee.data.listAssets(COLL_IN).assets.filter(function(a){return a.type==='IMAGE';});

if(images.length===0){
    print('Nenhuma imagem encontrada.');
}else{
    Map.addLayer(REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}),{},'Regions');
    Map.centerObject(REGIONS);
    var total=0;
    images.forEach(function(img){
        var name=img.id.split('/').pop(), eeImg=ee.Image(img.id), year=extractYear(name), geometry=REGIONS.geometry();
        var focosBuf=buildFocosBuffer(year,geometry);

        var lulcIsentas=landcover.select(ee.String('classification_').cat(ee.Number(year).format('%d'))).eq(CLASSES_ISENTAS).reduce('sum').gte(1);
        var exemption=ee.Image(0);
        REGIOES_FOCOS.forEach(function(rn){var rg=REGIONS.filter(ee.Filter.eq(REGION_PROPERTY,rn));var rr=ee.Image(0).paint(rg,1);exemption=exemption.where(focosBuf.multiply(lulcIsentas).multiply(rr).eq(1),1);});
        exemption=exemption.selfMask();

        var outImg=eeImg.unmask(0);
        outImg=outImg.where(exemption.eq(1).and(eeImg.mask().not()),eeImg.unmask(0));
        outImg=outImg.updateMask(eeImg.mask().or(exemption.eq(1))).selfMask();
        outImg=outImg.copyProperties(eeImg).set('filter_stage','ft03');

        var dest=COLL_OUT+'/'+name;
        Map.addLayer(focosBuf.selfMask(),{min:0,max:1,palette:['ff8800']},'Hotspot buffer '+year,false);
        Map.addLayer(exemption,{min:0,max:1,palette:['00ff00']},name+' | EXEMPT',false);
        Map.addLayer(ee.Image(eeImg).select(0).selfMask(),{min:0,max:1000,palette:['888888']},name+' | BEFORE',false);
        Map.addLayer(ee.Image(outImg).select(0).selfMask(),{min:0,max:1000,palette:['ff00ff']},name+' | AFTER',false);

        try{ee.data.getAsset(dest);print('  OK: '+name);}catch(e){total++;print('  Export: '+name);Export.image.toAsset({image:outImg.toInt16(),description:(CAMPAIGN+'_ft03_'+COLLECTION_BASE+'_'+name).substring(0,80).replace(/[^a-zA-Z0-9_]/g,'_'),assetId:dest,pyramidingPolicy:'mode',region:REGIONS.geometry().bounds(),scale:SCALE,maxPixels:1e13});}
    });
    print('Total export: '+total);
}
print('=== M7_03 done ===');
