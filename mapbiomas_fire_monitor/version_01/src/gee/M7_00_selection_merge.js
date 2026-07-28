/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M7_00
Selection and Export (UI) — Formulario Corrido

📅 DATA: julho 2026
🏷️ VERSAO: 3.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
Formulario unico (sem abas) para:
1. Selecionar campanha
2. Escolher colecao existente OU criar nova
3. Selecionar periodo e visualizar mosaico min NBR
4. Atribuir modelo DNN por regiao
5. Exportar imagem nacional para FILTERED/{collection}-ft00/

🌍 IDIOMAS: pt, es, en, fr, id
********************************************/

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;
var START_YEAR = 2025;
var APP_LANG = 'pt';

// ─── IDIOMAS ────────────────────────────────────────────────────────────────
var L = (function () {
    var d = {
        pt: { title:'M7 — Selecao e Export', section_config:'CONFIGURACAO', section_period:'PERIODO', section_regions:'REGIOES', section_confirm:'CONFIRMAR', campaign:'Campanha', existing:'Adicionar a existente', existing_empty:'(carregando...)', existing_none:'(nenhuma colecao)', or:'── OU ──', new_title:'Criar nova', collection_placeholder:'ex: propose_a', create:'Criar e selecionar', year:'Ano', month:'Mes', load:'Carregar periodo', loading:'Carregando...', no_data:'Sem dados para o periodo.', select_all:'Selecionar todos', clear_all:'Limpar todos', collection_target:'Collection', export_btn:'Exportar', confirm_title:'Confirmar Exportacao', pre_title:'Pre-Confirmacao', pre_body:'Sera criada/atualizada:', pre_warn:'O GEE solicitara confirmacao no navegador.', pre_ok:'OK, continuar', cancel:'Cancelar', done:'Concluido!', label_status_one:'1 modelo', label_status_none:'nenhum' },
        es: { title:'M7 — Seleccion', section_config:'CONFIGURACION', section_period:'PERIODO', section_regions:'REGIONES', section_confirm:'CONFIRMAR', campaign:'Campana', existing:'Agregar a existente', existing_empty:'(cargando...)', existing_none:'(ninguna)', or:'── O ──', new_title:'Crear nueva', collection_placeholder:'ej: propose_a', create:'Crear y seleccionar', year:'Ano', month:'Mes', load:'Cargar periodo', loading:'Cargando...', no_data:'Sin datos.', select_all:'Todos', clear_all:'Limpiar', collection_target:'Coleccion', export_btn:'Exportar', confirm_title:'Confirmar', pre_title:'Pre-Confirmacion', pre_body:'Se creara:', pre_warn:'GEE solicitara confirmacion.', pre_ok:'OK', cancel:'Cancelar', done:'Completado!', label_status_one:'1 modelo', label_status_none:'ninguno' },
        en: { title:'M7 — Selection & Export', section_config:'CONFIGURATION', section_period:'PERIOD', section_regions:'REGIONS', section_confirm:'CONFIRM', campaign:'Campaign', existing:'Add to existing', existing_empty:'(loading...)', existing_none:'(none)', or:'── OR ──', new_title:'Create new', collection_placeholder:'e.g. propose_a', create:'Create & select', year:'Year', month:'Month', load:'Load period', loading:'Loading...', no_data:'No data.', select_all:'Select all', clear_all:'Clear', collection_target:'Collection', export_btn:'Export', confirm_title:'Confirm Export', pre_title:'Pre-Confirmation', pre_body:'Will create/update:', pre_warn:'GEE will prompt for confirmation.', pre_ok:'OK, continue', cancel:'Cancel', done:'Done!', label_status_one:'1 model', label_status_none:'none' },
        fr: { title:'M7 — Selection', section_config:'CONFIGURATION', section_period:'PERIODE', section_regions:'REGIONS', section_confirm:'CONFIRMER', campaign:'Campagne', existing:'Ajouter a existante', existing_empty:'(chargement...)', existing_none:'(aucune)', or:'── OU ──', new_title:'Creer', collection_placeholder:'ex: propose_a', create:'Creer', year:'Annee', month:'Mois', load:'Charger', loading:'Chargement...', no_data:'Pas de donnees.', select_all:'Tous', clear_all:'Effacer', collection_target:'Collection', export_btn:'Exporter', confirm_title:'Confirmer', pre_title:'Pre-Confirmation', pre_body:'Va creer:', pre_warn:'GEE demandera confirmation.', pre_ok:'OK', cancel:'Annuler', done:'Termine!', label_status_one:'1 modele', label_status_none:'aucun' },
        id: { title:'M7 — Seleksi', section_config:'KONFIGURASI', section_period:'PERIODE', section_regions:'WILAYAH', section_confirm:'KONFIRMASI', campaign:'Kampanye', existing:'Tambah ke yang ada', existing_empty:'(memuat...)', existing_none:'(tidak ada)', or:'── ATAU ──', new_title:'Buat baru', collection_placeholder:'cth: propose_a', create:'Buat & pilih', year:'Tahun', month:'Bulan', load:'Muat periode', loading:'Memuat...', no_data:'Tidak ada data.', select_all:'Pilih semua', clear_all:'Hapus', collection_target:'Koleksi', export_btn:'Ekspor', confirm_title:'Konfirmasi', pre_title:'Pra-Konfirmasi', pre_body:'Akan dibuat:', pre_warn:'GEE akan minta konfirmasi.', pre_ok:'OK', cancel:'Batal', done:'Selesai!', label_status_one:'1 model', label_status_none:'tidak ada' },
    };
    return d[APP_LANG] || d.pt;
})();

// ─── ESTADOS ─────────────────────────────────────────────────────────────────
var S = {
    tab_inactive:  { margin:'0px', padding:'6px 12px', border:'1px solid #d3d3d3', color:'#70757a', backgroundColor:'#f1f3f4', stretch:'horizontal', fontSize:'12px' },
    section:       { margin:'0px', padding:'8px' },
    sectionTitle:  { fontSize:'13px', fontWeight:'bold', color:'#333', margin:'2px 0px 6px 0px' },
    card:          { margin:'4px 0px', padding:'6px', border:'1px solid #e0e0e0', backgroundColor:'#fafafa', borderRadius:'4px' },
    row:           { margin:'2px 0px', padding:'2px', stretch:'horizontal' },
    lbl:           { margin:'1px 0px', fontSize:'11px', color:'#555' },
    inp:           { margin:'2px 0px', stretch:'horizontal', fontSize:'12px' },
    btn_blue:      { margin:'2px', padding:'4px 10px', color:'#1a73e8', fontWeight:'bold' },
    btn_green:     { margin:'2px', padding:'4px 10px', color:'#0f9d58', fontWeight:'bold' },
    btn_gray:      { margin:'2px', padding:'4px 10px', color:'#70757a', fontWeight:'bold' },
    status_ok:     { color:'#0f9d58', fontWeight:'bold', fontSize:'11px' },
    status_err:    { color:'#d32f2f', fontWeight:'bold', fontSize:'11px' },
    orLabel:       { fontSize:'10px', color:'#aaa', textAlign:'center', margin:'4px 0px', stretch:'horizontal' },
    pre_box:       { margin:'6px 0px', padding:'10px', backgroundColor:'#fff8e1', border:'1px solid #ffcc00', borderRadius:'6px' },
};

var CLASS_PALETTE = ['#e6194b','#3cb44b','#ffe119','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#bfef45','#fabed4','#469990','#dcbeff','#9A6324','#fffac8','#800000'];

var managedLayers = {};
var availableModels = {};
var regionModelMap = {};
var regionEyeState = {};
var _cbStore = {};
var currentYear = null, currentMonth = null, currentPeriodKey = '';
var collectionName = 'propose_a';

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function ensureFolder(name) {
    var parts = name.split('/');
    var cur = CLASSIFICATIONS_ROOT;
    for (var i = 0; i < parts.length; i++) {
        cur += parts[i];
        try { ee.data.getAsset(cur); }
        catch (e) { ee.data.createAsset({ type: (i === parts.length - 1 && parts[i].indexOf('-ft') !== -1) ? 'IMAGE_COLLECTION' : 'FOLDER' }, cur); }
        cur += '/';
    }
}

function getDateKey(y, m) {
    return m !== null ? y + '_' + ('0' + m).slice(-2) : '' + y;
}

// ─── MAP ────────────────────────────────────────────────────────────────────

function mLayer(id, obj, vis, name) {
    if (managedLayers[id]) { managedLayers[id].setEeObject(obj); managedLayers[id].setVisParams(vis); managedLayers[id].setName(name); }
    else { managedLayers[id] = ui.Map.Layer(obj, vis, name); Map.layers().add(managedLayers[id]); }
}

function mRemoveClass() { Object.keys(managedLayers).forEach(function(k){if(k.indexOf('class_')===0){Map.layers().remove(managedLayers[k]);delete managedLayers[k];}}); }

function loadMosaic(year, month) {
    var dk = getDateKey(year, month);
    var bs = CATALOG_ROOT + '/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR';
    var m = ee.Image().select();
    ['blue','green','red','nir','swir1','swir2'].forEach(function(b){
        try {var bi=ee.ImageCollection(bs+'/'+b.toLowerCase()).filter(ee.Filter.eq('system:index','image_peru_fire_sentinel2_minnbr_'+b.toLowerCase()+'_'+dk)).mosaic(); var s=ee.Image(ee.Algorithms.If(bi.bandNames().size().gt(0),bi,ee.Image(0).rename(b.toLowerCase()).updateMask(0))); m=m.addBands(s.select([0],[b.toLowerCase()]),null,true);}
        catch(e){m=m.addBands(ee.Image(0).rename(b.toLowerCase()).updateMask(0),null,true);}
    });
    m = m.addBands(m.normalizedDifference(['nir','swir2']).rename('nbr'));
    mLayer('mosaic_minnbr', m, {bands:['swir1','nir','red'],min:3,max:40,gamma:0.85}, 'Min NBR '+dk);
}

// ─── CLASSIFICATIONS ────────────────────────────────────────────────────────

function loadClassifications(year, month, cb) {
    var dk = getDateKey(year, month);
    ee.data.listAssets(CLASSIFICATIONS_ROOT+'REGIONAL',{},function(cols){
        if(!cols||!cols.assets){cb({});return;}
        var dirs=cols.assets.filter(function(c){return c.type==='IMAGE_COLLECTION';});
        if(dirs.length===0){cb({});return;}
        var r={}; var p=dirs.length;
        dirs.forEach(function(c,idx){
            var mid=c.id.split('/').pop();
            ee.data.listAssets(c.id,{},function(imgs){
                if(imgs&&imgs.assets)imgs.assets.forEach(function(img){
                    if(img.type!=='IMAGE')return;
                    var name=img.id.split('/').pop(), parts=name.split('_');
                    var rp=null; for(var i=0;i<parts.length;i++){if(parts[i].indexOf('region')===0){rp=parts[i];break;}} if(!rp)return;
                    var ip=null; for(var j=parts.length-1;j>=0;j--){if(/^\d{4}$/.test(parts[j])){ip=parts[j]+(j+1<parts.length&&/^\d{2}$/.test(parts[j+1])?'_'+parts[j+1]:'');break;}} if(ip!==dk)return;
                    if(!r[rp])r[rp]=[];
                    if(!r[rp].some(function(x){return x.modelId===mid;})) r[rp].push({modelId:mid,assetId:img.id,color:CLASS_PALETTE[idx%15]});
                });
                p--; if(p===0)cb(r);
            });
        });
        if(p===0)cb(r);
    });
}

// ─── EXISTING ────────────────────────────────────────────────────────────────

function loadExisting(cb) {
    ensureFolder('FILTERED');
    ee.data.listAssets(CLASSIFICATIONS_ROOT+'FILTERED/',{},function(r){
        if(!r||!r.assets){cb([]);return;}
        cb(r.assets.filter(function(a){return a.type==='IMAGE_COLLECTION';}).map(function(a){return a.id.split('/').pop();}).sort());
    });
}

// ─── FORM ───────────────────────────────────────────────────────────────────

function buildForm() {
    ui.root.clear();
    var root = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:{width:'580px',margin:'0px',padding:'4px',backgroundColor:'#fff'}});
    root.add(ui.Label('MapBiomas-Fuego | '+L.title, {fontSize:'14px',fontWeight:'bold',color:'#d32f2f',margin:'4px'}));

    // ═══ CONFIG ═══
    var secCfg = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:S.section});
    secCfg.add(ui.Label('— '+L.section_config, S.sectionTitle));

    // Campaign
    secCfg.add(ui.Label(L.campaign, S.lbl));
    var ddCampaign = ui.Select({items:['MONITOR_01','MONITOR_DEV'], value:'MONITOR_01', style:S.inp});
    secCfg.add(ddCampaign);

    // Existing dropdown
    secCfg.add(ui.Label(L.existing, S.lbl));
    var ddExisting = ui.Select({items:[L.existing_empty], value:null, style:S.inp, disabled:true});
    secCfg.add(ddExisting);

    loadExisting(function(names){
        if(names.length===0){ddExisting.items().reset([L.existing_none]);ddExisting.setDisabled(true);}
        else {ddExisting.items().reset(names);ddExisting.setDisabled(false);}
    });

    // OR separator
    secCfg.add(ui.Label(L.or, S.orLabel));

    // New collection
    secCfg.add(ui.Label(L.new_title, S.lbl));
    var txtName = ui.Textbox({placeholder:L.collection_placeholder, value:collectionName, style:S.inp});
    secCfg.add(txtName);
    var btnCreate = ui.Button({label:L.create, style:S.btn_green, onClick:function(){
        collectionName = txtName.getValue().trim() || collectionName;
        ensureFolder('FILTERED/'+collectionName+'-ft00');
        print('OK: FILTERED/'+collectionName+'-ft00');
        buildRegionsSection(regionsPanel);
        buildConfirmSection(confirmPanel);
    }});
    secCfg.add(btnCreate);

    ddExisting.onChange(function(v){if(v&&v.indexOf('(')===-1){txtName.setValue(v); collectionName = v; buildRegionsSection(regionsPanel); buildConfirmSection(confirmPanel);}});
    txtName.onChange(function(v){collectionName=v; buildConfirmSection(confirmPanel);});

    root.add(secCfg);
    root.add(ui.Label('──────────────────────────────', {fontSize:'9px',color:'#ddd',margin:'0',stretch:'horizontal'}));

    // ═══ PERIOD ═══
    var secPeriod = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:S.section});
    secPeriod.add(ui.Label('— '+L.section_period, S.sectionTitle));

    var today = new Date();
    var mY=today.getFullYear(), mM=today.getMonth();
    if(mM===0){mM=12;mY--;}
    var yrs=[]; for(var y=START_YEAR;y<=mY;y++)yrs.push({label:''+y,value:y}); yrs.reverse();
    var mths=[]; for(var m=mM;m>=1;m--){var mm=m<10?'0'+m:''+m;mths.push({label:mm,value:m});}
    currentYear=mY; currentMonth=mths[0].value; currentPeriodKey=getDateKey(mY,mths[0].value);

    var ddY = ui.Select({items:yrs.map(function(y){return y.label;}),value:''+mY,style:S.inp});
    var ddM = ui.Select({items:mths.map(function(m){return m.label;}),value:mths[0].label,style:S.inp});

    ddY.onChange(function(v){currentYear=parseInt(v,10);});
    ddM.onChange(function(v){currentMonth=parseInt(v,10);});
    var btnLoad = ui.Button({label:L.load, style:S.btn_blue, onClick:function(){
        currentPeriodKey = getDateKey(currentYear, currentMonth);
        loadMosaic(currentYear, currentMonth);
        Map.centerObject(REGIONS);
        buildRegionsSection(regionsPanel);
    }});

    var rowP = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:S.row});
    rowP.add(ui.Label(L.year,S.lbl)); rowP.add(ddY);
    rowP.add(ui.Label(L.month,S.lbl)); rowP.add(ddM); rowP.add(btnLoad);
    secPeriod.add(rowP);
    root.add(secPeriod);
    root.add(ui.Label('──────────────────────────────', {fontSize:'9px',color:'#ddd',margin:'0',stretch:'horizontal'}));

    // ═══ REGIONS ═══
    var regionsPanel = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    var secRegions = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:S.section});
    secRegions.add(ui.Label('— '+L.section_regions, S.sectionTitle));
    secRegions.add(regionsPanel);
    root.add(secRegions);
    buildRegionsSection(regionsPanel);
    root.add(ui.Label('──────────────────────────────', {fontSize:'9px',color:'#ddd',margin:'0',stretch:'horizontal'}));

    // ═══ CONFIRM ═══
    var confirmPanel = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    var secConfirm = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:S.section});
    secConfirm.add(ui.Label('— '+L.section_confirm, S.sectionTitle));
    secConfirm.add(confirmPanel);
    root.add(secConfirm);
    buildConfirmSection(confirmPanel);

    ui.root.add(root);
    Map.setOptions('SATELLITE');
    Map.centerObject(REGIONS);
    Map.addLayer(REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}),{},'Regions');
}

// ─── REGIONS SECTION ────────────────────────────────────────────────────────

function buildRegionsSection(panel) {
    panel.clear();
    panel.add(ui.Label(L.loading+' '+currentPeriodKey, {fontSize:'10px',color:'#888'}));

    loadClassifications(currentYear, currentMonth, function(data){
        availableModels={};
        availableModels[currentPeriodKey]=data;
        panel.clear();
        var names=Object.keys(data).sort();
        if(names.length===0){panel.add(ui.Label(L.no_data,{color:'#d32f2f',fontSize:'12px',margin:'6px'}));return;}

        var hr=ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:S.row});
        hr.add(ui.Button({label:L.select_all,style:S.btn_blue,onClick:function(){names.forEach(function(r){if(data[r].length>0)regionModelMap[r]=data[r][0].modelId;});buildRegionsSection(panel);}}));
        hr.add(ui.Button({label:L.clear_all,style:S.btn_gray,onClick:function(){regionModelMap={};buildRegionsSection(panel);}}));
        panel.add(hr);

        names.forEach(function(rn){
            var models=data[rn].sort(function(a,b){return a.modelId.localeCompare(b.modelId);});
            var card=ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:S.card});
            card.add(ui.Label(rn.replace('region','Region '),{fontSize:'12px',fontWeight:'bold',color:'#1a73e8',margin:'2px 0'}));
            if(!regionModelMap[rn]&&models.length>0)regionModelMap[rn]=models[0].modelId;
            if(!_cbStore[rn])_cbStore[rn]={};
            models.forEach(function(m){
                var sel=(regionModelMap[rn]===m.modelId);
                var cb=ui.Checkbox({label:m.modelId,value:sel,style:{fontSize:'10px',margin:'1px 4px'}});
                cb.onChange(function(v){if(v){regionModelMap[rn]=m.modelId;Object.keys(_cbStore[rn]).forEach(function(k){if(k!==m.modelId)_cbStore[rn][k].setValue(false);});}else{if(regionModelMap[rn]===m.modelId)regionModelMap[rn]=null;}buildConfirmSection();});
                _cbStore[rn][m.modelId]=cb;
                var eye=ui.Button({label:' o ',style:S.btn_gray,onClick:function(){
                    var key=rn+'_'+m.modelId;
                    if(!regionEyeState[key])regionEyeState[key]=false;
                    regionEyeState[key]=!regionEyeState[key];
                    if(regionEyeState[key]){mLayer('class_'+key,ee.Image(m.assetId).select(0).divide(10).toByte().selfMask(),{min:0,max:100,palette:['#ffcccc','#ff6666','#cc0000','#660000']},m.modelId+' | '+rn);this.style=S.btn_blue;}
                    else{if(managedLayers['class_'+key]){Map.layers().remove(managedLayers['class_'+key]);delete managedLayers['class_'+key];}this.style=S.btn_gray;}
                }});
                card.add(ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{margin:'1px 0',padding:'2px',stretch:'horizontal'},widgets:[cb,eye]}));
            });
            panel.add(card);
        });
    });
}

// ─── CONFIRM SECTION ────────────────────────────────────────────────────────

function buildConfirmSection(panel) {
    if (!panel) {
        // Find the confirm panel in the UI
        var secs = ui.root.widgets().get(0).widgets();
        for (var s = 0; s < secs.length(); s++) {
            var w = secs.get(s);
            // Look for the section containing confirm
        }
        return;
    }
    panel.clear();
    var fullName = collectionName + '-ft00';
    panel.add(ui.Label(L.collection_target+': '+fullName+' / '+currentPeriodKey, {fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'2px','padding':'4px',backgroundColor:'#f0f4ff',borderRadius:'3px'}));

    var names = Object.keys(regionModelMap).sort();
    var hasAll = true;
    names.forEach(function(r){
        var m=regionModelMap[r];
        panel.add(ui.Label('  '+r.replace('region','Region ')+': '+(m?m:L.label_status_none), m?S.status_ok:S.status_err));
        if(!m)hasAll=false;
    });
    if(names.length===0)panel.add(ui.Label('Nenhuma regiao configurada.',S.status_err));

    // Export button
    var btnExport = ui.Button({label:L.export_btn, style:S.btn_green, disabled:!hasAll||names.length===0, onClick:function(){
        showPrePopup(panel);
    }});
    panel.add(btnExport);
}

// ─── PRE-POPUP ──────────────────────────────────────────────────────────────

function showPrePopup(parentPanel) {
    parentPanel.clear();
    var fullName = collectionName + '-ft00';
    var box = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:S.pre_box});
    box.add(ui.Label('⚠ '+L.pre_title, {fontSize:'13px',fontWeight:'bold',color:'#cc8800',margin:'2px'}));
    box.add(ui.Label(L.pre_body, {fontSize:'11px',color:'#333',margin:'2px'}));
    box.add(ui.Label('FILTERED/'+fullName+'/'+currentPeriodKey, {fontSize:'11px',fontWeight:'bold',fontFamily:'monospace',color:'#1a73e8',margin:'2px','padding':'4px',backgroundColor:'#fff'}));
    box.add(ui.Label(L.pre_warn, {fontSize:'10px',color:'#888',margin:'4px 2px'}));
    var br = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:{stretch:'horizontal',margin:'4px 0 0 0'}});
    br.add(ui.Button({label:L.cancel, style:S.btn_gray, onClick:function(){buildConfirmSection(parentPanel);}}));
    br.add(ui.Button({label:L.pre_ok, style:S.btn_green, onClick:function(){executeExport(parentPanel);}}));
    box.add(br);
    parentPanel.add(box);
}

// ─── EXPORT ─────────────────────────────────────────────────────────────────

function executeExport(parentPanel) {
    parentPanel.clear();
    parentPanel.add(ui.Label(L.loading, {fontSize:'11px',color:'#1a73e8',margin:'4px'}));

    var fullName = collectionName + '-ft00';
    ensureFolder('FILTERED/'+fullName);

    var rns = Object.keys(regionModelMap).filter(function(r){return!!regionModelMap[r];});
    if(rns.length===0){parentPanel.add(ui.Label('Erro: nenhuma regiao.',S.status_err));return;}

    var nImg = ee.Image(0).rename('probability');
    var dImg = ee.Image(0).rename('dayOfYear');
    var mList = [];

    rns.forEach(function(rn){
        var mid=regionModelMap[rn]; mList.push(rn+':'+mid);
        var assets=availableModels[currentPeriodKey]&&availableModels[currentPeriodKey][rn];
        if(!assets)return;
        var found=null; for(var i=0;i<assets.length;i++){if(assets[i].modelId===mid){found=assets[i];break;}} if(!found)return;
        var rMask=ee.Image(0).paint(REGIONS.filter(ee.Filter.eq(REGION_PROPERTY,rn)),1);
        var src=ee.Image(found.assetId);
        nImg=nImg.where(rMask.eq(1),src.select(0));
        dImg=dImg.where(rMask.eq(1),src.select(1));
    });

    nImg=nImg.addBands(dImg).selfMask().set({'region_models':mList.join(','),'campaign':'MONITOR_01','filter_stage':'ft00','period':currentPeriodKey});

    var destPath=CLASSIFICATIONS_ROOT+'FILTERED/'+fullName;
    var destAsset=destPath+'/'+currentPeriodKey;

    Map.addLayer(nImg.select('probability').selfMask(),{min:0,max:1000,palette:['#ffcccc','#ff0000','#660000']},'National '+currentPeriodKey,false);

    try{ee.data.getAsset(destAsset);print('Ja existe: '+destAsset);}
    catch(e){print('Exportando: '+destAsset);Export.image.toAsset({image:nImg.toInt16(),description:currentPeriodKey.replace(/_/g,''),assetId:destAsset,pyramidingPolicy:'mode',region:REGIONS.geometry().bounds(),scale:SCALE,maxPixels:1e13});}

    parentPanel.clear();
    parentPanel.add(ui.Label(L.done,{fontSize:'12px',color:'#0f9d58',fontWeight:'bold',margin:'4px'}));
    parentPanel.add(ui.Label('FILTERED/'+fullName+'/'+currentPeriodKey,{fontSize:'10px',color:'#555',fontFamily:'monospace',margin:'2px'}));
}

// ─── INIT ───────────────────────────────────────────────────────────────────

buildForm();
print('M7_00 3.0 carregado.');
