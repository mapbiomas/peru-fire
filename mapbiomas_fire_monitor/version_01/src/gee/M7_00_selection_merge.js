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
        pt:{title:'M7 — Selecao e Export',cfg:'CONFIGURACAO',period:'PERIODO',regions:'REGIOES',confirm:'CONFIRMAR',campaign:'Campanha',existing:'Predicoes existentes',new_title:'Criar nova',select:'Selecionar',create:'Criar e selecionar',placeholder:'ex: propose_a',year:'Ano',month:'Mes',load:'Carregar',loading:'Carregando...',no_data:'Sem dados.',select_all:'Selecionar todos',clear_all:'Limpar',target:'Predicao',export_btn:'Exportar',pre_title:'Pre-Confirmacao',pre_body:'Sera criado/atualizado:',pre_warn:'O GEE solicitara confirmacao.',pre_ok:'OK',cancel:'Cancelar',done:'Concluido!',one:'1 modelo',none:'nenhum'},
        es:{title:'M7 — Seleccion',cfg:'CONFIG',period:'PERIODO',regions:'REGIONES',confirm:'CONFIRMAR',campaign:'Campana',existing:'Predicciones existentes',new_title:'Crear nueva',select:'Seleccionar',create:'Crear y seleccionar',placeholder:'ej: propose_a',year:'Ano',month:'Mes',load:'Cargar',loading:'Cargando...',no_data:'Sin datos.',select_all:'Todos',clear_all:'Limpiar',target:'Prediccion',export_btn:'Exportar',pre_title:'Pre-Confirmacion',pre_body:'Se creara:',pre_warn:'GEE solicitara confirmacion.',pre_ok:'OK',cancel:'Cancelar',done:'Completado!',one:'1 modelo',none:'ninguno'},
        en:{title:'M7 — Selection & Export',cfg:'CONFIGURATION',period:'PERIOD',regions:'REGIONS',confirm:'CONFIRM',campaign:'Campaign',existing:'Existing predictions',new_title:'Create new',select:'Select',create:'Create & select',placeholder:'e.g. propose_a',year:'Year',month:'Month',load:'Load',loading:'Loading...',no_data:'No data.',select_all:'Select all',clear_all:'Clear',target:'Prediction',export_btn:'Export',pre_title:'Pre-Confirmation',pre_body:'Will create/update:',pre_warn:'GEE will prompt for confirmation.',pre_ok:'OK',cancel:'Cancel',done:'Done!',one:'1 model',none:'none'},
        fr:{title:'M7 — Selection',cfg:'CONFIG',period:'PERIODE',regions:'REGIONS',confirm:'CONFIRMER',campaign:'Campagne',existing:'Predictions existantes',new_title:'Creer',select:'Selectionner',create:'Creer',placeholder:'ex: propose_a',year:'Annee',month:'Mois',load:'Charger',loading:'Chargement...',no_data:'Pas de donnees.',select_all:'Tous',clear_all:'Effacer',target:'Prediction',export_btn:'Exporter',pre_title:'Pre-Confirmation',pre_body:'Va creer:',pre_warn:'GEE demandera confirmation.',pre_ok:'OK',cancel:'Annuler',done:'Termine!',one:'1 modele',none:'aucun'},
        id:{title:'M7 — Seleksi',cfg:'KONFIG',period:'PERIODE',regions:'WILAYAH',confirm:'KONFIRMASI',campaign:'Kampanye',existing:'Prediksi yang ada',new_title:'Buat baru',select:'Pilih',create:'Buat & pilih',placeholder:'cth: propose_a',year:'Tahun',month:'Bulan',load:'Muat',loading:'Memuat...',no_data:'Tidak ada.',select_all:'Semua',clear_all:'Hapus',target:'Prediksi',export_btn:'Ekspor',pre_title:'Pra-Konfirmasi',pre_body:'Akan dibuat:',pre_warn:'GEE akan minta konfirmasi.',pre_ok:'OK',cancel:'Batal',done:'Selesai!',one:'1 model',none:'tidak ada'},
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
var mLayers={}, avMods={}, rMap={}, _cbs={}, regionNames=[];
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
            if(imgs&&imgs.assets)imgs.assets.forEach(function(img){if(img.type!=='IMAGE')return;var name=img.id.split('/').pop(),parts=name.split('_');var rp=null;for(var i=0;i<regionNames.length;i++){if(name.indexOf(regionNames[i])!==-1){rp=regionNames[i];break}}if(!rp)return;var ip=null;for(var j=parts.length-1;j>=0;j--){if(/^\d{4}$/.test(parts[j])){ip=parts[j]+(j+1<parts.length&&/^\d{2}$/.test(parts[j+1])?'_'+parts[j+1]:'');break}}if(ip!==dk)return;if(!r[rp])r[rp]=[];if(!r[rp].some(function(x){return x.modelId===mid}))r[rp].push({modelId:mid,assetId:img.id,color:CPAL[idx%15]})});
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

var rootBox, regionsBox, confirmBox, contentsBox, summaryBox, ddExisting, ddPeriod, txtName;

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

    // Contents panel: mostra periodos ja na colecao
    contentsBox=ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    cPrd.add(contentsBox);

    // Period select: populado dinamicamente pelos conteudos da ft00
    ddPeriod=ui.Select({items:['...'],value:null,style:S.inp,disabled:true});
    ddPeriod.onChange(function(v){
        if(!v||v==='...'||v.indexOf('(')!==-1)return;
        cPeriod=v.split(' ')[0];
        var y=parseInt(cPeriod.substring(0,4),10), m=parseInt(cPeriod.substring(5,7),10);
        cYear=y;cMonth=m;
        loadMosaic(cYear,cMonth);Map.centerObject(REGIONS);
        buildRegionsPanel();
    });
    cPrd.add(ddPeriod);
    root.add(cPrd);

    // ═══ REGIONS ═══
    var cRgn=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:COLORS.regions});
    cRgn.add(ui.Label(L.regions,{fontSize:'12px',fontWeight:'bold',color:'#333',margin:'0 0 6px 0'}));
    summaryBox=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{margin:'0 0 6px 0',padding:'6px',backgroundColor:'#fff',border:'1px solid #e0e0e0',borderRadius:'4px'}});
    cRgn.add(summaryBox);
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
    regionNames=REGIONS.aggregate_array(REGION_PROPERTY).distinct().getInfo().sort();

    // Carrega dropdown inicial
    loadExisting(function(names){
        if(names.length===0){ddExisting.items().reset(['(nenhuma)']);ddExisting.setDisabled(true);}
        else {
            ddExisting.items().reset(names);ddExisting.setDisabled(false);
            ddExisting.setValue(names[0]);
            collName=names[0].split('-ft')[0]||names[0];
            txtName.setValue(collName);
            refreshAll();
        }
    });
    loadCollectionContents();
}

// ─── PERIOD COUNTS ──────────────────────────────────────────────────────────

function loadPeriodCounts(cb){
    ee.data.listAssets(CLASSIFICATIONS_ROOT+'REGIONAL',{},function(cols){
        var counts={};
        if(!cols||!cols.assets){cb(counts);return}
        var dirs=cols.assets.filter(function(c){return c.type==='IMAGE_COLLECTION'});
        if(dirs.length===0){cb(counts);return}
        var p=dirs.length;
        dirs.forEach(function(c){
            ee.data.listAssets(c.id,{},function(imgs){
                if(imgs&&imgs.assets)imgs.assets.forEach(function(img){
                    if(img.type!=='IMAGE')return;
                    var name=img.id.split('/').pop(),parts=name.split('_'),period=null;
                    for(var j=parts.length-1;j>=0;j--){if(/^\d{4}$/.test(parts[j])){period=parts[j]+(j+1<parts.length&&/^\d{2}$/.test(parts[j+1])?'_'+parts[j+1]:'');break}}
                    if(period)counts[period]=(counts[period]||0)+1;
                });
                p--;if(p===0)cb(counts);
            });
        });
    });
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

        var card=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{margin:'0 0 6px 0',padding:'6px',backgroundColor:'#fff',border:'1px solid #c8d6f0',borderRadius:'4px'}});
        card.add(ui.Label(L.existing+': '+fn,{fontSize:'10px',fontWeight:'bold',color:'#1a73e8',margin:'0 0 4px 0'}));

        if(periods.length===0){
            card.add(ui.Label('(vazia)',{fontSize:'10px',color:'#aaa',margin:'2px'}));
        } else {
            var list=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{maxHeight:'100px'}});
            periods.forEach(function(p){
                list.add(ui.Label(' '+p+'  ✅',{fontSize:'10px',fontFamily:'monospace',color:'#0f9d58',margin:'1px 0'}));
            });
            card.add(list);
            card.add(ui.Label('Total: '+periods.length,{fontSize:'10px',color:'#888',margin:'2px 0 0 0'}));
        }
        contentsBox.add(card);

        // Popula dropdown: periodos NAO na colecao + contagem de predicoes
        if(ddPeriod){
            var today=new Date();var my=today.getFullYear(),mm=today.getMonth();
            if(mm===0){mm=12;my--}
            var all=[];
            for(var y=my;y>=START_YEAR;y--){
                var me=(y===my)?mm:12;
                for(var m=me;m>=1;m--){all.push(y+'_'+('0'+m).slice(-2));}
            }
            var recent=all.filter(function(p){return periods.indexOf(p)===-1;});
            loadPeriodCounts(function(counts){
                var items;
                if(recent.length===0){
                    items=['(todos preenchidos)'];ddPeriod.setDisabled(true);ddPeriod.setValue(null);
                } else {
                    items=recent.map(function(p){return p+' ('+(counts[p]||0)+' pred.)';});
                    ddPeriod.setDisabled(false);
                    ddPeriod.items().reset(items);
                    // Default: most recent period WITH data
                    var defIdx=0;
                    for(var r=0;r<recent.length;r++){if((counts[recent[r]]||0)>1){defIdx=r;break}}
                    ddPeriod.setValue(items[defIdx]);cPeriod=recent[defIdx];
                    cYear=parseInt(recent[defIdx].substring(0,4),10);cMonth=parseInt(recent[defIdx].substring(5,7),10);
                }
            });
        }
    });
}

// ─── REGIONS ────────────────────────────────────────────────────────────────

function buildRegionsPanel(){
    regionsBox.clear();
    regionsBox.add(ui.Label(L.loading+' '+cPeriod,{fontSize:'10px',color:'#888'}));
    var fnInit=collName+'-ft00';
    summaryBox.clear();
    summaryBox.add(ui.Label('Periodo: '+cPeriod+' | Colecao: '+fnInit,{fontSize:'9px',fontFamily:'monospace',color:'#1a73e8',margin:'1px 0'}));
    loadClassifications(cYear,cMonth,function(data){
        avMods={};avMods[cPeriod]=data;regionsBox.clear();
        var hr=ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'0 0 4px 0'}});
        hr.add(ui.Button({label:L.select_all,style:S.btn_blue,onClick:function(){regionNames.forEach(function(r){if(data[r]&&data[r].length>0){rMap[r]=data[r][0].modelId;if(_cbs[r])Object.keys(_cbs[r]).forEach(function(k){_cbs[r][k].setValue(k===rMap[r])})}});buildConfirmPanel();}}));
        hr.add(ui.Button({label:L.clear_all,style:S.btn_gray,onClick:function(){Object.keys(_cbs).forEach(function(rn){Object.keys(_cbs[rn]).forEach(function(k){_cbs[rn][k].setValue(false)})});rMap={};buildConfirmPanel();}}));
        regionsBox.add(hr);

        // Two columns
        var leftCol=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{stretch:'horizontal'}});
        var rightCol=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{stretch:'horizontal'}});
        var mid=Math.ceil(regionNames.length/2);

        regionNames.forEach(function(rn,idx){
            var models=(data[rn]||[]).sort(function(a,b){return a.modelId.localeCompare(b.modelId)});
            var card=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{margin:'2px',padding:'4px',backgroundColor:'#fff',border:'1px solid #e0e0e0',borderRadius:'4px'}});
            card.add(ui.Label(rn,{fontSize:'11px',fontWeight:'bold',color:'#1a73e8',margin:'1px 0'}));

            if(models.length===0){
                card.add(ui.Label('(sem predicao)',{fontSize:'10px',color:'#aaa',margin:'2px 0'}));
            } else {
                if(!rMap[rn])rMap[rn]=models[0].modelId;
                if(!_cbs[rn])_cbs[rn]={};
                models.forEach(function(m){
                    var sel=(rMap[rn]===m.modelId);
                    var cb=ui.Checkbox({label:m.modelId,value:sel,style:{fontSize:'10px',margin:'1px 2px'}});
                    cb.onChange(function(v){
                        var key=rn+'_'+m.modelId;
                        if(v){
                            rMap[rn]=m.modelId;
                            Object.keys(_cbs[rn]).forEach(function(k){if(k!==m.modelId)_cbs[rn][k].setValue(false)});
                            mL('class_'+key,ee.Image(m.assetId).select(0).divide(10).toByte().selfMask(),{min:0,max:100,palette:['#fcc','#f66','#c00','#600']},m.modelId+'|'+rn);
                        } else {
                            if(rMap[rn]===m.modelId)rMap[rn]=null;
                            if(mLayers['class_'+key]){Map.layers().remove(mLayers['class_'+key]);delete mLayers['class_'+key]}
                        }
                        buildConfirmPanel();
                    });
                    _cbs[rn][m.modelId]=cb;
                    card.add(cb);
                    if(sel){mL('class_'+rn+'_'+m.modelId,ee.Image(m.assetId).select(0).divide(10).toByte().selfMask(),{min:0,max:100,palette:['#fcc','#f66','#c00','#600']},m.modelId+'|'+rn);}
                });
            }
            var col=idx<mid?leftCol:rightCol;
            col.add(card);
        });

        var rowCols=ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal'},widgets:[leftCol,rightCol]});
        regionsBox.add(rowCols);

        // Update summary card
        summaryBox.clear();
        var fn2=collName+'-ft00';
        summaryBox.add(ui.Label('Periodo: '+cPeriod+' | Colecao: '+fn2,{fontSize:'9px',fontFamily:'monospace',color:'#1a73e8',margin:'1px 0'}));
        var withData=regionNames.filter(function(r){return data[r]&&data[r].length>0;}).length;
        summaryBox.add(ui.Label('Regioes com dados: '+withData+'/'+regionNames.length,{fontSize:'10px',color:'#333',margin:'1px 0'}));
        var selected=regionNames.filter(function(r){return!!rMap[r]}).length;
        summaryBox.add(ui.Label('Modelos selecionados: '+selected+'/'+withData+' regioes',{fontSize:'9px',color:selected===withData?'#0f9d58':'#e37400',margin:'1px 0'}));
        buildConfirmPanel();
    });
}

// ─── CONFIRM ────────────────────────────────────────────────────────────────

function buildConfirmPanel(){
    if(!confirmBox)return;
    confirmBox.clear();var fn=collName+'-ft00';
    confirmBox.add(ui.Label(L.target+': '+fn+' / '+cPeriod,{fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'2px',padding:'4px',backgroundColor:'#fff',borderRadius:'3px'}));
    var names=Object.keys(rMap).sort(),hasAll=true;
    names.forEach(function(r){var m=rMap[r];confirmBox.add(ui.Label('  '+r+': '+(m?m:L.none),m?S.ok:S.err));if(!m)hasAll=false});
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
print('M7_00 3.7 carregado.');
