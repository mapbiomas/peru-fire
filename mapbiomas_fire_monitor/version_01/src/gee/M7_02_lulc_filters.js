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
// Add missing year bands (duplicate 2024 for years beyond collection range)
var crYear = new Date().getFullYear();
for (var y = 2025; y <= crYear; y++) {
    landcover = landcover.addBands(landcover.select('classification_2024').rename('classification_' + y));
}

var COLLECTION_BASE = 'propose_a';
var STAGE_IN = '-ft01';
var STAGE_OUT = '-ft02';
var CAMPAIGN = 'MONITOR_01';

var CLASSES_AGUA = [26, 31, 33];
var CLASSES_SEM_VEG = [22, 23, 24, 25, 32, 61, 68];
var masks = {
    'region1':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region2':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region3':[24,29],'region4':[24,68,25,29],'region5':[29,24,68],'region6':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region7':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region8':CLASSES_AGUA.concat(CLASSES_SEM_VEG),'region9':[25],'region10':[25]
};

var LULC_PALETTE = require('users/mapbiomas/modules:Palettes.js').get('brazil');

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

ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_IN);
ensureFolder('FILTERED/'+COLLECTION_BASE+STAGE_OUT);

ee.data.listAssets(COLL_IN,{},function(result){
var images=[];
if(result&&result.assets)images=result.assets.filter(function(a){return a.type==='IMAGE';});

if(images.length===0){
    print('Nenhuma imagem encontrada.');
}else{
    Map.addLayer(REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}),{},'Regions');
    Map.centerObject(REGIONS);
    Map.addLayer(landcover.select('classification_2024').selfMask(),{min:0,max:72,palette:LULC_PALETTE},'LULC Peru',false);

    // Period panel (bottom-left)
    var periodPanel = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),
        style:{position:'bottom-left',maxHeight:'60%',width:'200px',padding:'4px',
               backgroundColor:'rgba(255,255,255,0.92)',border:'1px solid #ccc',borderRadius:'4px'}});
    periodPanel.add(ui.Label('PERIODOS',{fontWeight:'bold',fontSize:'11px',margin:'2px'}));
    var activeLayer = null;
    images.forEach(function(img,idx){
        var n=img.id.split('/').pop();
        var cb=ui.Checkbox({label:n,value:idx===0,style:{fontSize:'10px',margin:'1px 2px'}});
        cb.onChange(function(v){if(!v)return;
            for(var w=0;w<periodPanel.widgets().length();w++){var ww=periodPanel.widgets().get(w);if(ww!==cb&&ww.setValue)try{ww.setValue(false)}catch(e){}}
            if(activeLayer)Map.layers().remove(activeLayer);
            activeLayer=ui.Map.Layer(ee.Image(img.id).select(0).selfMask(),{min:0,max:1000,palette:['#fcc','#f66','#c00','#600']},n+' | BEFORE');
            Map.layers().add(activeLayer);
        });
        periodPanel.add(cb);
    });
    Map.add(periodPanel);

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
        Map.addLayer(ee.Image(eeImg).select(0).selfMask(),{min:0,max:1000,palette:['888888']},name+' | BEFORE',false);
        Map.addLayer(ee.Image(removedMask).select(0).selfMask(),{min:0,max:1000,palette:['ff0000']},name+' | REMOVED',false);
        Map.addLayer(ee.Image(maskedImg).select(0).selfMask(),{min:0,max:1000,palette:['00cc00']},name+' | AFTER',false);

        try{ee.data.getAsset(dest);print('  OK: '+name);}catch(e){total++;print('  Export: '+name);Export.image.toAsset({image:ee.Image(maskedImg).toInt16(),description:(CAMPAIGN+'_ft02_'+COLLECTION_BASE+'_'+name).substring(0,80).replace(/[^a-zA-Z0-9_]/g,'_'),assetId:dest,pyramidingPolicy:'mode',region:REGIONS.geometry().bounds(),scale:SCALE,maxPixels:1e13});}
    });
    print('Total export: '+total);
}
});
print('=== M7_02 done ===');
