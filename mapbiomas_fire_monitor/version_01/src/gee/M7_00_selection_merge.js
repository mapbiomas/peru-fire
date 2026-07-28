/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M7_00
Selection and Export (UI) — Formulario Corrido v3.1

📅 DATA: julho 2026
🏷️ VERSAO: 3.1

📌 SEÇÕES COM FUNDO COLORIDO:
  CONFIG — cinza   |   PERIODO — azul claro
  REGIOES — cinza  |   CONFIRMAR — verde claro
********************************************/

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;
var START_YEAR = 2025;
var APP_LANG = 'pt';

var L = (function(){
    var d={
        pt:{title:'M7 — Selecao e Export',cfg:'CONFIGURACAO',period:'PERIODO',regions:'REGIOES',confirm:'CONFIRMAR',campaign:'Campanha',existing:'Colecoes existentes',new_title:'Criar nova',select:'Selecionar',create:'Criar e selecionar',placeholder:'ex: propose_a',year:'Ano',month:'Mes',load:'Carregar',loading:'Carregando...',no_data:'Sem dados.',select_all:'Selecionar todos',clear_all:'Limpar',target:'Collection',export_btn:'Exportar',pre_title:'Pre-Confirmacao',pre_body:'Sera criado/atualizado:',pre_warn:'O GEE solicitara confirmacao.',pre_ok:'OK',cancel:'Cancelar',done:'Concluido!',one:'1 modelo',none:'nenhum'},
        es:{title:'M7 — Seleccion',cfg:'CONFIG',period:'PERIODO',regions:'REGIONES',confirm:'CONFIRMAR',campaign:'Campana',existing:'Colecciones existentes',new_title:'Crear nueva',select:'Seleccionar',create:'Crear y seleccionar',placeholder:'ej: propose_a',year:'Ano',month:'Mes',load:'Cargar',loading:'Cargando...',no_data:'Sin datos.',select_all:'Todos',clear_all:'Limpiar',target:'Coleccion',export_btn:'Exportar',pre_title:'Pre-Confirmacion',pre_body:'Se creara:',pre_warn:'GEE solicitara confirmacion.',pre_ok:'OK',cancel:'Cancelar',done:'Completado!',one:'1 modelo',none:'ninguno'},
        en:{title:'M7 — Selection & Export',cfg:'CONFIGURATION',period:'PERIOD',regions:'REGIONS',confirm:'CONFIRM',campaign:'Campaign',existing:'Existing collections',new_title:'Create new',select:'Select',create:'Create & select',placeholder:'e.g. propose_a',year:'Year',month:'Month',load:'Load',loading:'Loading...',no_data:'No data.',select_all:'Select all',clear_all:'Clear',target:'Collection',export_btn:'Export',pre_title:'Pre-Confirmation',pre_body:'Will create/update:',pre_warn:'GEE will prompt for confirmation.',pre_ok:'OK',cancel:'Cancel',done:'Done!',one:'1 model',none:'none'},
        fr:{title:'M7 — Selection',cfg:'CONFIG',period:'PERIODE',regions:'REGIONS',confirm:'CONFIRMER',campaign:'Campagne',existing:'Existantes',new_title:'Creer',select:'Selectionner',create:'Creer',placeholder:'ex: propose_a',year:'Annee',month:'Mois',load:'Charger',loading:'Chargement...',no_data:'Pas de donnees.',select_all:'Tous',clear_all:'Effacer',target:'Collection',export_btn:'Exporter',pre_title:'Pre-Confirmation',pre_body:'Va creer:',pre_warn:'GEE demandera confirmation.',pre_ok:'OK',cancel:'Annuler',done:'Termine!',one:'1 modele',none:'aucun'},
        id:{title:'M7 — Seleksi',cfg:'KONFIG',period:'PERIODE',regions:'WILAYAH',confirm:'KONFIRMASI',campaign:'Kampanye',existing:'Koleksi ada',new_title:'Buat baru',select:'Pilih',create:'Buat & pilih',placeholder:'cth: propose_a',year:'Tahun',month:'Bulan',load:'Muat',loading:'Memuat...',no_data:'Tidak ada.',select_all:'Semua',clear_all:'Hapus',target:'Koleksi',export_btn:'Ekspor',pre_title:'Pra-Konfirmasi',pre_body:'Akan dibuat:',pre_warn:'GEE akan minta konfirmasi.',pre_ok:'OK',cancel:'Batal',done:'Selesai!',one:'1 model',none:'tidak ada'},
    };
    return d[APP_LANG]||d.pt;
})();

var COLORS = {
    cfg:     { margin:'4px', padding:'8px', backgroundColor:'#f8f9fa', border:'1px solid #e0e0e0', borderRadius:'6px' },
    period:  { margin:'4px', padding:'8px', backgroundColor:'#f0f4ff', border:'1px solid #c8d6f0', borderRadius:'6px' },
    regions: { margin:'4px', padding:'8px', backgroundColor:'#f8f9fa', border:'1px solid #e0e0e0', borderRadius:'6px' },
    confirm: { margin:'4px', padding:'8px', backgroundColor:'#e8f5e9', border:'1px solid #b8d8ba', borderRadius:'6px' },
    sub:     { margin:'2px 0', padding:'6px', backgroundColor:'#fff', border:'1px solid #e0e0e0', borderRadius:'4px', stretch:'horizontal' },
    divider: { margin:'0 4px', backgroundColor:'#d0d0d0', width:'1px' },
    stack:   { margin:'2px 0', stretch:'horizontal' },
};
var S = {
    lbl:{fontSize:'11px',color:'#555',margin:'2px 0'},
    inp:{stretch:'horizontal',fontSize:'12px',margin:'2px 0'},
    btn_blue:{margin:'2px',padding:'4px 10px',color:'#1a73e8',fontWeight:'bold'},
    btn_green:{margin:'2px',padding:'4px 10px',color:'#0f9d58',fontWeight:'bold'},
    btn_gray:{margin:'2px',padding:'4px 10px',color:'#70757a',fontWeight:'bold'},
    ok:{color:'#0f9d58',fontWeight:'bold',fontSize:'11px'},
    err:{color:'#d32f2f',fontWeight:'bold',fontSize:'11px'},
    pre:{margin:'6px 0',padding:'10px',backgroundColor:'#fff8e1',border:'1px solid #ffcc00',borderRadius:'6px'},
};

var CPAL = ['#e6194b','#3cb44b','#ffe119','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#bfef45','#fabed4','#469990','#dcbeff','#9A6324','#fffac8','#800000'];
var mLayers={}, avMods={}, rMap={}, eyeSt={}, _cbs={};
var cYear=null,cMonth=null,cPeriod='';
var collName='propose_a';

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function ensureFolder(name){
    var p=name.split('/'), cur=CLASSIFICATIONS_ROOT;
    for(var i=0;i<p.length;i++){cur+=p[i];try{ee.data.getAsset(cur)}catch(e){ee.data.createAsset({type:(i===p.length-1&&p[i].indexOf('-ft')!==-1)?'IMAGE_COLLECTION':'FOLDER'},cur)}cur+='/';}
}
function getDK(y,m){return m!==null?y+'_'+('0'+m).slice(-2):''+y;}

// ─── MAP ────────────────────────────────────────────────────────────────────

function mL(id,obj,vis,name){
    if(mLayers[id]){mLayers[id].setEeObject(obj);mLayers[id].setVisParams(vis);mLayers[id].setName(name)}
    else{mLayers[id]=ui.Map.Layer(obj,vis,name);Map.layers().add(mLayers[id]);}
}
function loadMosaic(y,m){
    var dk=getDK(y,m),bs=CATALOG_ROOT+'/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR',img=ee.Image().select();
    ['blue','green','red','nir','swir1','swir2'].forEach(function(b){
        try{var bi=ee.ImageCollection(bs+'/'+b.toLowerCase()).filter(ee.Filter.eq('system:index','image_peru_fire_sentinel2_minnbr_'+b.toLowerCase()+'_'+dk)).mosaic();img=img.addBands(ee.Image(ee.Algorithms.If(bi.bandNames().size().gt(0),bi,ee.Image(0).rename(b.toLowerCase()).updateMask(0))).select([0],[b.toLowerCase()]),null,true)}
        catch(e){img=img.addBands(ee.Image(0).rename(b.toLowerCase()).updateMask(0),null,true)}
    });
    img=img.addBands(img.normalizedDifference(['nir','swir2']).rename('nbr'));
    mL('mosaic_minnbr',img,{bands:['swir1','nir','red'],min:3,max:40,gamma:0.85},'Min NBR '+dk);
}

// ─── CLASSIFICATIONS ────────────────────────────────────────────────────────

function loadClassifications(y,m,cb){
    var dk=getDK(y,m);
    ee.data.listAssets(CLASSIFICATIONS_ROOT+'REGIONAL',{},function(cols){
        if(!cols||!cols.assets){cb({});return} var dirs=cols.assets.filter(function(c){return c.type==='IMAGE_COLLECTION'}),r={},p=dirs.length;if(dirs.length===0){cb({});return}
        dirs.forEach(function(c,idx){var mid=c.id.split('/').pop();ee.data.listAssets(c.id,{},function(imgs){
            if(imgs&&imgs.assets)imgs.assets.forEach(function(img){if(img.type!=='IMAGE')return;var name=img.id.split('/').pop(),parts=name.split('_');var rp=null;for(var i=0;i<parts.length;i++){if(parts[i].indexOf('region')===0){rp=parts[i];break}}if(!rp)return;var ip=null;for(var j=parts.length-1;j>=0;j--){if(/^\d{4}$/.test(parts[j])){ip=parts[j]+(j+1<parts.length&&/^\d{2}$/.test(parts[j+1])?'_'+parts[j+1]:'');break}}if(ip!==dk)return;if(!r[rp])r[rp]=[];if(!r[rp].some(function(x){return x.modelId===mid}))r[rp].push({modelId:mid,assetId:img.id,color:CPAL[idx%15]})});
            p--;if(p===0)cb(r);
        })});
        if(p===0)cb(r);
    });
}

function loadExisting(cb){
    ensureFolder('FILTERED');
    ee.data.listAssets(CLASSIFICATIONS_ROOT+'FILTERED/',{},function(r){
        if(!r||!r.assets){cb([]);return}cb(r.assets.filter(function(a){return a.type==='IMAGE_COLLECTION'}).map(function(a){return a.id.split('/').pop()}).sort());
    });
}

// ─── FORM ───────────────────────────────────────────────────────────────────

var rootBox, regionsBox, confirmBox, contentsBox, ddExisting, txtName;

function buildForm(){
    rootBox = ui.root;
    // Não limpa o root para manter o mapa visível — mas GEE exige root.clear() para reconstruir
    rootBox.clear();
    var root=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{width:'580px',margin:'0',padding:'4px',backgroundColor:'#fff'}});

    // HEADER
    root.add(ui.Label('MapBiomas-Fuego | '+L.title,{fontSize:'14px',fontWeight:'bold',color:'#d32f2f',margin:'4px'}));

    // ═══ CONFIG ═══
    var cCfg=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.cfg});
    cCfg.add(ui.Label(L.cfg,{fontSize:'12px',fontWeight:'bold',color:'#333',margin:'0 0 6px 0'}));
    cCfg.add(ui.Label(L.campaign,S.lbl));
    cCfg.add(ui.Select({items:['MONITOR_01','MONITOR_DEV'],value:'MONITOR_01',style:S.inp}));

    // 2 sub-paineis lado a lado
    var subRow=ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{margin:'6px 0',stretch:'horizontal'}});

    // LEFT: existentes
    var subLeft=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.sub});
    subLeft.add(ui.Label(L.existing,{fontSize:'11px',fontWeight:'bold',color:'#555',margin:'0 0 2px 0'}));
    ddExisting=ui.Select({items:['...'],value:null,style:S.inp,disabled:true});
    subLeft.add(ddExisting);
    var btnSelect=ui.Button({label:L.select,style:S.btn_blue,onClick:function(){
        var v=ddExisting.getValue();if(!v||v==='...')return;
        collName=v.split('-ft')[0]||v;txtName.setValue(collName);refreshAll();
    }});
    subLeft.add(btnSelect);

    // RIGHT: nova
    var subRight=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.sub});
    subRight.add(ui.Label(L.new_title,{fontSize:'11px',fontWeight:'bold',color:'#555',margin:'0 0 2px 0'}));
    txtName=ui.Textbox({placeholder:L.placeholder,value:collName,style:S.inp});
    subRight.add(txtName);
    var btnCreate=ui.Button({label:L.create,style:S.btn_green,onClick:function(){
        var name=txtName.getValue().trim()||collName;collName=name;
        ensureFolder('FILTERED/'+name+'-ft00');
        loadExisting(function(names){
            ddExisting.items().reset(names);ddExisting.setDisabled(false);
            var target=names.filter(function(n){return n.indexOf(name+'-ft')===0;})[0];
            if(target){ddExisting.setValue(target);collName=name;}else{ddExisting.setValue(null);}
            refreshAll();
        });
        print('OK: FILTERED/'+name+'-ft00');
    }});
    subRight.add(btnCreate);
    txtName.onChange(function(v){collName=v;});

    subRow.add(subLeft).add(subRight);
    cCfg.add(subRow);
    root.add(cCfg);

    // ═══ PERIOD ═══
    var cPrd=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.period});
    cPrd.add(ui.Label(L.period,{fontSize:'12px',fontWeight:'bold',color:'#333',margin:'0 0 6px 0'}));

    var today=new Date(); var mY=today.getFullYear(),mM=today.getMonth();
    if(mM===0){mM=12;mY--}
    cYear=mY;cMonth=mM;cPeriod=getDK(mY,mM);

    var sldY=ui.Slider({min:START_YEAR,max:mY,value:mY,step:1,style:{stretch:'horizontal'}});
    var lblY=ui.Label(L.year+': '+mY,S.lbl);
    sldY.onChange(function(v){lblY.setValue(L.year+': '+v);cYear=v;cPeriod=getDK(cYear,cMonth);if(v===mY)sldM.setMax(mM);else sldM.setMax(12);});
    var sldM=ui.Slider({min:1,max:mM,value:mM,step:1,style:{stretch:'horizontal'}});
    var lblM=ui.Label(L.month+': '+('0'+mM).slice(-2),S.lbl);
    sldM.onChange(function(v){lblM.setValue(L.month+': '+('0'+v).slice(-2));cMonth=v;cPeriod=getDK(cYear,cMonth);});

    cPrd.add(lblY).add(sldY).add(lblM).add(sldM);
    cPrd.add(ui.Button({label:L.load,style:S.btn_blue,onClick:function(){
        cPeriod=getDK(cYear,cMonth);loadMosaic(cYear,cMonth);Map.centerObject(REGIONS);
        buildRegionsPanel();
    }}));

    // Contents panel: mostra periodos ja na colecao
    contentsBox=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{margin:'6px 0 0 0'}});
    cPrd.add(contentsBox);
    root.add(cPrd);

    // ═══ REGIONS ═══
    var cRgn=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.regions});
    cRgn.add(ui.Label(L.regions,{fontSize:'12px',fontWeight:'bold',color:'#333',margin:'0 0 6px 0'}));
    regionsBox=ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    cRgn.add(regionsBox);
    root.add(cRgn);
    buildRegionsPanel();

    // ═══ CONFIRM ═══
    var cCfm=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.confirm});
    cCfm.add(ui.Label(L.confirm,{fontSize:'12px',fontWeight:'bold',color:'#333',margin:'0 0 6px 0'}));
    confirmBox=ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    cCfm.add(confirmBox);
    root.add(cCfm);
    buildConfirmPanel();

    rootBox.add(root);
    Map.setOptions('SATELLITE');
    Map.centerObject(REGIONS);
    Map.addLayer(REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}),{},'Regions');

    // Carrega dropdown inicial
    loadExisting(function(names){
        if(names.length===0){ddExisting.items().reset(['(nenhuma)']);ddExisting.setDisabled(true);}
        else {ddExisting.items().reset(names);ddExisting.setDisabled(false);}
    });
    loadCollectionContents();
}

// ─── COLLECTION CONTENTS ────────────────────────────────────────────────────

function loadCollectionContents(){
    if(!contentsBox)return;
    contentsBox.clear();
    var fn=collName+'-ft00';
    var path=CLASSIFICATIONS_ROOT+'FILTERED/'+fn+'/';

    ee.data.listAssets(path,{},function(r){
        var periods=[];
        if(r&&r.assets)periods=r.assets.filter(function(a){return a.type==='IMAGE'}).map(function(a){return a.id.split('/').pop()}).sort().reverse();

        var card=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{margin:'4px 0',padding:'6px',backgroundColor:'#fff',border:'1px solid #c8d6f0',borderRadius:'4px'}});
        card.add(ui.Label(L.existing+': '+fn,{fontSize:'10px',fontWeight:'bold',color:'#1a73e8',margin:'0 0 4px 0'}));

        if(periods.length===0){
            card.add(ui.Label('(vazia)',{fontSize:'10px',color:'#aaa',margin:'2px'}));
        } else {
            var list=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{maxHeight:'140px'}});
            periods.forEach(function(p){
                list.add(ui.Label(' '+p+'  ✅',{fontSize:'11px',fontFamily:'monospace',color:'#0f9d58',margin:'1px 0'}));
            });
            card.add(list);
            card.add(ui.Label('Total: '+periods.length+' | Ultimo: '+periods[0],{fontSize:'10px',color:'#888',margin:'4px 0 0 0'}));
        }
        contentsBox.add(card);
    });
}

// ─── REGIONS ────────────────────────────────────────────────────────────────

function buildRegionsPanel(){
    regionsBox.clear();
    regionsBox.add(ui.Label(L.loading+' '+cPeriod,{fontSize:'10px',color:'#888'}));
    loadClassifications(cYear,cMonth,function(data){
        avMods={};avMods[cPeriod]=data;regionsBox.clear();
        var names=Object.keys(data).sort();if(names.length===0){regionsBox.add(ui.Label(L.no_data,{color:'#d32f2f',margin:'6px'}));buildConfirmPanel();return}
        var hr=ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'0 0 4px 0'}});
        hr.add(ui.Button({label:L.select_all,style:S.btn_blue,onClick:function(){names.forEach(function(r){if(data[r].length>0)rMap[r]=data[r][0].modelId});buildRegionsPanel();buildConfirmPanel();}}));
        hr.add(ui.Button({label:L.clear_all,style:S.btn_gray,onClick:function(){rMap={};buildRegionsPanel();buildConfirmPanel();}}));
        regionsBox.add(hr);
        names.forEach(function(rn){
            var models=data[rn].sort(function(a,b){return a.modelId.localeCompare(b.modelId)});
            var card=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{margin:'2px 0',padding:'4px',backgroundColor:'#fff',border:'1px solid #e0e0e0',borderRadius:'4px'}});
            card.add(ui.Label(rn.replace('region','Region '),{fontSize:'12px',fontWeight:'bold',color:'#1a73e8',margin:'1px 0'}));
            if(!rMap[rn]&&models.length>0)rMap[rn]=models[0].modelId;
            if(!_cbs[rn])_cbs[rn]={};
            models.forEach(function(m){
                var sel=(rMap[rn]===m.modelId);
                var cb=ui.Checkbox({label:m.modelId,value:sel,style:{fontSize:'10px',margin:'1px 4px'}});
                cb.onChange(function(v){if(v){rMap[rn]=m.modelId;Object.keys(_cbs[rn]).forEach(function(k){if(k!==m.modelId)_cbs[rn][k].setValue(false)})}else{if(rMap[rn]===m.modelId)rMap[rn]=null}buildConfirmPanel()});
                _cbs[rn][m.modelId]=cb;
                var eye=ui.Button({label:'o',style:S.btn_gray,onClick:function(){
                    var key=rn+'_'+m.modelId;if(!eyeSt[key])eyeSt[key]=false;eyeSt[key]=!eyeSt[key];
                    if(eyeSt[key]){mL('class_'+key,ee.Image(m.assetId).select(0).divide(10).toByte().selfMask(),{min:0,max:100,palette:['#fcc','#f66','#c00','#600']},m.modelId+'|'+rn);this.style=S.btn_blue}
                    else{if(mLayers['class_'+key]){Map.layers().remove(mLayers['class_'+key]);delete mLayers['class_'+key]}this.style=S.btn_gray}
                }});
                card.add(ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'1px 0',padding:'1px'},widgets:[cb,eye]}));
            });
            regionsBox.add(card);
        });
        buildConfirmPanel();
    });
}

// ─── CONFIRM ────────────────────────────────────────────────────────────────

function buildConfirmPanel(){
    if(!confirmBox)return;
    confirmBox.clear();var fn=collName+'-ft00';
    confirmBox.add(ui.Label(L.target+': '+fn+' / '+cPeriod,{fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'2px',padding:'4px',backgroundColor:'#fff',borderRadius:'3px'}));
    var names=Object.keys(rMap).sort(),hasAll=true;
    names.forEach(function(r){var m=rMap[r];confirmBox.add(ui.Label('  '+r.replace('region','Region ')+': '+(m?m:L.none),m?S.ok:S.err));if(!m)hasAll=false});
    if(names.length===0)confirmBox.add(ui.Label('Nenhuma regiao configurada.',S.err));
    confirmBox.add(ui.Button({label:L.export_btn,style:S.btn_green,disabled:!hasAll||names.length===0,onClick:function(){showPrePopup()}}));
}

// ─── PRE-POPUP ──────────────────────────────────────────────────────────────

function showPrePopup(){
    confirmBox.clear();var fn=collName+'-ft00';
    var bx=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:S.pre});
    bx.add(ui.Label('⚠ '+L.pre_title,{fontSize:'13px',fontWeight:'bold',color:'#cc8800',margin:'2px'}));
    bx.add(ui.Label(L.pre_body,{fontSize:'11px',color:'#333',margin:'2px'}));
    bx.add(ui.Label('FILTERED/'+fn+'/'+cPeriod,{fontSize:'11px',fontWeight:'bold',fontFamily:'monospace',color:'#1a73e8',margin:'2px',padding:'4px',backgroundColor:'#fff'}));
    bx.add(ui.Label(L.pre_warn,{fontSize:'10px',color:'#888',margin:'4px 2px'}));
    var br=ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'4px 0 0 0'}});
    br.add(ui.Button({label:L.cancel,style:S.btn_gray,onClick:function(){buildConfirmPanel()}}));
    br.add(ui.Button({label:L.pre_ok,style:S.btn_green,onClick:function(){doExport()}}));
    bx.add(br);confirmBox.add(bx);
}

// ─── EXPORT ─────────────────────────────────────────────────────────────────

function doExport(){
    confirmBox.clear();confirmBox.add(ui.Label(L.loading,{fontSize:'11px',color:'#1a73e8',margin:'4px'}));
    var fn=collName+'-ft00';ensureFolder('FILTERED/'+fn);
    var rns=Object.keys(rMap).filter(function(r){return!!rMap[r]});if(rns.length===0){confirmBox.add(ui.Label('Erro: nenhuma regiao.',S.err));return}
    var nImg=ee.Image(0).rename('probability'),dImg=ee.Image(0).rename('dayOfYear'),mL=[];
    rns.forEach(function(rn){
        var mid=rMap[rn];mL.push(rn+':'+mid);var assets=avMods[cPeriod]&&avMods[cPeriod][rn];if(!assets)return;
        var found=null;for(var i=0;i<assets.length;i++){if(assets[i].modelId===mid){found=assets[i];break}}if(!found)return;
        var rMask=ee.Image(0).paint(REGIONS.filter(ee.Filter.eq(REGION_PROPERTY,rn)),1),src=ee.Image(found.assetId);
        nImg=nImg.where(rMask.eq(1),src.select(0));dImg=dImg.where(rMask.eq(1),src.select(1));
    });
    nImg=nImg.addBands(dImg).selfMask().set({'region_models':mL.join(','),'campaign':'MONITOR_01','filter_stage':'ft00','period':cPeriod});
    var dest=CLASSIFICATIONS_ROOT+'FILTERED/'+fn+'/'+cPeriod;
    Map.addLayer(nImg.select('probability').selfMask(),{min:0,max:1000,palette:['#fcc','#f00','#600']},'National '+cPeriod,false);
    try{ee.data.getAsset(dest);print('Ja existe: '+dest)}
    catch(e){print('Exportando: '+dest);Export.image.toAsset({image:nImg.toInt16(),description:cPeriod.replace(/_/g,''),assetId:dest,pyramidingPolicy:'mode',region:REGIONS.geometry().bounds(),scale:SCALE,maxPixels:1e13})}
    confirmBox.clear();confirmBox.add(ui.Label(L.done,{fontSize:'12px',color:'#0f9d58',fontWeight:'bold',margin:'4px'}));
    confirmBox.add(ui.Label('FILTERED/'+fn+'/'+cPeriod,{fontSize:'10px',color:'#555',fontFamily:'monospace',margin:'2px'}));
    loadCollectionContents();
}

function refreshAll(){buildRegionsPanel();buildConfirmPanel();loadCollectionContents();}

// ─── INIT ───────────────────────────────────────────────────────────────────

buildForm();
print('M7_00 3.1 carregado.');
