/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M9_00
Pre-Public Promotion (UI)

📅 DATA: julho 2026
🏷️ VERSAO: 1.0

📌 O QUE FAZ:
1. Seleciona colecao de CANDIDATES/
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
        pt:{title:'M9 — Promover a PRE_PUBLIC',campaign:'Campanha',collection:'Colecao',candidates:'Candidatos',protocol:'Protocolo',promote:'Promover para PRE_PUBLIC',select_all:'Selecionar todos',clear:'Limpar',loading:'Carregando...',no_data:'Nenhum candidato encontrado.',done:'Promovido!',checklist_title:'Checklist',check_threshold:'✅ Area dentro do threshold',check_visual:'📍 Verificar visualmente',check_modis:'MODIS overlap',pre_title:'Confirmar Promocao',pre_body:'Serao copiados para PRE_PUBLIC/',pre_warn:'O GEE solicitara confirmacao.',cancel:'Cancelar',ok:'Confirmar',area_label:'ha',export_csv:'📊 Exportar CSV'},
        en:{title:'M9 — Promote to PRE_PUBLIC',campaign:'Campaign',collection:'Collection',candidates:'Candidates',protocol:'Protocol',promote:'Promote to PRE_PUBLIC',select_all:'Select all',clear:'Clear',loading:'Loading...',no_data:'No candidates found.',done:'Promoted!',checklist_title:'Checklist',check_threshold:'✅ Area within threshold',check_visual:'📍 Check visually',check_modis:'MODIS overlap',pre_title:'Confirm Promotion',pre_body:'Will copy to PRE_PUBLIC/',pre_warn:'GEE will prompt for confirmation.',cancel:'Cancel',ok:'Confirm',area_label:'ha',export_csv:'📊 Export CSV'},
        es:{title:'M9 — Promover a PRE_PUBLIC',campaign:'Campana',collection:'Coleccion',candidates:'Candidatos',protocol:'Protocolo',promote:'Promover a PRE_PUBLIC',select_all:'Todos',clear:'Limpiar',loading:'Cargando...',no_data:'Sin candidatos.',done:'Promovido!',checklist_title:'Checklist',check_threshold:'✅ Area dentro del umbral',check_visual:'📍 Verificar visualmente',check_modis:'MODIS overlap',pre_title:'Confirmar Promocion',pre_body:'Se copiara a PRE_PUBLIC/',pre_warn:'GEE solicitara confirmacion.',cancel:'Cancelar',ok:'Confirmar',area_label:'ha',export_csv:'📊 Exportar CSV'},
    };
    return d[APP_LANG]||d.pt;
})();

var STYLE = {
    card:{margin:'4px',padding:'8px',backgroundColor:'#f8f9fa',border:'1px solid #e0e0e0',borderRadius:'6px'},
    lbl:{fontSize:'11px',color:'#555',margin:'2px 0'},
    inp:{stretch:'horizontal',fontSize:'12px',margin:'2px 0'},
    btnGreen:{margin:'2px',padding:'4px 10px',color:'#0f9d58',fontWeight:'bold'},
    btnBlue:{margin:'2px',padding:'4px 10px',color:'#1a73e8',fontWeight:'bold'},
    btnGray:{margin:'2px',padding:'4px 10px',color:'#70757a',fontWeight:'bold'},
    ok:{color:'#0f9d58',fontWeight:'bold',fontSize:'11px'},
    err:{color:'#d32f2f',fontWeight:'bold',fontSize:'11px'},
    pre:{margin:'6px 0',padding:'10px',backgroundColor:'#fff8e1',border:'1px solid #ffcc00',borderRadius:'6px'},
    sectionTitle:{fontSize:'12px',fontWeight:'bold',color:'#333',margin:'0 0 6px 0'},
};

var selectedPeriods = {};
var candidateData = {};
var dropdownCollection;

function ensureFolder(name){
    var p=name.split('/'), cur=CLASSIFICATIONS_ROOT;
    for(var i=0;i<p.length;i++){cur+=p[i];try{ee.data.getAsset(cur)}catch(e){ee.data.createAsset({type:'IMAGE_COLLECTION'},cur)}cur+='/';}
}

// ─── FORM ───────────────────────────────────────────────────────────────────

function buildForm(){
    ui.root.clear();
    var root = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:{width:'580px',margin:'0',padding:'4px',backgroundColor:'#fff'}});
    root.add(ui.Label('MapBiomas-Fuego | '+L.title,{fontSize:'14px',fontWeight:'bold',color:'#d32f2f',margin:'4px'}));

    // Campaign + Collection
    var cfgSection = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:STYLE.card});
    cfgSection.add(ui.Label(L.campaign,STYLE.lbl));
    cfgSection.add(ui.Select({items:['MONITOR_01','MONITOR_DEV'],value:'MONITOR_01',style:STYLE.inp}));

    cfgSection.add(ui.Label(L.collection,STYLE.lbl));
    dropdownCollection = ui.Select({items:['...'],value:null,style:STYLE.inp,disabled:true});
    cfgSection.add(dropdownCollection);
    root.add(cfgSection);

    // Candidates listing
    var candidatesSection = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:STYLE.card});
    candidatesSection.add(ui.Label(L.candidates,STYLE.sectionTitle));
    var candidatesBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    candidatesSection.add(candidatesBox);
    root.add(candidatesSection);

    // Protocol
    var protocolSection = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:STYLE.card});
    protocolSection.add(ui.Label(L.protocol,STYLE.sectionTitle));
    var protocolBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    protocolSection.add(protocolBox);
    root.add(protocolSection);

    // Actions
    var actionsRow = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'4px 0'}});
    var btnCsv = ui.Button({label:L.export_csv,style:STYLE.btnBlue,onClick:function(){exportCsv();}});
    var btnPromote = ui.Button({label:L.promote,style:STYLE.btnGreen,onClick:function(){showPrePopup(protocolBox);}});
    actionsRow.add(btnCsv).add(btnPromote);
    root.add(actionsRow);

    ui.root.add(root);
    Map.setOptions('SATELLITE');
    Map.centerObject(REGIONS);

    loadCandidateCollections();
    dropdownCollection.onChange(function(v){
        if(!v||v==='...')return;
        loadCandidates(v,candidatesBox,protocolBox);
    });
}

// ─── LOAD CANDIDATE COLLECTIONS ─────────────────────────────────────────────

function loadCandidateCollections(){
    var path = CLASSIFICATIONS_ROOT+'CANDIDATES/';
    ensureFolder('CANDIDATES');
    ee.data.listAssets(path,{},function(r){
        var names=[];
        if(r&&r.assets)names=r.assets.filter(function(a){return a.type==='IMAGE_COLLECTION'}).map(function(a){return a.id.split('/').pop()}).sort();
        if(names.length===0){dropdownCollection.items().reset(['(nenhum candidato)']);dropdownCollection.setDisabled(true);}
        else{dropdownCollection.items().reset(names);dropdownCollection.setDisabled(false);dropdownCollection.setValue(names[0]);}
    });
}

// ─── LOAD CANDIDATES ────────────────────────────────────────────────────────

function loadCandidates(collectionName,candidatesBox,protocolBox){
    candidatesBox.clear();
    candidatesBox.add(ui.Label(L.loading,{fontSize:'10px',color:'#888'}));
    selectedPeriods = {};

    var path = CLASSIFICATIONS_ROOT+'CANDIDATES/'+collectionName+'/';
    ee.data.listAssets(path,{},function(r){
        candidateData = {};
        var periods=[];
        if(r&&r.assets)r.assets.forEach(function(a){
            if(a.type==='IMAGE'){
                var img = ee.Image(a.id);
                var period = a.id.split('/').pop();
                var areaHa = img.get('burned_area_ha')||'?';
                candidateData[period] = {assetId:a.id,areaHa:areaHa};
                periods.push(period);
            }
        });
        periods.sort().reverse();

        candidatesBox.clear();
        if(periods.length===0){
            candidatesBox.add(ui.Label(L.no_data,{color:'#d32f2f',margin:'4px'}));
            return;
        }

        var header = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'0 0 4px 0'}});
        header.add(ui.Button({label:L.select_all,style:STYLE.btnBlue,onClick:function(){
            periods.forEach(function(p){selectedPeriods[p]=true;});
            loadCandidates(collectionName,candidatesBox,protocolBox);
        }}));
        header.add(ui.Button({label:L.clear,style:STYLE.btnGray,onClick:function(){
            selectedPeriods={};
            loadCandidates(collectionName,candidatesBox,protocolBox);
        }}));
        candidatesBox.add(header);

        periods.forEach(function(p){
            var checked = selectedPeriods[p]||false;
            var cb = ui.Checkbox({label:p+' — '+candidateData[p].areaHa+' '+L.area_label,value:checked,style:{fontSize:'10px',margin:'1px 2px'}});
            cb.onChange(function(v){selectedPeriods[p]=v;});
            candidatesBox.add(cb);
        });

        var selCount = periods.filter(function(p){return selectedPeriods[p];}).length;
        candidatesBox.add(ui.Label('Selecionados: '+selCount+'/'+periods.length,{fontSize:'10px',color:'#888',margin:'4px 0'}));

        // Protocol
        protocolBox.clear();
        protocolBox.add(ui.Label(L.check_threshold,STYLE.ok));
        protocolBox.add(ui.Label(L.check_visual,{fontSize:'11px',color:'#e37400',margin:'1px 0'}));
    });
}

// ─── EXPORT CSV ─────────────────────────────────────────────────────────────

function exportCsv(){
    var path = CLASSIFICATIONS_ROOT+'CANDIDATES/';
    ee.data.listAssets(path,{},function(cols){
        var csv=['collection,period,area_ha'];
        var pending=0;
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

function showPrePopup(protocolBox){
    protocolBox.clear();
    var sel = Object.keys(selectedPeriods).filter(function(p){return selectedPeriods[p];});
    if(sel.length===0){protocolBox.add(ui.Label('Nenhum selecionado.',STYLE.err));return;}

    var box = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:STYLE.pre});
    box.add(ui.Label('⚠ '+L.pre_title,{fontSize:'13px',fontWeight:'bold',color:'#cc8800',margin:'2px'}));
    box.add(ui.Label(L.pre_body,{fontSize:'11px',color:'#333',margin:'2px'}));
    sel.forEach(function(p){
        box.add(ui.Label('  '+p,{fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'1px'}));
    });
    box.add(ui.Label(L.pre_warn,{fontSize:'10px',color:'#888',margin:'4px 2px'}));
    var br = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'4px 0 0 0'}});
    br.add(ui.Button({label:L.cancel,style:STYLE.btnGray}));
    br.add(ui.Button({label:L.ok,style:STYLE.btnGreen,onClick:function(){doPromote(sel,protocolBox);}}));
    box.add(br);
    protocolBox.add(box);
}

// ─── PROMOTE ────────────────────────────────────────────────────────────────

function doPromote(periods,protocolBox){
    protocolBox.clear();
    protocolBox.add(ui.Label(L.loading,{fontSize:'11px',color:'#1a73e8',margin:'4px'}));

    var colName = dropdownCollection.getValue();
    var campaign = 'monitor_01';
    var prePublicPath = CLASSIFICATIONS_ROOT+'PRE_PUBLIC/'+campaign+'/';
    ensureFolder('PRE_PUBLIC/'+campaign);

    var total = 0;
    periods.forEach(function(p){
        var src = CLASSIFICATIONS_ROOT+'CANDIDATES/'+colName+'/'+p;
        var dest = prePublicPath+p;

        try{ee.data.getAsset(dest);print('Ja existe: '+dest);}
        catch(e){
            total++;
            print('Copiando: '+src+' -> '+dest);
            ee.data.copyAsset(src,dest);
        }
    });

    protocolBox.clear();
    protocolBox.add(ui.Label(L.done+' ('+total+' periodos)',{fontSize:'12px',color:'#0f9d58',fontWeight:'bold',margin:'4px'}));
    protocolBox.add(ui.Label('Destino: PRE_PUBLIC/'+campaign+'/',{fontSize:'10px',color:'#555',fontFamily:'monospace',margin:'2px'}));
}

// ─── INIT ───────────────────────────────────────────────────────────────────

buildForm();
print('M9_00 1.0 carregado.');
