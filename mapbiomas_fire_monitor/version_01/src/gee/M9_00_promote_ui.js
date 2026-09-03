/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M9_00
Pre-Public Promotion (UI) — Redesign v5.0

📅 DATA: setembro 2026
🏷️ VERSAO: 5.0

📌 SEÇÕES COM FUNDO COLORIDO:
  CONFIG — cinza   |   CANDIDATOS — azul claro
  PROTOCOLO — cinza  |   PROMOVER — verde claro

📌 O QUE FAZ:
1. CONFIG: pais (dropdown) + grid de datas (selecao unica,
   promovidas bloqueadas) + campanhas (checkbox multi)
2. Cada campanha ligada adiciona um grupo de grids com o seu
   proprio CLASSIFICATIONS_ROOT (CATALOG_01/{CAMPAIGN}/...)
3. Etapas ftXX descobertas automaticamente (subpastas FOLDER
   de FILTERED/{propuesta}/ que casam /^ft\d\d$/)
4. Cada grid: colunas = propuestas, 1 linha = data selecionada
   (global). Celula = checkbox de promocao (selecao unica por linha)
5. Datas ja promovidas por campanha: linha de status com checkbox
   (Ver no mapa) + botao Despromover (age nas marcadas)
6. Protocolo: checklist obligatorio que libera la promocion
7. Promueve a PRE_PUBLIC via ee.data.copyAsset

📌 SIN CREACION AUTOMATICA DE ASSETS:
  Ningun ee.data.createAsset se dispara al inicializar.
  Area quemada NO se calcula aqui (papel del M8).
********************************************/

// ⚙️ CONFIGURACION DEL USUARIO
var COUNTRY = 'peru';    // peru | chile | bolivia | colombia | paraguay | guyana
var CAMPAIGNS = ['MONITOR_01', 'MONITOR_DEV'];   // campanhas disponiveis

var COUNTRIES = {
    chile:    { catalog: 'projects/mapbiomas-chile/assets/FIRE/CATALOG_01',    regions: 'projects/mapbiomas-chile/assets/FIRE/AUXILIARY_DATA/regiones_fuego_chile_v1' },
    peru:     { catalog: 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01',     regions: 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1' },
    bolivia:  { catalog: 'projects/mapbiomas-bolivia/assets/FIRE/CATALOG_01',  regions: 'projects/mapbiomas-bolivia/assets/FIRE/AUXILIARY_DATA/regiones_fuego_bolivia_v1' },
    colombia: { catalog: 'projects/mapbiomas-colombia/assets/FIRE/CATALOG_01', regions: 'projects/mapbiomas-colombia/assets/FIRE/AUXILIARY_DATA/regiones_fuego_colombia_v1' },
    paraguay: { catalog: 'projects/mapbiomas-paraguay/assets/FIRE/CATALOG_01', regions: 'projects/mapbiomas-paraguay/assets/FIRE/AUXILIARY_DATA/regiones_fuego_paraguay_v1' },
    guyana:   { catalog: 'projects/mapbiomas-guyana/assets/FIRE/CATALOG_01',   regions: 'projects/mapbiomas-guyana/assets/FIRE/AUXILIARY_DATA/regiones_fuego_guyana_v1' }
};

var COUNTRY_CFG = COUNTRIES[COUNTRY] || COUNTRIES.peru;
var CATALOG_ROOT = COUNTRY_CFG.catalog;
var REGIONS = ee.FeatureCollection(COUNTRY_CFG.regions);
var SCALE = 10;
var APP_LANG = 'es';

// 🔗 Looker Studio — estadisticas de area quemada (M8)
var STATS_URL = 'https://datastudio.google.com/reporting/cc275c3b-4a5e-4b4c-97af-50191eca7698';

var L = (function(){
    var d={
        pt:{title:'M9 — Promover a PRE_PUBLIC',cfg:'CONFIGURACAO',candidates:'CANDIDATOS',protocol:'PROTOCOLO',promote:'PROMOVER',country:'Pais',date:'Datas',campaign:'Campanha',proposal:'Proposta',existing_pre:'Ja promovidos',empty_pre:'(vazio)',loading:'Carregando...',no_data:'Nenhum candidato encontrado.',done:'Promovido!',check_visual:'📍 Verificar a cicatriz no mapa',check_mosaic:'🛰️ Comparar com o mosaico Sentinel-2',check_area:'📊 Area conferida (estatisticas M8)',stats_link:'📊 Ver estatisticas (Looker Studio)',protocol_hint:'Marque os 3 itens para liberar a promocao.',pre_title:'Confirmar Promocao',pre_body:'Serao copiados para PRE_PUBLIC/',pre_warn:'A pasta PRE_PUBLIC/{campanha} sera criada se necessario.',cancel:'Cancelar',ok:'Confirmar',promote_btn:'Promover para PRE_PUBLIC',target:'Destino',none_selected:'Nenhum selecionado.',selected:'Selecionados',view:'Ver',unpromote:'Despromover',unpromote_confirm:'Despromover as imagens marcadas?',unpromote_done:'Despromovido!',promoted:'Promovido'},
        es:{title:'M9 — Promover a PRE_PUBLIC',cfg:'CONFIG',candidates:'CANDIDATOS',protocol:'PROTOCOLO',promote:'PROMOVER',country:'Pais',date:'Fechas',campaign:'Campana',proposal:'Propuesta',existing_pre:'Ya promovidos',empty_pre:'(vacio)',loading:'Cargando...',no_data:'Sin candidatos.',done:'¡Promovido!',check_visual:'📍 Verificar la cicatriz en el mapa',check_mosaic:'🛰️ Comparar con el mosaico Sentinel-2',check_area:'📊 Area verificada (estadisticas M8)',stats_link:'📊 Ver estadisticas (Looker Studio)',protocol_hint:'Marque los 3 items para habilitar la promocion.',pre_title:'Confirmar Promocion',pre_body:'Se copiara a PRE_PUBLIC/',pre_warn:'La carpeta PRE_PUBLIC/{campana} se creara si es necesario.',cancel:'Cancelar',ok:'Confirmar',promote_btn:'Promover a PRE_PUBLIC',target:'Destino',none_selected:'Ninguno seleccionado.',selected:'Seleccionados',view:'Ver',unpromote:'Despromover',unpromote_confirm:'¿Despromover las imagenes marcadas?',unpromote_done:'¡Despromovido!',promoted:'Promovido'},
        en:{title:'M9 — Promote to PRE_PUBLIC',cfg:'CONFIGURATION',candidates:'CANDIDATES',protocol:'PROTOCOL',promote:'PROMOTE',country:'Country',date:'Dates',campaign:'Campaign',proposal:'Proposal',existing_pre:'Already promoted',empty_pre:'(empty)',loading:'Loading...',no_data:'No candidates found.',done:'Promoted!',check_visual:'📍 Verify the scar on the map',check_mosaic:'🛰️ Compare with Sentinel-2 mosaic',check_area:'📊 Area verified (M8 stats)',stats_link:'📊 View statistics (Looker Studio)',protocol_hint:'Check the 3 items to enable promotion.',pre_title:'Confirm Promotion',pre_body:'Will copy to PRE_PUBLIC/',pre_warn:'The PRE_PUBLIC/{campaign} folder will be created if needed.',cancel:'Cancel',ok:'Confirm',promote_btn:'Promote to PRE_PUBLIC',target:'Destination',none_selected:'None selected.',selected:'Selected',view:'View',unpromote:'Unpromote',unpromote_confirm:'Unpromote the checked images?',unpromote_done:'Unpromoted!',promoted:'Promoted'},
        fr:{title:'M9 — Promouvoir vers PRE_PUBLIC',cfg:'CONFIG',candidates:'CANDIDATS',protocol:'PROTOCOLE',promote:'PROMOUVOIR',country:'Pays',date:'Dates',campaign:'Campagne',proposal:'Proposition',existing_pre:'Deja promus',empty_pre:'(vide)',loading:'Chargement...',no_data:'Aucun candidat.',done:'Promu!',check_visual:'📍 Verifier la cicatrice sur la carte',check_mosaic:'🛰️ Comparer avec le mosaique Sentinel-2',check_area:'📊 Zone verifiee (stats M8)',stats_link:'📊 Voir les statistiques (Looker Studio)',protocol_hint:'Cochez les 3 items pour activer la promotion.',pre_title:'Confirmer la Promotion',pre_body:'Va copier vers PRE_PUBLIC/',pre_warn:'Le dossier PRE_PUBLIC/{campagne} sera cree si necessaire.',cancel:'Annuler',ok:'Confirmer',promote_btn:'Promouvoir vers PRE_PUBLIC',target:'Destination',none_selected:'Aucun selectionne.',selected:'Selectionnes',view:'Voir',unpromote:'Depromouvoir',unpromote_confirm:'Depromouvoir les images cochees ?',unpromote_done:'Depromu !',promoted:'Promu'},
        id:{title:'M9 — Promosikan ke PRE_PUBLIC',cfg:'KONFIG',candidates:'KANDIDAT',protocol:'PROTOKOL',promote:'PROMOSI',country:'Negara',date:'Tanggal',campaign:'Kampanye',proposal:'Proposal',existing_pre:'Sudah dipromosikan',empty_pre:'(kosong)',loading:'Memuat...',no_data:'Tidak ada kandidat.',done:'Terpromosi!',check_visual:'📍 Periksa bekas luka di peta',check_mosaic:'🛰️ Bandingkan dengan mosaik Sentinel-2',check_area:'📊 Luas diverifikasi (statistik M8)',stats_link:'📊 Lihat statistik (Looker Studio)',protocol_hint:'Centang 3 item untuk mengaktifkan promosi.',pre_title:'Konfirmasi Promosi',pre_body:'Akan disalin ke PRE_PUBLIC/',pre_warn:'Folder PRE_PUBLIC/{kampanye} akan dibuat jika perlu.',cancel:'Batal',ok:'Konfirmasi',promote_btn:'Promosikan ke PRE_PUBLIC',target:'Tujuan',none_selected:'Tidak ada yang dipilih.',selected:'Terpilih',view:'Lihat',unpromote:'Batalkan promosi',unpromote_confirm:'Batalkan promosi gambar yang dicentang?',unpromote_done:'Promosi dibatalkan!',promoted:'Dipromosikan'},
    };
    return d[APP_LANG]||d.es;
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
    btnRed:       { margin:'2px', padding:'4px 10px', color:'#d32f2f', fontWeight:'bold' },
    statusOk:     { color:'#0f9d58', fontWeight:'bold', fontSize:'11px' },
    statusErr:    { color:'#d32f2f', fontWeight:'bold', fontSize:'11px' },
    prePopup:     { margin:'6px 0', padding:'10px', backgroundColor:'#fff8e1', border:'1px solid #ffcc00', borderRadius:'6px' },
    sectionTitle: { fontSize:'12px', fontWeight:'bold', color:'#333', margin:'0 0 6px 0' },
    card:         { margin:'2px', padding:'4px', backgroundColor:'#fff', border:'1px solid #e0e0e0', borderRadius:'4px' },
    summaryCard:  { margin:'0 0 6px 0', padding:'6px', backgroundColor:'#fff', border:'1px solid #e0e0e0', borderRadius:'4px' },
    contentsCard: { margin:'0 0 6px 0', padding:'6px', backgroundColor:'#fff', border:'1px solid #c8d6f0', borderRadius:'4px' },
    gridHeader:   { fontSize:'10px', fontWeight:'bold', color:'#1a73e8', margin:'1px 3px' },
    gridCell:     { fontSize:'10px', margin:'1px 2px' },
    gridDate:     { fontSize:'10px', fontFamily:'monospace', color:'#333', margin:'2px 4px', width:'64px' },
    gridHead:     { fontSize:'10px', fontWeight:'bold', color:'#1a73e8', margin:'2px 4px' },
};

// ─── APPLICATION STATE ──────────────────────────────────────────────────────

var selectedCells = {};          // key: campanha__etapa__propuesta__fecha
var promotedChecks = {};         // key: campanha__fecha -> bool (marcadas para Ver/Despromover)
var campaignData = {};           // { CAMPAIGN: { proposals, stages, stageData, promoted } }
var enabledCampaigns = {};       // { CAMPAIGN: bool }
var allDates = [];               // uniao de datas (disponiveis + promovidas)
var selectedDate = null;         // data global selecionada no grid de datas
var protocolChecked = {visual:false, mosaic:false, area:false};
var cellCheckboxes = {};         // key -> ui.Checkbox (radio por linea)
var dateCheckboxes = {};         // fecha -> ui.Checkbox
var mapLayers = {};
var mapWidget = ui.Map();
var dropdownCountry, dateBox, campaignBox, candidatesBox, protocolBox, promoteBox, contentsBox, statusLabel, exportStatus, promoteButton;

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function classificationsRoot(camp){return CATALOG_ROOT+'/'+camp+'/LIBRARY_CLASSIFICATIONS/';}

function prePublicPath(camp){return classificationsRoot(camp)+'PRE_PUBLIC/'+camp.toLowerCase()+'/';}

function cellKey(camp, stage, proposal, period){return camp+'__'+stage+'__'+proposal+'__'+period;}

function promotedKey(camp, period){return camp+'__'+period;}

function isDatePromotedGlobal(date){
    return Object.keys(enabledCampaigns).some(function(c){
        return enabledCampaigns[c] && campaignData[c] && campaignData[c].promoted[date];
    });
}

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

// ─── COUNTRY ────────────────────────────────────────────────────────────────

function setCountry(c){
    COUNTRY = c;
    COUNTRY_CFG = COUNTRIES[c]||COUNTRIES.peru;
    CATALOG_ROOT = COUNTRY_CFG.catalog;
    REGIONS = ee.FeatureCollection(COUNTRY_CFG.regions);
    removeMapLayer('regions_boundary');
    manageMapLayer('regions_boundary', REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}), {}, 'Regiones');
    mapWidget.centerObject(REGIONS);
    selectedDate = null;
    loadAll();
}

// ─── MAP LAYERS ─────────────────────────────────────────────────────────────

function manageMapLayer(id, obj, vis, name){
    if(mapLayers[id]){
        mapLayers[id].setEeObject(obj);
        mapLayers[id].setVisParams(vis);
        mapLayers[id].setName(name);
    } else {
        mapLayers[id] = ui.Map.Layer(obj, vis, name);
        mapWidget.layers().add(mapLayers[id]);
    }
}

function removeMapLayer(id){
    if(mapLayers[id]){mapWidget.layers().remove(mapLayers[id]);delete mapLayers[id];}
}

function clearCandidateLayers(){
    Object.keys(mapLayers).forEach(function(k){
        if(k.indexOf('cand_')===0||k.indexOf('mosaic_')===0||k.indexOf('promoted_')===0)removeMapLayer(k);
    });
}

function loadMosaic(period){
    var bs = CATALOG_ROOT+'/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR';
    var img = ee.Image().select();
    ['blue','green','red','nir','swir1','swir2'].forEach(function(b){
        try {
            var bi = ee.ImageCollection(bs+'/'+b.toLowerCase()).filter(ee.Filter.eq('system:index','image_peru_fire_sentinel2_minnbr_'+b.toLowerCase()+'_'+period)).mosaic();
            img = img.addBands(ee.Image(ee.Algorithms.If(bi.bandNames().size().gt(0),bi,ee.Image(0).rename(b.toLowerCase()).updateMask(0))).select([0],[b.toLowerCase()]),null,true);
        } catch(e) {
            img = img.addBands(ee.Image(0).rename(b.toLowerCase()).updateMask(0),null,true);
        }
    });
    manageMapLayer('mosaic_'+period, img, {
        bands: ['swir1', 'nir', 'red'],
        min: 5,
        max: 48,
        gamma: 1.1
    }, 'Mosaico Sentinel-2 MinNBR ' + period);
}

// ─── SELECT / DESELECT CELL ─────────────────────────────────────────────────

function setCellSelected(camp, stage, proposal, period, v){
    var key = cellKey(camp, stage, proposal, period);
    selectedCells[key] = v;
    if(v){
        loadMosaic(period);
        var img = ee.Image(classificationsRoot(camp)+'FILTERED/'+proposal+'/'+stage+'/'+period).select('probability').selfMask();
        manageMapLayer('cand_'+key, img, {min:0,max:1000,palette:['#fcc','#f00','#600']}, 'Cand '+period+' | '+proposal+' | '+stage+' | '+camp);
        // radio por linea: desmarcar otras propuestas de la misma fecha en este grid (mismo camp+stage)
        campaignData[camp].proposals.forEach(function(p2){
            if(p2!==proposal){
                var k2 = cellKey(camp, stage, p2, period);
                if(selectedCells[k2]){
                    selectedCells[k2] = false;
                    if(cellCheckboxes[k2])cellCheckboxes[k2].setValue(false);
                    removeMapLayer('cand_'+k2);
                }
            }
        });
    } else {
        removeMapLayer('cand_'+key);
        var any = Object.keys(selectedCells).some(function(k){
            return selectedCells[k] && k.split('__')[3]===period;
        });
        if(!any)removeMapLayer('mosaic_'+period);
    }
    updatePromoteSummary();
}

// ─── LOAD ALL ───────────────────────────────────────────────────────────────

function activeCampaigns(){return Object.keys(enabledCampaigns).filter(function(c){return enabledCampaigns[c];});}

function loadAll(){
    clearCandidateLayers();
    selectedCells = {};
    cellCheckboxes = {};
    promotedChecks = {};
    protocolChecked = {visual:false, mosaic:false, area:false};
    candidatesBox.clear();
    candidatesBox.add(ui.Label(L.loading,{fontSize:'10px',color:'#888'}));

    var camps = activeCampaigns();
    if(camps.length===0){
        campaignData = {};
        allDates = [];
        renderDateGrid();
        renderCandidates();
        updatePromoteSummary();
        hideLoading();
        return;
    }

    campaignData = {};
    var pending = camps.length;
    camps.forEach(function(camp){loadCampaign(camp, function(){pending--;if(pending===0)finishLoad();});});
}

function loadCampaign(camp, cb){
    campaignData[camp] = {proposals:[], stages:[], stageData:{}, promoted:{}};
    var root = classificationsRoot(camp);
    ee.data.listAssets(root+'FILTERED/',{},function(r,err){
        var props=[];
        if(!err&&r&&r.assets)props=r.assets.filter(function(a){return a.type==='FOLDER'}).map(function(a){return a.id.split('/').pop()}).sort();
        campaignData[camp].proposals = props;
        if(props.length===0){loadPromoted(camp, cb);return;}

        var pendingStages = props.length;
        var stageUnion = {};
        props.forEach(function(prop){
            ee.data.listAssets(root+'FILTERED/'+prop+'/',{},function(r2,err2){
                if(!err2&&r2&&r2.assets)r2.assets.forEach(function(a){
                    var name = a.id.split('/').pop();
                    // etapas ftXX sao IMAGE_COLLECTION no GEE (ver ensureFolder do M7)
                    if((a.type==='IMAGE_COLLECTION'||a.type==='FOLDER')&&/^ft\d\d$/.test(name))stageUnion[name]=true;
                });
                pendingStages--;
                if(pendingStages===0){
                    campaignData[camp].stages = Object.keys(stageUnion).sort();
                    var stg = campaignData[camp].stages;
                    if(stg.length===0){loadPromoted(camp, cb);return;}
                    stg.forEach(function(s){campaignData[camp].stageData[s]={};props.forEach(function(p){campaignData[camp].stageData[s][p]=[];});});
                    var pendingImgs = stg.length*props.length;
                    stg.forEach(function(s){
                        props.forEach(function(p){
                            ee.data.listAssets(root+'FILTERED/'+p+'/'+s+'/',{},function(r3,err3){
                                if(!err3&&r3&&r3.assets)r3.assets.forEach(function(a){
                                    if(a.type==='IMAGE')campaignData[camp].stageData[s][p].push(a.id.split('/').pop());
                                });
                                pendingImgs--;
                                if(pendingImgs===0)loadPromoted(camp, cb);
                            });
                        });
                    });
                }
            });
        });
    });
}

function loadPromoted(camp, cb){
    ee.data.listAssets(prePublicPath(camp),{},function(r,err){
        if(!err&&r&&r.assets)r.assets.forEach(function(a){
            if(a.type==='IMAGE')campaignData[camp].promoted[a.id.split('/').pop()]=true;
        });
        cb();
    });
}

function finishLoad(){
    var dateSet = {};
    Object.keys(campaignData).forEach(function(camp){
        var d = campaignData[camp];
        d.stages.forEach(function(s){
            d.proposals.forEach(function(p){
                (d.stageData[s][p]||[]).forEach(function(dt){dateSet[dt]=true;});
            });
        });
        Object.keys(d.promoted).forEach(function(dt){dateSet[dt]=true;});
    });
    allDates = Object.keys(dateSet).sort().reverse();
    if(!selectedDate || allDates.indexOf(selectedDate)===-1){
        var pick = null;
        for(var i=0;i<allDates.length;i++){if(!isDatePromotedGlobal(allDates[i])){pick=allDates[i];break;}}
        selectedDate = pick || (allDates[0]||null);
    }
    renderDateGrid();
    renderPromotedLine();
    renderCandidates();
    updatePromoteSummary();
    hideLoading();
}

// ─── DATE GRID ──────────────────────────────────────────────────────────────

function renderDateGrid(){
    if(!dateBox)return;
    dateBox.clear();
    dateBox.add(ui.Label(L.date, STYLE.label));
    var row = ui.Panel({layout:ui.Panel.Layout.flow('horizontal')});
    if(allDates.length===0){
        row.add(ui.Label(L.empty_pre, {fontSize:'10px',color:'#aaa',margin:'2px'}));
    } else {
        allDates.forEach(function(d){
            var blocked = isDatePromotedGlobal(d);
            var cb = ui.Checkbox({
                label: d + (blocked?'  ✅':''),
                value: selectedDate===d,
                disabled: blocked,
                style: STYLE.gridCell
            });
            dateCheckboxes[d] = cb;
            cb.onChange(function(v){
                if(!v)return;
                selectedDate = d;
                // seleccion unica
                Object.keys(dateCheckboxes).forEach(function(d2){
                    if(d2!==d&&dateCheckboxes[d2].getValue())dateCheckboxes[d2].setValue(false);
                });
                selectedCells = {};
                cellCheckboxes = {};
                clearCandidateLayers();
                renderCandidates();
                updatePromoteSummary();
            });
            row.add(cb);
        });
    }
    dateBox.add(row);
}

// ─── RENDER CANDIDATES (groups per campaign) ────────────────────────────────

function renderCandidates(){
    candidatesBox.clear();
    var camps = activeCampaigns();
    if(camps.length===0){
        candidatesBox.add(ui.Label(L.no_data,{fontSize:'11px',color:'#d32f2f',margin:'4px'}));
        buildProtocolChecklist();
        return;
    }
    if(!selectedDate){
        candidatesBox.add(ui.Label(L.empty_pre,{fontSize:'11px',color:'#888',margin:'4px'}));
        buildProtocolChecklist();
        return;
    }

    camps.forEach(function(camp){
        var d = campaignData[camp];
        if(!d)return;
        var group = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:STYLE.card});
        group.add(ui.Label(camp+' | '+classificationsRoot(camp), {fontSize:'10px',fontWeight:'bold',color:'#1a73e8',margin:'2px'}));

        var stages = d.stages.filter(function(s){
            return d.proposals.some(function(p){return (d.stageData[s][p]||[]).indexOf(selectedDate)!==-1;});
        });

        if(stages.length===0){
            group.add(ui.Label('('+L.empty_pre+')', {fontSize:'9px',color:'#aaa',margin:'1px 3px'}));
        } else {
            stages.forEach(function(stg){
                group.add(buildStageGrid(camp, stg, d));
            });
        }
        candidatesBox.add(group);
    });

    candidatesBox.add(ui.Button({label:L.unpromote, style:STYLE.btnRed, onClick:function(){showUnpromoteConfirm();}}));
    buildProtocolChecklist();
}

function buildStageGrid(camp, stage, d){
    var grid = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:{margin:'2px 0'}});
    var head = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:{backgroundColor:'#eef2fa',margin:'0 0 2px 0'}});
    head.add(ui.Label(stage, STYLE.gridHeader));
    d.proposals.forEach(function(prop){
        head.add(ui.Label(prop, STYLE.gridHead));
    });
    grid.add(head);

    var row = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:{margin:'1px 0'}});
    row.add(ui.Label(selectedDate, STYLE.gridDate));
    d.proposals.forEach(function(prop){
        var available = (d.stageData[stage][prop]||[]).indexOf(selectedDate)!==-1;
        var promoted = d.promoted[selectedDate];
        if(!available || promoted){
            row.add(ui.Label(promoted?'✅':'·', {fontSize:'9px',color:promoted?'#0f9d58':'#ccc',margin:'2px 6px'}));
            return;
        }
        var key = cellKey(camp, stage, prop, selectedDate);
        var cb = ui.Checkbox({label:'', value:!!selectedCells[key], style:STYLE.gridCell});
        cellCheckboxes[key] = cb;
        cb.onChange(function(v){setCellSelected(camp, stage, prop, selectedDate, v);});
        row.add(cb);
    });
    grid.add(row);
    return grid;
}

function updatePromoteSummary(){
    if(!promoteBox)return;
    var sel = Object.keys(selectedCells).filter(function(k){return selectedCells[k];});
    promoteBox.clear();
    promoteBox.add(ui.Label(L.target+': PRE_PUBLIC/{campana}', {fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'2px',padding:'4px',backgroundColor:'#fff',borderRadius:'3px'}));
    promoteBox.add(ui.Label(L.selected+': '+sel.length+' imagen'+(sel.length===1?'':'es'), sel.length>0?STYLE.statusOk:STYLE.statusErr));
    if(promoteButton){
        var ready = sel.length>0 && protocolChecked.visual && protocolChecked.mosaic && protocolChecked.area;
        promoteButton.setDisabled(!ready);
    }
}

// ─── PROTOCOL ───────────────────────────────────────────────────────────────

function buildProtocolChecklist(){
    if(!protocolBox)return;
    protocolBox.clear();
    protocolBox.add(ui.Label(L.protocol_hint, {fontSize:'10px',color:'#888',margin:'0 0 4px 0'}));
    var items = [
        {key:'visual', label:L.check_visual},
        {key:'mosaic', label:L.check_mosaic},
        {key:'area',   label:L.check_area}
    ];
    items.forEach(function(it){
        var cb = ui.Checkbox({label:it.label, value:protocolChecked[it.key]||false, style:STYLE.checkbox});
        cb.onChange(function(v){protocolChecked[it.key]=v;updatePromoteSummary();});
        protocolBox.add(cb);
    });
    var link = ui.Label(L.stats_link, {fontSize:'10px',color:'#1a73e8',margin:'2px 0 0 18px',textDecoration:'underline'});
    link.setUrl(STATS_URL);
    protocolBox.add(link);
}

// ─── PROMOTED (Ver / Despromover) ───────────────────────────────────────────

function showUnpromoteConfirm(){
    contentsBox.clear();
    var checked = Object.keys(promotedChecks).filter(function(k){return promotedChecks[k];});
    if(checked.length===0){
        contentsBox.clear();
        renderPromotedLine();
        return;
    }
    var card = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:STYLE.prePopup});
    card.add(ui.Label('⚠ '+L.unpromote_confirm,{fontSize:'12px',fontWeight:'bold',color:'#cc8800',margin:'2px'}));
    checked.forEach(function(k){
        var parts = k.split('__');
        card.add(ui.Label(parts[0]+' | '+parts[1], {fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'1px'}));
    });
    var br = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'4px 0 0 0'}});
    br.add(ui.Button({label:L.cancel,style:STYLE.btnGray,onClick:function(){renderPromotedLine();}}));
    br.add(ui.Button({label:L.ok,style:STYLE.btnRed,onClick:function(){doUnpromote(checked);}}));
    card.add(br);
    contentsBox.add(card);
}

function renderPromotedLine(){
    if(!contentsBox)return;
    contentsBox.clear();
    var card = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:STYLE.contentsCard});
    card.add(ui.Label(L.existing_pre, {fontSize:'10px',fontWeight:'bold',color:'#1a73e8',margin:'0 0 4px 0'}));
    var camps = activeCampaigns();
    var any = false;
    camps.forEach(function(camp){
        var d = campaignData[camp];
        if(!d)return;
        var periods = Object.keys(d.promoted).sort().reverse();
        periods.forEach(function(p){
            any = true;
            var row = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'), style:{margin:'1px 0'}});
            var pk = promotedKey(camp, p);
            var cb = ui.Checkbox({label:camp+' | '+p+' ✅', value:promotedChecks[pk]||false, style:STYLE.gridCell});
            cb.onChange(function(v){
                promotedChecks[pk] = v;
                if(v){
                    var img = ee.Image(prePublicPath(camp)+p).select('probability').selfMask();
                    loadMosaic(p);
                    manageMapLayer('promoted_'+pk, img, {min:0,max:1000,palette:['#fcc','#f00','#600']}, 'Promovido '+p+' | '+camp);
                } else {
                    removeMapLayer('promoted_'+pk);
                }
            });
            row.add(cb);
            card.add(row);
        });
    });
    if(!any)card.add(ui.Label(L.empty_pre, {fontSize:'10px',color:'#aaa',margin:'2px'}));
    contentsBox.add(card);
}

function doUnpromote(checked){
    setExportStatus('loading','Despromovendo...');
    var total = 0;
    checked.forEach(function(k){
        var parts = k.split('__');
        var dest = prePublicPath(parts[0])+parts[1];
        try{
            ee.data.deleteAsset(dest);
            print('Despromovido: '+dest);
            total++;
        }catch(e){
            print('Error: '+dest+' -> '+e);
        }
    });
    setExportStatus('success',L.unpromote_done+' ('+total+')');
    clearCandidateLayers();
    loadAll();
}

// ─── PRE-POPUP ──────────────────────────────────────────────────────────────

function showPrePopup(){
    protocolBox.clear();
    var sel = Object.keys(selectedCells).filter(function(k){return selectedCells[k];});
    if(sel.length===0){protocolBox.add(ui.Label(L.none_selected,STYLE.statusErr));return;}

    var box = ui.Panel({layout:ui.Panel.Layout.flow('vertical'),style:STYLE.prePopup});
    box.add(ui.Label('⚠ '+L.pre_title,{fontSize:'13px',fontWeight:'bold',color:'#cc8800',margin:'2px'}));
    box.add(ui.Label(L.pre_body,{fontSize:'11px',color:'#333',margin:'2px'}));
    sel.forEach(function(k){
        var parts = k.split('__');
        box.add(ui.Label('  '+parts[3]+'  |  '+parts[0]+'  |  '+parts[1]+'  |  '+parts[2],{fontSize:'11px',fontFamily:'monospace',color:'#1a73e8',margin:'1px'}));
    });
    box.add(ui.Label(L.pre_warn,{fontSize:'10px',color:'#888',margin:'4px 2px'}));
    var br = ui.Panel({layout:ui.Panel.Layout.flow('horizontal'),style:{stretch:'horizontal',margin:'4px 0 0 0'}});
    br.add(ui.Button({label:L.cancel,style:STYLE.btnGray,onClick:function(){buildProtocolChecklist();}}));
    br.add(ui.Button({label:L.ok,style:STYLE.btnGreen,onClick:function(){doPromote(sel);}}));
    box.add(br);
    protocolBox.add(box);
}

// ─── CREATE PRE_PUBLIC STRUCTURE (only here, inside a button) ───────────────

function getAssetInfo(path){
    try{return ee.data.getAsset(path);}catch(e){return null;}
}

function ensurePrePublicStructure(camp){
    var root = classificationsRoot(camp);
    var base = root+'PRE_PUBLIC';
    var info = getAssetInfo(base);

    if(info===null){
        ee.data.createAsset({type:'FOLDER'}, base);
    } else if(info.type!=='FOLDER'){
        var listing = ee.data.listAssets(base, {});
        if(!listing || typeof listing.assets === 'undefined'){
            setExportStatus('error','Nao foi possivel inspecionar PRE_PUBLIC. Recrie como FOLDER manualmente no GEE.');
            return false;
        }
        var hasAssets = listing.assets.length>0;
        if(!hasAssets){
            ee.data.deleteAsset(base);
            ee.data.createAsset({type:'FOLDER'}, base);
            print('ℹ️ PRE_PUBLIC recriado como FOLDER (era '+info.type+').');
        } else {
            setExportStatus('error','PRE_PUBLIC e '+info.type+' e contem assets. Reestruture para FOLDER manualmente.');
            return false;
        }
    }

    var camppath = base + '/' + camp.toLowerCase();
    if(getAssetInfo(camppath)===null){
        ee.data.createAsset({type:'IMAGE_COLLECTION'}, camppath);
    }
    return true;
}

// ─── PROMOTE ────────────────────────────────────────────────────────────────

function doPromote(cells){
    protocolBox.clear();
    protocolBox.add(ui.Label(L.loading,{fontSize:'11px',color:'#1a73e8',margin:'4px'}));
    setExportStatus('loading','Promovendo '+cells.length+' imagen'+(cells.length===1?'':'es')+'...');
    showLoading();

    var total = 0;
    cells.forEach(function(k){
        var parts = k.split('__');
        var camp = parts[0], stage = parts[1], prop = parts[2], period = parts[3];
        if(!ensurePrePublicStructure(camp))return;
        var src = classificationsRoot(camp)+'FILTERED/'+prop+'/'+stage+'/'+period;
        var dest = prePublicPath(camp)+period;
        try{ee.data.getAsset(dest);setExportStatus('info','Ja existe: '+period+' ('+camp+')');}
        catch(e){
            total++;
            print('Copiando: '+src+' -> '+dest);
            ee.data.copyAsset(src,dest);
        }
    });

    protocolBox.clear();
    protocolBox.add(ui.Label(L.done+' ('+total+' imagen'+(total===1?'':'es')+')',{fontSize:'12px',color:'#0f9d58',fontWeight:'bold',margin:'4px'}));
    hideLoading();
    loadAll();
}

// ─── SECTIONS ───────────────────────────────────────────────────────────────

function buildConfigSection(){
    var section = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:SECTION_STYLE.config});
    section.add(ui.Label(L.cfg, STYLE.sectionTitle));

    section.add(ui.Label(L.country, STYLE.label));
    dropdownCountry = ui.Select({items:Object.keys(COUNTRIES), value:COUNTRY, style:STYLE.input});
    dropdownCountry.onChange(function(v){if(v&&v!==COUNTRY)setCountry(v);});
    section.add(dropdownCountry);

    dateBox = ui.Panel({layout:ui.Panel.Layout.flow('vertical')});
    section.add(dateBox);
    renderDateGrid();

    section.add(ui.Label(L.campaign, STYLE.label));
    campaignBox = ui.Panel({layout:ui.Panel.Layout.flow('horizontal')});
    CAMPAIGNS.forEach(function(c, idx){
        var cb = ui.Checkbox({label:c, value:idx===0, style:STYLE.gridCell});
        enabledCampaigns[c] = idx===0;
        cb.onChange(function(v){enabledCampaigns[c]=v;selectedDate=null;loadAll();});
        campaignBox.add(cb);
    });
    section.add(campaignBox);
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
    promoteButton = ui.Button({label:L.promote_btn, style:STYLE.btnGreen, disabled:true, onClick:function(){showPrePopup();}});
    actionsRow.add(promoteButton);
    section.add(actionsRow);
    updatePromoteSummary();
    return section;
}

// ─── FORM ───────────────────────────────────────────────────────────────────

function buildForm(){
    ui.root.clear();

    var sidePanel = ui.Panel({
        layout: ui.Panel.Layout.flow('vertical'),
        style: {width: '540px', margin: '0', padding: '6px', backgroundColor: '#fff'}
    });

    sidePanel.add(ui.Label('MapBiomas-Fuego | '+L.title,{fontSize:'14px',fontWeight:'bold',color:'#d32f2f',margin:'4px'}));
    statusLabel = ui.Label({value:'', style:{fontSize:'10px',color:'#1a73e8',margin:'2px 4px',shown:false,stretch:'horizontal'}});
    sidePanel.add(statusLabel);

    sidePanel.add(buildConfigSection());
    sidePanel.add(buildCandidatesSection());
    sidePanel.add(buildProtocolSection());

    exportStatus = ui.Panel({layout:ui.Panel.Layout.flow('vertical'), style:{margin:'4px',shown:false}});
    sidePanel.add(exportStatus);

    sidePanel.add(buildPromoteSection());

    mapWidget.setOptions('SATELLITE');
    mapWidget.centerObject(REGIONS);
    manageMapLayer('regions_boundary', REGIONS.style({color:'ffffff',fillColor:'00000000',width:1}), {}, 'Regiones');

    var splitPanel = ui.SplitPanel({
        firstPanel: sidePanel,
        secondPanel: mapWidget,
        orientation: 'horizontal',
        wipe: false
    });

    ui.root.add(splitPanel);

    loadAll();
}

// ─── INIT ───────────────────────────────────────────────────────────────────

buildForm();
print('M9_00 5.0 carregado.');