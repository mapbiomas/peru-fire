/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M9_00
Pre-Public Promotion (UI) — Formulario Corrido

📅 DATA: julho 2026
🏷️ VERSAO: 2.0

📌 SEÇÕES COM FUNDO COLORIDO:
  CONFIG — cinza   |   CANDIDATOS — azul claro
  PROTOCOLO — cinza  |   PROMOVER — verde claro

📌 O QUE FAZ:
1. Seleciona campanha + colecao de CANDIDATES/
2. Lista periodos candidatos com area queimada
3. Protocolo de avaliacao simples
4. Promove para PRE_PUBLIC via ee.data.copyAsset
********************************************/

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var SCALE = 10;
var APP_LANG = 'pt';

var L = (function(){
    var d={
        pt:{title:'M9 — Promover a PRE_PUBLIC',cfg:'CONFIGURACAO',candidates:'CANDIDATOS',protocol:'PROTOCOLO',promote:'PROMOVER',campaign:'Campanha',collection:'Colecao',existing_pre:'Ja promovidos',empty_pre:'(vazio)',select_all:'Selecionar todos',clear:'Limpar',filter_placeholder:'filtrar periodos...',loading:'Carregando...',no_data:'Nenhum candidato encontrado.',done:'Promovido!',check_threshold:'✅ Area dentro do threshold',check_visual:'📍 Verificar visualmente',check_modis:'🔎 MODIS overlap',pre_title:'Confirmar Promocao',pre_body:'Serao copiados para PRE_PUBLIC/',pre_warn:'O GEE solicitara confirmacao.',cancel:'Cancelar',ok:'Confirmar',area_label:'ha',export_csv:'📊 Exportar CSV',promote_btn:'Promover para PRE_PUBLIC',target:'Destino',none_selected:'Nenhum selecionado.',selected:'Selecionados',no_collection:'(nenhuma colecao)'},
        es:{title:'M9 — Promover a PRE_PUBLIC',cfg:'CONFIG',candidates:'CANDIDATOS',protocol:'PROTOCOLO',promote:'PROMOVER',campaign:'Campana',collection:'Coleccion',existing_pre:'Ya promovidos',empty_pre:'(vacio)',select_all:'Todos',clear:'Limpiar',filter_placeholder:'filtrar periodos...',loading:'Cargando...',no_data:'Sin candidatos.',done:'Promovido!',check_threshold:'✅ Area dentro del umbral',check_visual:'📍 Verificar visualmente',check_modis:'🔎 MODIS overlap',pre_title:'Confirmar Promocion',pre_body:'Se copiara a PRE_PUBLIC/',pre_warn:'GEE solicitara confirmacion.',cancel:'Cancelar',ok:'Confirmar',area_label:'ha',export_csv:'📊 Exportar CSV',promote_btn:'Promover a PRE_PUBLIC',target:'Destino',none_selected:'Ninguno seleccionado.',selected:'Seleccionados',no_collection:'(ninguna coleccion)'},
        en:{title:'M9 — Promote to PRE_PUBLIC',cfg:'CONFIGURATION',candidates:'CANDIDATES',protocol:'PROTOCOL',promote:'PROMOTE',campaign:'Campaign',collection:'Collection',existing_pre:'Already promoted',empty_pre:'(empty)',select_all:'Select all',clear:'Clear',filter_placeholder:'filter periods...',loading:'Loading...',no_data:'No candidates found.',done:'Promoted!',check_threshold:'✅ Area within threshold',check_visual:'📍 Check visually',check_modis:'🔎 MODIS overlap',pre_title:'Confirm Promotion',pre_body:'Will copy to PRE_PUBLIC/',pre_warn:'GEE will prompt for confirmation.',cancel:'Cancel',ok:'Confirm',area_label:'ha',export_csv:'📊 Export CSV',promote_btn:'Promote to PRE_PUBLIC',target:'Destination',none_selected:'None selected.',selected:'Selected',no_collection:'(no collection)'},
        fr:{title:'M9 — Promouvoir vers PRE_PUBLIC',cfg:'CONFIG',candidates:'CANDIDATS',protocol:'PROTOCOLE',promote:'PROMOUVOIR',campaign:'Campagne',collection:'Collection',existing_pre:'Deja promus',empty_pre:'(vide)',select_all:'Tout',clear:'Effacer',filter_placeholder:'filtrer periodes...',loading:'Chargement...',no_data:'Aucun candidat.',done:'Promu!',check_threshold:'✅ Zone dans le seuil',check_visual:'📍 Verifier visuellement',check_modis:'🔎 MODIS overlap',pre_title:'Confirmer la Promotion',pre_body:'Va copier vers PRE_PUBLIC/',pre_warn:'GEE demandera confirmation.',cancel:'Annuler',ok:'Confirmer',area_label:'ha',export_csv:'📊 Exporter CSV',promote_btn:'Promouvoir vers PRE_PUBLIC',target:'Destination',none_selected:'Aucun selectionne.',selected:'Selectionnes',no_collection:'(aucune collection)'},
        id:{title:'M9 — Promosikan ke PRE_PUBLIC',cfg:'KONFIG',candidates:'KANDIDAT',protocol:'PROTOKOL',promote:'PROMOSI',campaign:'Kampanye',collection:'Koleksi',existing_pre:'Sudah dipromosikan',empty_pre:'(kosong)',select_all:'Semua',clear:'Hapus',filter_placeholder:'filter periode...',loading:'Memuat...',no_data:'Tidak ada kandidat.',done:'Terpromosi!',check_threshold:'✅ Area dalam ambang',check_visual:'📍 Periksa visual',check_modis:'🔎 MODIS overlap',pre_title:'Konfirmasi Promosi',pre_body:'Akan disalin ke PRE_PUBLIC/',pre_warn:'GEE akan minta konfirmasi.',cancel:'Batal',ok:'Konfirmasi',area_label:'ha',export_csv:'📊 Ekspor CSV',promote_btn:'Promosikan ke PRE_PUBLIC',target:'Tujuan',none_selected:'Tidak ada yang dipilih.',selected:'Terpilih',no_collection:'(tanpa koleksi)'},
    };
    return d[APP_LANG]||d.pt;
})();

var SECTION_STYLE = {
    config:     { margin:'4px', padding:'8px', backgroundColor:'#f8f9fa', border:'1px solid #e0e0e0', borderRadius:'6px' },
    candidates: { margin:'4px', padding:'8px', backgroundColor:'#f0f4ff', border:'1px solid #c8d6f0', borderRadius:'6px' },
    protocol:   { margin:'4px', padding:'8px', backgroundColor:'#f8f9fa', border:'1px solid #e0e0e0', borderRadius:'6px' },
    promote:    { margin:'4px', padding:'8px', backgroundColor:'#e8f5e9', border:'1px solid #b8d8ba', borderRadius:'6px' },
};

var STYLE = {
    label:        { fontSize:'11px', color:'#555', margin:'2px 0' },
    input:        { stretch:'horizontal', fontSize:'12px', margin:'2px 0' },
    btnBlue:      { margin:'2px', padding:'4px 10px', color:'#1a73e8', fontWeight:'bold' },
    btnGreen:     { margin:'2px', padding:'4px 10px', color:'#0f9d58', fontWeight:'bold' },
    btnGray:      { margin:'2px', padding:'4px 10px', color:'#70757a', fontWeight:'bold' },
    statusOk:     { color:'#0f9d58', fontWeight:'bold', fontSize:'11px' },
    statusErr:    { color:'#d32f2f', fontWeight:'bold', fontSize:'11px' },
    prePopup:     { margin:'6px 0', padding:'10px', backgroundColor:'#fff8e1', border:'1px solid #ffcc00', borderRadius:'6px' },
    sectionTitle: { fontSize:'12px', fontWeight:'bold', color:'#333', margin:'0 0 6px 0' },
    card:         { margin:'2px', padding:'4px', backgroundColor:'#fff', border:'1px solid #e0e0e0', borderRadius:'4px' },
    summaryCard:  { margin:'0 0 6px 0', padding:'6px', backgroundColor:'#fff', border:'1px solid #e0e0e0', borderRadius:'4px' },
    contentsCard: { margin:'0 0 6px 0', padding:'6px', backgroundColor:'#fff', border:'1px solid #c8d6f0', borderRadius:'4px' },
    checkbox:     { fontSize:'10px', margin:'1px 2px' },
};

// ─── APPLICATION STATE ──────────────────────────────────────────────────────

var selectedPeriods = {};
var candidateData = {};
var candidatePeriods = [];
var filterText = '';
var dropdownCollection, dropdownCampaign, candidatesBox, protocolBox, promoteBox, contentsBox, statusLabel, exportStatus;

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function ensureFolder(name){
    var p=name.split('/'), cur=CLASSIFICATIONS_ROOT;
    for(var i=0;i<p.length;i++){cur+=p[i];try{ee.data.getAsset(cur)}catch(e){ee.data.createAsset({type:'IMAGE_COLLECTION'},cur)}cur+='/';}
}

function campaignSlug(){var v=dropdownCampaign?dropdownCampaign.getValue():'MONITOR_01';return (v||'MONITOR_01').toLowerCase();}

function prePublicPath(){return CLASSIFICATIONS_ROOT+'PRE_PUBLIC/'+campaignSlug()+'/';}

function showLoading(){if(statusLabel)statusLabel.style().set('shown',true);}
function hideLoading(){if(statusLabel)statusLabel.style().set('shown',false);}

function setExportStatus(state, msg){
    if(!exportStatus)return;
    var colors={loading:{bg:'#fff8e1',icon:'⏳'},success:{bg:'#e8f5e9',icon:'✅'},error:{bg:'#ffeaea',icon:'❌'},info:{bg:'#f0f4ff',icon:'ℹ️'}};
    var c=colors[state]||colors.info;
    exportStatus.style().set('shown',true);
    exportStatus.clear();
    exportStatus.add(ui.Label(c.icon+' '+msg,{fontSize:'11px',padding:'4px 8px',backgroundColor:c.bg,borderRadius:'3px',margin:'2px 0',stretch:'horizontal'}));
}

// ─── LOAD CANDIDATE COLLECTIONS ─────────────────────────────────────────────

function loadCandidateCollections(){
    var path = CLASSIFICATIONS_ROOT+'CANDIDATES/';
    ensureFolder('CANDIDATES');
    ee.data.listAssets(path,{},function(r){
        var names=[];
        if(r&&r.assets)names=r.assets.filter(function(a){return a.type==='IMAGE_COLLECTION'}).map(function(a){return a.id.split('/').pop()}).sort();
        if(names.length===0){dropdownCollection.items().reset([L.no_collection]);dropdownCollection.setDisabled(true);}
        else{dropdownCollection.items().reset(names);dropdownCollection.setDisabled(false);dropdownCollection.setValue(names[0]);loadCandidates(names[0]);}
    });
}

// ─── PRE_PUBLIC CONTENTS ─────────────────────────────────────────────────────

function loadPrePublicContents(){
    if(!contentsBox)return;
    contentsBox.clear();
    var path = prePublicPath();
    ensureFolder('PRE_PUBLIC/'+campaignSlug());

    ee.data.listAssets(path,{},function(r){
        var periods=[];
        if(r&&r.assets)periods=r.assets.filter(function(a){return a.type==='IMAGE'}).map(function(a){return a.id.split('/').pop()}).sort().reverse();

        var card = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:STYLE.contentsCard});
        card.add(ui.Label(L.existing_pre+': PRE_PUBLIC/'+campaignSlug(), {fontSize:'10px',fontWeight:'bold',color:'#1a73e8',margin:'0 0 4px 0'}));

        if(periods.length===0){
            card.add(ui.Label(L.empty_pre, {fontSize:'10px',color:'#aaa',margin:'2px'}));
        } else {
            var list = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:{maxHeight:'100px'}});
            periods.forEach(function(p){list.add(ui.Label(' '+p+'  ✅', {fontSize:'10px',fontFamily:'monospace',color:'#0f9d58',margin:'1px 0'}));});
            card.add(list);
            card.add(ui.Label('Total: '+periods.length, {fontSize:'10px',color:'#888',margin:'2px 0 0 0'}));
        }
        contentsBox.add(card);
    });
}

// ─── LOAD CANDIDATES ────────────────────────────────────────────────────────

function loadCandidates(collectionName){
    candidatesBox.clear();
    candidatesBox.add(ui.Label(L.loading,{fontSize:'10px',color:'#888'}));
    selectedPeriods = {};
    filterText = '';

    var path = CLASSIFICATIONS_ROOT+'CANDIDATES/'+collectionName+'/';
    ee.data.listAssets(path,{},function(r){
        candidateData = {};
        candidatePeriods = [];
        if(r&&r.assets)r.assets.forEach(function(a){
            if(a.type==='IMAGE'){
                var period = a.id.split('/').pop();
                var img = ee.Image(a.id);
                var areaHa = img.get('burned_area_ha')||'?';
                candidateData[period] = {assetId:a.id,areaHa:areaHa};
                candidatePeriods.push(period);
            }
        });
        candidatePeriods.sort().reverse();
        renderCandidates(collectionName);
        updatePromoteSummary();
        hideLoading();
    });
}

// ─── RENDER CANDIDATES ──────────────────────────────────────────────────────

function renderCandidates(collectionName){
    candidatesBox.clear();
    if(candidatePeriods.length===0){
        candidatesBox.add(ui.Label(L.no_data,{fontSize:'11px',color:'#d32f2f',margin:'4px'}));
        buildProtocolChecklist();
        return;
    }

    var headerRow = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:{stretch:'horizontal',margin:'0 0 4px 0'}});
    var txtFilter = ui.Textbox({placeholder:L.filter_placeholder, style:{stretch:'horizontal',fontSize:'10px'}});
    txtFilter.onChange(function(v){filterText=v.toLowerCase();renderCandidates(collectionName);});
    headerRow.add(txtFilter);
    headerRow.add(ui.Button({label:L.select_all, style:STYLE.btnBlue, onClick:function(){
        candidatePeriods.forEach(function(p){selectedPeriods[p]=true;});
        renderCandidates(collectionName);
    }}));
    headerRow.add(ui.Button({label:L.clear, style:STYLE.btnGray, onClick:function(){
        selectedPeriods={};
        renderCandidates(collectionName);
    }}));
    candidatesBox.add(headerRow);

    var shown = candidatePeriods.filter(function(p){return !filterText||p.toLowerCase().indexOf(filterText)!==-1;});
    var list = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    shown.forEach(function(p){
        var checked = selectedPeriods[p]||false;
        var cb = ui.Checkbox({label:p+' — '+candidateData[p].areaHa+' '+L.area_label, value:checked, style:STYLE.checkbox});
        cb.onChange(function(v){selectedPeriods[p]=v;updatePromoteSummary();});
        list.add(cb);
    });
    if(shown.length===0){
        list.add(ui.Label('('+candidatePeriods.length+' oculto'+(candidatePeriods.length>1?'s':'')+')', {fontSize:'9px',color:'#aaa',margin:'1px 0'}));
    }
    candidatesBox.add(list);

    var selCount = candidatePeriods.filter(function(p){return selectedPeriods[p];}).length;
    candidatesBox.add(ui.Label(L.selected+': '+selCount+'/'+candidatePeriods.length,{fontSize:'10px',color:'#888',margin:'4px 0'}));

    buildProtocolChecklist();
}

function updatePromoteSummary(){
    if(!promoteBox)return;
    var sel = Object.keys(selectedPeriods).filter(function(p){return selectedPeriods[p];});
    promoteBox.clear();
    promoteBox.add(ui.Label(L.target+': '+prePublicPath(), {fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'2px',padding:'4px',backgroundColor:'#fff',borderRadius:'3px'}));
    promoteBox.add(ui.Label(L.selected+': '+sel.length+' periodo'+(sel.length===1?'':'s'), sel.length>0?STYLE.statusOk:STYLE.statusErr));
}

// ─── PROTOCOL ───────────────────────────────────────────────────────────────

function buildProtocolChecklist(){
    if(!protocolBox)return;
    protocolBox.clear();
    protocolBox.add(ui.Label(L.check_threshold,STYLE.statusOk));
    protocolBox.add(ui.Label(L.check_visual,{fontSize:'11px',color:'#e37400',margin:'1px 0'}));
    protocolBox.add(ui.Label(L.check_modis,{fontSize:'11px',color:'#e37400',margin:'1px 0'}));
}

// ─── EXPORT CSV ─────────────────────────────────────────────────────────────

function exportCsv(){
    var path = CLASSIFICATIONS_ROOT+'CANDIDATES/';
    ee.data.listAssets(path,{},function(cols){
        var csv=['collection,period,area_ha'];
        if(!cols||!cols.assets){print(csv.join('\n'));return}
        cols.assets.filter(function(c){return c.type==='IMAGE_COLLECTION'}).forEach(function(c){
            var colName=c.id.split('/').pop();
            ee.data.listAssets(c.id,{},function(imgs){
                if(imgs&&imgs.assets)imgs.assets.forEach(function(img){
                    if(img.type!=='IMAGE')return;
                    var period=img.id.split('/').pop();
                    var area=ee.Image(img.id).get('burned_area_ha').getInfo()||'?';
                    csv.push([colName,period,area].join(','));
                });
            });
        });
        setTimeout(function(){print('--- CSV Looker Studio ---');print(csv.join('\n'));},3000);
    });
}

// ─── PRE-POPUP ──────────────────────────────────────────────────────────────

function showPrePopup(){
    protocolBox.clear();
    var sel = Object.keys(selectedPeriods).filter(function(p){return selectedPeriods[p];});
    if(sel.length===0){protocolBox.add(ui.Label(L.none_selected,STYLE.statusErr));return;}

    var box = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:STYLE.prePopup});
    box.add(ui.Label('⚠ '+L.pre_title,{fontSize:'13px',fontWeight:'bold',color:'#cc8800',margin:'2px'}));
    box.add(ui.Label(L.pre_body,{fontSize:'11px',color:'#333',margin:'2px'}));
    box.add(ui.Label(prePublicPath(), {fontSize:'11px',fontWeight:'bold',fontFamily:'monospace',color:'#1a73e8',margin:'2px',padding:'4px',backgroundColor:'#fff'}));
    sel.forEach(function(p){
        box.add(ui.Label('  '+p,{fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'1px'}));
    });
    box.add(ui.Label(L.pre_warn,{fontSize:'10px',color:'#888',margin:'4px 2px'}));
    var br = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'4px 0 0 0'}});
    br.add(ui.Button({label:L.cancel,style:STYLE.btnGray,onClick:function(){buildProtocolChecklist();}}));
    br.add(ui.Button({label:L.ok,style:STYLE.btnGreen,onClick:function(){doPromote(sel);}}));
    box.add(br);
    protocolBox.add(box);
}

// ─── PROMOTE ────────────────────────────────────────────────────────────────

function doPromote(periods){
    protocolBox.clear();
    protocolBox.add(ui.Label(L.loading,{fontSize:'11px',color:'#1a73e8',margin:'4px'}));
    setExportStatus('loading','Promovendo '+periods.length+' periodo'+(periods.length===1?'':'s')+'...');
    showLoading();

    var colName = dropdownCollection.getValue();
    var destRoot = prePublicPath();
    ensureFolder('PRE_PUBLIC/'+campaignSlug());

    var total = 0;
    periods.forEach(function(p){
        var src = CLASSIFICATIONS_ROOT+'CANDIDATES/'+colName+'/'+p;
        var dest = destRoot+p;

        try{ee.data.getAsset(dest);setExportStatus('info','Ja existe: '+p);}
        catch(e){
            total++;
            print('Copiando: '+src+' -> '+dest);
            ee.data.copyAsset(src,dest);
        }
    });

    protocolBox.clear();
    protocolBox.add(ui.Label(L.done+' ('+total+' periodo'+(total===1?'':'s')+')',{fontSize:'12px',color:'#0f9d58',fontWeight:'bold',margin:'4px'}));
    protocolBox.add(ui.Label('Destino: '+destRoot,{fontSize:'10px',color:'#555',fontFamily:'monospace',margin:'2px'}));
    hideLoading();
    loadPrePublicContents();
}

// ─── SECTIONS ───────────────────────────────────────────────────────────────

function buildConfigSection(){
    var section = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:SECTION_STYLE.config});
    section.add(ui.Label(L.cfg, STYLE.sectionTitle));
    section.add(ui.Label(L.campaign, STYLE.label));
    dropdownCampaign = ui.Select({items:['MONITOR_01','MONITOR_DEV'], value:'MONITOR_01', style:STYLE.input});
    dropdownCampaign.onChange(function(){loadPrePublicContents();updatePromoteSummary();});
    section.add(dropdownCampaign);

    section.add(ui.Label(L.collection, STYLE.label));
    dropdownCollection = ui.Select({items:['...'], value:null, style:STYLE.input, disabled:true});
    dropdownCollection.onChange(function(v){
        if(!v||v===L.no_collection)return;
        loadCandidates(v);
    });
    section.add(dropdownCollection);
    return section;
}

function buildCandidatesSection(){
    var section = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:SECTION_STYLE.candidates});
    section.add(ui.Label(L.candidates, STYLE.sectionTitle));

    contentsBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    section.add(contentsBox);

    candidatesBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    section.add(candidatesBox);
    return section;
}

function buildProtocolSection(){
    var section = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:SECTION_STYLE.protocol});
    section.add(ui.Label(L.protocol, STYLE.sectionTitle));
    protocolBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    section.add(protocolBox);
    buildProtocolChecklist();
    return section;
}

function buildPromoteSection(){
    var section = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:SECTION_STYLE.promote});
    section.add(ui.Label(L.promote, STYLE.sectionTitle));

    promoteBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:STYLE.summaryCard});
    section.add(promoteBox);

    var actionsRow = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:{stretch:'horizontal',margin:'4px 0'}});
    actionsRow.add(ui.Button({label:L.export_csv, style:STYLE.btnBlue, onClick:function(){exportCsv();}}));
    actionsRow.add(ui.Button({label:L.promote_btn, style:STYLE.btnGreen, onClick:function(){showPrePopup();}}));
    section.add(actionsRow);
    return section;
}

// ─── FORM ───────────────────────────────────────────────────────────────────

function buildForm(){
    ui.root.clear();
    var root = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:{width:'580px',margin:'0',padding:'4px',backgroundColor:'#fff'}});
    root.add(ui.Label('MapBiomas-Fuego | '+L.title,{fontSize:'14px',fontWeight:'bold',color:'#d32f2f',margin:'4px'}));
    statusLabel = ui.Label({value:'', style:{fontSize:'10px',color:'#1a73e8',margin:'2px 4px',shown:false,stretch:'horizontal'}});
    root.add(statusLabel);

    root.add(buildConfigSection());
    root.add(buildCandidatesSection());
    root.add(buildProtocolSection());

    exportStatus = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:{margin:'4px',shown:false}});
    root.add(exportStatus);

    root.add(buildPromoteSection());

    ui.root.add(root);
    Map.setOptions('SATELLITE');
    Map.centerObject(REGIONS);

    loadPrePublicContents();
    loadCandidateCollections();
}

// ─── INIT ───────────────────────────────────────────────────────────────────

buildForm();
print('M9_00 2.0 carregado.');