/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M7_00
Selection and Export (UI)

📅 DATA: julho 2026
🏷️ VERSAO: 2.1
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Seleciona ou cria colecao em FILTERED/
2. Define parametros (campanha, sensor, mosaico, periodicidade)
3. Seleciona periodo e visualiza mosaico min NBR
4. Para cada regiao, escolhe qual modelo DNN usar
5. Compoe imagem nacional por periodo
6. Exporta para FILTERED/{collection_name}-ft00/{period}

🌍 IDIOMAS: pt, es, en, fr, id
********************************************/

var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var CAMPAIGN = 'MONITOR_01';
var CLASSIFICATIONS_ROOT = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var SCALE = 10;
var START_YEAR = 2025;
var APP_LANG = 'pt';

var L = (function () {
    var dict = {
        pt: {
            title: 'MapBiomas-Fogo | M7 — Selecao e Export',
            config: 'CONFIG', period: 'PERIODO', regions: 'REGIOES', confirm: 'CONFIRMAR',
            lbl_campaign: 'Campanha', lbl_sensor: 'Sensor', lbl_mosaic: 'Mosaico',
            lbl_periodicity: 'Periodicidade', lbl_collection_name: 'Nome da colecao',
            lbl_collection_placeholder: 'ex: propose_a',
            lbl_existing: 'Colecoes em FILTERED/',
            lbl_existing_loading: '(carregando...)',
            lbl_existing_none: '(nenhuma colecao)',
            lbl_year: 'Ano', lbl_month: 'Mes', lbl_annual: 'Anual',
            lbl_loading: 'Carregando...',
            lbl_no_data: 'Sem dados para o periodo.',
            lbl_region: 'Regiao', lbl_models: 'Modelos disponiveis',
            lbl_select_all: 'Selecionar todos', lbl_deselect_all: 'Limpar todos',
            lbl_new_collection: 'Nova colecao',
            lbl_add_existing: 'Adicionar periodo',
            lbl_btn_export: 'Exportar',
            lbl_confirm_title: 'Confirmar Exportacao',
            lbl_confirm_ok: 'Confirmar',
            lbl_confirm_cancel: 'Cancelar',
            lbl_status_one: '1 modelo',
            lbl_status_none: 'nenhum modelo',
            lbl_exporting: 'Exportando...',
            lbl_done: 'Concluido!',
            lbl_no_selection: 'Nenhuma regiao configurada.',
            lbl_mosaic_loading: 'Carregando mosaico...',
            lbl_class_loading: 'Carregando classificacoes...',
            lbl_error_no_region_model: 'Selecione ao menos 1 modelo por regiao.',
            lbl_pre_popup_title: 'Pre-Confirmacao',
            lbl_pre_popup_body: 'Sera criada/atualizada a collection:',
            lbl_pre_popup_warn: 'O GEE solicitara confirmacao no navegador.',
            lbl_pre_popup_continue: 'OK, continuar',
        },
        es: {
            title: 'MapBiomas-Fuego | M7 — Seleccion y Export',
            config: 'CONFIG', period: 'PERIODO', regions: 'REGIONES', confirm: 'CONFIRMAR',
            lbl_campaign: 'Campana', lbl_sensor: 'Sensor', lbl_mosaic: 'Mosaico',
            lbl_periodicity: 'Periodicidad', lbl_collection_name: 'Nombre de coleccion',
            lbl_collection_placeholder: 'ej: propose_a',
            lbl_existing: 'Colecciones en FILTERED/',
            lbl_existing_loading: '(cargando...)',
            lbl_existing_none: '(ninguna coleccion)',
            lbl_year: 'Ano', lbl_month: 'Mes', lbl_annual: 'Anual',
            lbl_loading: 'Cargando...',
            lbl_no_data: 'Sin datos para el periodo.',
            lbl_region: 'Region', lbl_models: 'Modelos disponibles',
            lbl_select_all: 'Seleccionar todos', lbl_deselect_all: 'Limpiar todos',
            lbl_new_collection: 'Nueva coleccion',
            lbl_add_existing: 'Agregar periodo',
            lbl_btn_export: 'Exportar',
            lbl_confirm_title: 'Confirmar Exportacion',
            lbl_confirm_ok: 'Confirmar', lbl_confirm_cancel: 'Cancelar',
            lbl_status_one: '1 modelo', lbl_status_none: 'ningun modelo',
            lbl_exporting: 'Exportando...', lbl_done: 'Completado!',
            lbl_no_selection: 'Ninguna region configurada.',
            lbl_mosaic_loading: 'Cargando mosaico...',
            lbl_class_loading: 'Cargando clasificaciones...',
            lbl_error_no_region_model: 'Seleccione al menos 1 modelo por region.',
            lbl_pre_popup_title: 'Pre-Confirmacion',
            lbl_pre_popup_body: 'Se creara/actualizara la coleccion:',
            lbl_pre_popup_warn: 'GEE solicitara confirmacion en el navegador.',
            lbl_pre_popup_continue: 'OK, continuar',
        },
        en: {
            title: 'MapBiomas-Fire | M7 — Selection and Export',
            config: 'CONFIG', period: 'PERIOD', regions: 'REGIONS', confirm: 'CONFIRM',
            lbl_campaign: 'Campaign', lbl_sensor: 'Sensor', lbl_mosaic: 'Mosaic',
            lbl_periodicity: 'Periodicity', lbl_collection_name: 'Collection name',
            lbl_collection_placeholder: 'e.g. propose_a',
            lbl_existing: 'Collections in FILTERED/',
            lbl_existing_loading: '(loading...)',
            lbl_existing_none: '(no collections)',
            lbl_year: 'Year', lbl_month: 'Month', lbl_annual: 'Annual',
            lbl_loading: 'Loading...',
            lbl_no_data: 'No data for selected period.',
            lbl_region: 'Region', lbl_models: 'Available models',
            lbl_select_all: 'Select all', lbl_deselect_all: 'Clear all',
            lbl_new_collection: 'New collection',
            lbl_add_existing: 'Add period',
            lbl_btn_export: 'Export',
            lbl_confirm_title: 'Confirm Export',
            lbl_confirm_ok: 'Confirm', lbl_confirm_cancel: 'Cancel',
            lbl_status_one: '1 model', lbl_status_none: 'no model',
            lbl_exporting: 'Exporting...', lbl_done: 'Done!',
            lbl_no_selection: 'No region configured.',
            lbl_mosaic_loading: 'Loading mosaic...',
            lbl_class_loading: 'Loading classifications...',
            lbl_error_no_region_model: 'Select at least 1 model per region.',
            lbl_pre_popup_title: 'Pre-Confirmation',
            lbl_pre_popup_body: 'Will create/update collection:',
            lbl_pre_popup_warn: 'GEE will prompt for browser confirmation.',
            lbl_pre_popup_continue: 'OK, continue',
        },
        fr: {
            title: 'MapBiomas-Feu | M7 — Selection et Export',
            config: 'CONFIG', period: 'PERIODE', regions: 'REGIONS', confirm: 'CONFIRMER',
            lbl_campaign: 'Campagne', lbl_sensor: 'Capteur', lbl_mosaic: 'Mosaique',
            lbl_periodicity: 'Periodicite', lbl_collection_name: 'Nom de la collection',
            lbl_collection_placeholder: 'ex: propose_a',
            lbl_existing: 'Collections dans FILTERED/',
            lbl_existing_loading: '(chargement...)',
            lbl_existing_none: '(aucune collection)',
            lbl_year: 'Annee', lbl_month: 'Mois', lbl_annual: 'Annuel',
            lbl_loading: 'Chargement...',
            lbl_no_data: 'Pas de donnees.',
            lbl_region: 'Region', lbl_models: 'Modeles disponibles',
            lbl_select_all: 'Tout selectionner', lbl_deselect_all: 'Tout effacer',
            lbl_new_collection: 'Nouvelle collection',
            lbl_add_existing: 'Ajouter periode',
            lbl_btn_export: 'Exporter',
            lbl_confirm_title: 'Confirmer l\'exportation',
            lbl_confirm_ok: 'Confirmer', lbl_confirm_cancel: 'Annuler',
            lbl_status_one: '1 modele', lbl_status_none: 'aucun modele',
            lbl_exporting: 'Exportation...', lbl_done: 'Termine!',
            lbl_no_selection: 'Aucune region configuree.',
            lbl_mosaic_loading: 'Chargement mosaique...',
            lbl_class_loading: 'Chargement classifications...',
            lbl_error_no_region_model: 'Selectionnez au moins 1 modele par region.',
            lbl_pre_popup_title: 'Pre-Confirmation',
            lbl_pre_popup_body: 'Va creer/mettre a jour la collection:',
            lbl_pre_popup_warn: 'GEE demandera confirmation dans le navigateur.',
            lbl_pre_popup_continue: 'OK, continuer',
        },
        id: {
            title: 'MapBiomas-Api | M7 — Seleksi dan Ekspor',
            config: 'KONFIG', period: 'PERIODE', regions: 'WILAYAH', confirm: 'KONFIRMASI',
            lbl_campaign: 'Kampanye', lbl_sensor: 'Sensor', lbl_mosaic: 'Mosaik',
            lbl_periodicity: 'Periodisitas', lbl_collection_name: 'Nama koleksi',
            lbl_collection_placeholder: 'cth: propose_a',
            lbl_existing: 'Koleksi di FILTERED/',
            lbl_existing_loading: '(memuat...)',
            lbl_existing_none: '(tidak ada)',
            lbl_year: 'Tahun', lbl_month: 'Bulan', lbl_annual: 'Tahunan',
            lbl_loading: 'Memuat...',
            lbl_no_data: 'Tidak ada data.',
            lbl_region: 'Wilayah', lbl_models: 'Model tersedia',
            lbl_select_all: 'Pilih semua', lbl_deselect_all: 'Hapus semua',
            lbl_new_collection: 'Koleksi baru',
            lbl_add_existing: 'Tambah periode',
            lbl_btn_export: 'Ekspor',
            lbl_confirm_title: 'Konfirmasi Ekspor',
            lbl_confirm_ok: 'Konfirmasi', lbl_confirm_cancel: 'Batal',
            lbl_status_one: '1 model', lbl_status_none: 'tidak ada',
            lbl_exporting: 'Mengekspor...', lbl_done: 'Selesai!',
            lbl_no_selection: 'Tidak ada wilayah.',
            lbl_mosaic_loading: 'Memuat mosaik...',
            lbl_class_loading: 'Memuat klasifikasi...',
            lbl_error_no_region_model: 'Pilih minimal 1 model per wilayah.',
            lbl_pre_popup_title: 'Pra-Konfirmasi',
            lbl_pre_popup_body: 'Akan membuat/memperbarui koleksi:',
            lbl_pre_popup_warn: 'GEE akan meminta konfirmasi browser.',
            lbl_pre_popup_continue: 'OK, lanjutkan',
        },
    };
    return dict[APP_LANG] || dict['pt'];
})();

var styles = {
    main_panel: { margin: '0px', padding: '4px', backgroundColor: '#ffffff' },
    card: { margin: '2px', padding: '6px', border: '1px solid #e0e0e0', backgroundColor: '#fcfcfc', borderRadius: '4px' },
    row: { margin: '0px', padding: '2px', stretch: 'horizontal' },
    title: { margin: '2px', padding: '2px', fontSize: '13px', fontWeight: 'bold', color: '#333' },
    label: { margin: '1px', padding: '0px', fontSize: '11px', color: '#555' },
    input: { margin: '1px', padding: '2px', stretch: 'horizontal' },
    input_large: { margin: '2px', padding: '6px', stretch: 'horizontal', fontSize: '13px' },
    btn_blue: { margin: '2px', padding: '4px 10px', color: '#1a73e8', fontWeight: 'bold', fontSize: '11px' },
    btn_green: { margin: '2px', padding: '4px 10px', color: '#0f9d58', fontWeight: 'bold', fontSize: '11px' },
    btn_gray: { margin: '2px', padding: '4px 10px', color: '#70757a', fontWeight: 'bold', fontSize: '11px' },
    tab_active: { margin: '0px', padding: '6px 12px', border: '1px solid #1a73e8', color: '#1a73e8', fontWeight: 'bold', backgroundColor: '#e8f0fe', stretch: 'horizontal', fontSize: '12px' },
    tab_inactive: { margin: '0px', padding: '6px 12px', border: '1px solid #d3d3d3', color: '#70757a', backgroundColor: '#f1f3f4', stretch: 'horizontal', fontSize: '12px' },
    region_card: { margin: '4px 0px', padding: '6px', border: '1px solid #e0e0e0', backgroundColor: '#fafafa', borderRadius: '4px' },
    model_row: { margin: '1px 0px', padding: '2px', stretch: 'horizontal' },
    status_ok: { color: '#0f9d58', fontWeight: 'bold', fontSize: '11px' },
    status_warn: { color: '#e37400', fontWeight: 'bold', fontSize: '11px' },
    status_err: { color: '#d32f2f', fontWeight: 'bold', fontSize: '11px' },
    pre_popup_bg: { margin: '4px', padding: '10px', backgroundColor: '#fff8e1', border: '1px solid #ffcc00', borderRadius: '6px' },
};

var CLASS_PALETTE = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
    '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
];

var managedLayers = {};
var availableModels = {};
var regionModelMap = {};
var regionEyeState = {};
var _cbStore = {};
var currentYear = null;
var currentMonth = null;
var currentPeriodKey = '';
var currentMosaicImg = null;
var collectionName = 'propose_a';
var _existingCollections = [];

var panel_root = null;
var panel_body = null;
var abas = {};
var txtCollectionName = null;

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function ensureFolder(name) {
    var parts = name.split('/');
    var current = CLASSIFICATIONS_ROOT;
    for (var i = 0; i < parts.length; i++) {
        current += parts[i];
        try { ee.data.getAsset(current); }
        catch (e) { ee.data.createAsset({ type: (i === parts.length - 1 && parts[i].indexOf('-ft') !== -1) ? 'IMAGE_COLLECTION' : 'FOLDER' }, current); }
        current += '/';
    }
}

function getDateKey(y, m) {
    return m !== null ? y + '_' + ('0' + m).slice(-2) : '' + y;
}

// ─── MAP ────────────────────────────────────────────────────────────────────

function updateManagedLayer(id, eeObject, vis, name) {
    if (managedLayers[id]) { managedLayers[id].setEeObject(eeObject); managedLayers[id].setVisParams(vis); managedLayers[id].setName(name); }
    else { managedLayers[id] = ui.Map.Layer(eeObject, vis, name); Map.layers().add(managedLayers[id]); }
}

function removeAllClassLayers() {
    Object.keys(managedLayers).forEach(function (id) { if (id.indexOf('class_') === 0) { Map.layers().remove(managedLayers[id]); delete managedLayers[id]; } });
}

// ─── MOSAIC ──────────────────────────────────────────────────────────────────

function loadMosaic(year, month) {
    var dk = getDateKey(year, month);
    var base = CATALOG_ROOT + '/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR';
    var bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];
    var mosaico = ee.Image().select();
    bands.forEach(function (b) {
        try {
            var bi = ee.ImageCollection(base + '/' + b.toLowerCase()).filter(ee.Filter.eq('system:index', 'image_peru_fire_sentinel2_minnbr_' + b.toLowerCase() + '_' + dk)).mosaic();
            var s = ee.Image(ee.Algorithms.If(bi.bandNames().size().gt(0), bi, ee.Image(0).rename(b.toLowerCase()).updateMask(0)));
            mosaico = mosaico.addBands(s.select([0], [b.toLowerCase()]), null, true);
        } catch (e) { mosaico = mosaico.addBands(ee.Image(0).rename(b.toLowerCase()).updateMask(0), null, true); }
    });
    mosaico = mosaico.addBands(mosaico.normalizedDifference(['nir', 'swir2']).rename('nbr'));
    updateManagedLayer('mosaic_minnbr', mosaico, { bands: ['swir1', 'nir', 'red'], min: 3, max: 40, gamma: 0.85 }, 'Min NBR ' + dk);
    currentMosaicImg = mosaico;
    return mosaico;
}

// ─── CLASSIFICATIONS ────────────────────────────────────────────────────────

function loadClassifications(year, month, callback) {
    var dk = getDateKey(year, month);
    var regional = CLASSIFICATIONS_ROOT + 'REGIONAL';
    ee.data.listAssets(regional, {}, function (cols) {
        if (!cols || !cols.assets) { callback({}); return; }
        var dirs = cols.assets.filter(function (c) { return c.type === 'IMAGE_COLLECTION'; });
        if (dirs.length === 0) { callback({}); return; }
        var result = {};
        var pending = dirs.length;
        dirs.forEach(function (c, idx) {
            var modelId = c.id.split('/').pop();
            ee.data.listAssets(c.id, {}, function (imgs) {
                if (imgs && imgs.assets) imgs.assets.forEach(function (img) {
                    if (img.type !== 'IMAGE') return;
                    var name = img.id.split('/').pop();
                    var parts = name.split('_');
                    var regionPart = null;
                    for (var i = 0; i < parts.length; i++) { if (parts[i].indexOf('region') === 0) { regionPart = parts[i]; break; } }
                    if (!regionPart) return;
                    var imgPeriod = null;
                    for (var j = parts.length - 1; j >= 0; j--) {
                        if (/^\d{4}$/.test(parts[j])) { imgPeriod = parts[j] + (j + 1 < parts.length && /^\d{2}$/.test(parts[j + 1]) ? '_' + parts[j + 1] : ''); break; }
                    }
                    if (imgPeriod !== dk) return;
                    if (!result[regionPart]) result[regionPart] = [];
                    if (!result[regionPart].some(function (r) { return r.modelId === modelId; }))
                        result[regionPart].push({ modelId: modelId, assetId: img.id, color: CLASS_PALETTE[idx % 15] });
                });
                pending--;
                if (pending === 0) callback(result);
            });
        });
        if (pending === 0) callback(result);
    });
}

// ─── EXISTING COLLECTIONS ───────────────────────────────────────────────────

function loadExistingCollections(callback) {
    ensureFolder('FILTERED');
    var base = CLASSIFICATIONS_ROOT + 'FILTERED/';
    ee.data.listAssets(base, {}, function (result) {
        if (!result || !result.assets) { callback([]); return; }
        var names = result.assets.filter(function (a) { return a.type === 'IMAGE_COLLECTION'; }).map(function (a) { return a.id.split('/').pop(); }).sort();
        _existingCollections = names;
        callback(names);
    });
}

// ─── UI ─────────────────────────────────────────────────────────────────────

function buildUI() {
    ui.root.clear();
    panel_root = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: { width: '580px', margin: '0px', padding: '4px', backgroundColor: '#ffffff' } });
    panel_root.add(ui.Label('MapBiomas-Fuego | M7', { fontSize: '15px', fontWeight: 'bold', color: '#d32f2f', margin: '4px' }));
    panel_root.add(ui.Label(L.title, { fontSize: '12px', color: '#555', margin: '2px 4px' }));
    var tabBar = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '4px 0px', stretch: 'horizontal' } });
    abas.btnConfig = ui.Button({ label: L.config, style: styles.tab_active, onClick: function () { showTab('config'); } });
    abas.btnPeriod = ui.Button({ label: L.period, style: styles.tab_inactive, onClick: function () { showTab('period'); } });
    abas.btnRegions = ui.Button({ label: L.regions, style: styles.tab_inactive, onClick: function () { showTab('regions'); } });
    abas.btnConfirm = ui.Button({ label: L.confirm, style: styles.tab_inactive, onClick: function () { showTab('confirm'); } });
    tabBar.add(abas.btnConfig).add(abas.btnPeriod).add(abas.btnRegions).add(abas.btnConfirm);
    panel_root.add(tabBar);
    panel_body = ui.Panel({ style: { margin: '4px', padding: '4px' } });
    panel_root.add(panel_body);
    ui.root.add(panel_root);
    Map.setOptions('SATELLITE');
    Map.centerObject(REGIONS);
    Map.addLayer(REGIONS.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
    showTab('config');
}

function showTab(tabName) {
    ['Config', 'Period', 'Regions', 'Confirm'].forEach(function (t) {
        var key = 'btn' + t;
        if (abas[key]) abas[key].style = (t.toLowerCase() === tabName) ? styles.tab_active : styles.tab_inactive;
    });
    panel_body.clear();
    if (tabName === 'config') buildConfigTab();
    else if (tabName === 'period') buildPeriodTab();
    else if (tabName === 'regions') buildRegionsTab();
    else if (tabName === 'confirm') buildConfirmTab();
}

// ─── TAB: CONFIG ────────────────────────────────────────────────────────────

function buildConfigTab() {
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });

    // Existing collections dropdown
    var lblEx = ui.Label(L.lbl_existing, { margin: '4px 1px 0px 1px', fontSize: '11px', color: '#555' });
    card.add(lblEx);
    var ddExisting = ui.Select({ items: [L.lbl_existing_loading], value: null, style: styles.input });
    ddExisting.setDisabled(true);
    card.add(ddExisting);

    loadExistingCollections(function (names) {
        if (names.length === 0) {
            ddExisting.items().reset([L.lbl_existing_none]);
            ddExisting.setDisabled(true);
        } else {
            ddExisting.items().reset(names);
            ddExisting.setDisabled(false);
        }
    });
    ddExisting.onChange(function (v) { if (v && v.indexOf('(') === -1) { txtCollectionName.setValue(v); collectionName = v; } });

    // Collection name textbox
    card.add(ui.Label(L.lbl_collection_name, styles.label));
    txtCollectionName = ui.Textbox({ placeholder: L.lbl_collection_placeholder, value: collectionName, style: styles.input_large });
    txtCollectionName.onChange(function (v) { collectionName = v; });
    card.add(txtCollectionName);

    // Campaign (fixed, preselected)
    card.add(ui.Label(L.lbl_campaign, styles.label));
    card.add(ui.Label('MONITOR_01', { fontSize: '12px', fontWeight: 'bold', color: '#333', margin: '2px', padding: '4px' }));

    // Sensor
    card.add(ui.Label(L.lbl_sensor, styles.label));
    var ddSensor = ui.Select({ items: ['sentinel2', 'landsat'], value: 'sentinel2', style: styles.input });
    card.add(ddSensor);

    // Mosaic
    card.add(ui.Label(L.lbl_mosaic, styles.label));
    var ddMosaic = ui.Select({ items: ['minnbr', 'minnbr_buffer', 'median', 'minndvi'], value: 'minnbr', style: styles.input });
    card.add(ddMosaic);

    // Periodicity
    card.add(ui.Label(L.lbl_periodicity, styles.label));
    var ddPeriodicity = ui.Select({ items: ['monthly', 'yearly'], value: 'monthly', style: styles.input });
    card.add(ddPeriodicity);

    // Buttons
    card.add(ui.Label('', { margin: '4px' }));
    var btnRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    var btnNew = ui.Button({ label: L.lbl_new_collection, style: styles.btn_green, onClick: function () { ensureFolder('FILTERED/' + collectionName + '-ft00'); print('OK: FILTERED/' + collectionName + '-ft00'); showTab('period'); } });
    var btnAdd = ui.Button({ label: L.lbl_add_existing, style: styles.btn_blue, onClick: function () { showTab('period'); } });
    btnRow.add(btnNew).add(btnAdd);
    card.add(btnRow);

    panel_body.add(card);
}

// ─── TAB: PERIOD ─────────────────────────────────────────────────────────────

function buildPeriodTab() {
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });
    var today = new Date();
    var mY = today.getFullYear();
    var mM = today.getMonth();
    if (mM === 0) { mM = 12; mY--; }
    var yrs = [];
    for (var y = START_YEAR; y <= mY; y++) yrs.push({ label: '' + y, value: y });
    yrs.reverse();
    var mths = [];
    for (var m = mM; m >= 1; m--) { var mm = m < 10 ? '0' + m : '' + m; mths.push({ label: mm, value: m }); }

    var ddY = ui.Select({ items: yrs.map(function (y) { return y.label; }), value: '' + mY, style: styles.input });
    var ddM = ui.Select({ items: mths.map(function (m) { return m.label; }), value: mths[0].label, style: styles.input });
    currentYear = mY;
    currentMonth = mths[0].value;
    currentPeriodKey = getDateKey(currentYear, currentMonth);

    ddY.onChange(function (v) { currentYear = parseInt(v, 10); refreshPeriod(); });
    ddM.onChange(function (v) { currentMonth = parseInt(v, 10); refreshPeriod(); });
    card.add(ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [ui.Label(L.lbl_year, styles.label), ddY] }));
    card.add(ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [ui.Label(L.lbl_month, styles.label), ddM] }));
    card.add(ui.Button({ label: 'Carregar periodo', style: styles.btn_blue, onClick: refreshPeriod }));
    panel_body.add(card);
    refreshPeriod();
}

function refreshPeriod() {
    currentPeriodKey = getDateKey(currentYear, currentMonth);
    loadMosaic(currentYear, currentMonth);
    Map.centerObject(REGIONS);
}

// ─── TAB: REGIONS ────────────────────────────────────────────────────────────

function buildRegionsTab() {
    panel_body.add(ui.Label(L.lbl_class_loading + ' ' + currentPeriodKey, { fontSize: '10px', color: '#888' }));
    loadClassifications(currentYear, currentMonth, function (data) {
        availableModels = {};
        availableModels[currentPeriodKey] = data;
        panel_body.clear();
        var names = Object.keys(data).sort();
        if (names.length === 0) { panel_body.add(ui.Label(L.lbl_no_data, { color: '#d32f2f', fontSize: '12px', margin: '10px' })); return; }
        var scroll = ui.Panel({ style: { margin: '2px', padding: '2px' } });
        var hr = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '2px', padding: '4px', stretch: 'horizontal' } });
        hr.add(ui.Button({ label: L.lbl_select_all, style: styles.btn_blue, onClick: function () { names.forEach(function (r) { if (data[r].length > 0) regionModelMap[r] = data[r][0].modelId; }); buildRegionsTab(); } }));
        hr.add(ui.Button({ label: L.lbl_deselect_all, style: styles.btn_gray, onClick: function () { regionModelMap = {}; buildRegionsTab(); } }));
        scroll.add(hr);
        names.forEach(function (rn, idx) {
            var models = data[rn].sort(function (a, b) { return a.modelId.localeCompare(b.modelId); });
            var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.region_card });
            card.add(ui.Label(rn.replace('region', 'Region '), { fontSize: '13px', fontWeight: 'bold', color: '#1a73e8', margin: '2px 0px' }));
            if (!regionModelMap[rn] && models.length > 0) regionModelMap[rn] = models[0].modelId;
            if (!_cbStore[rn]) _cbStore[rn] = {};
            models.forEach(function (m) {
                var sel = (regionModelMap[rn] === m.modelId);
                var cb = ui.Checkbox({ label: m.modelId, value: sel, style: { fontSize: '10px', margin: '1px 4px' } });
                cb.onChange(function (v) { if (v) { regionModelMap[rn] = m.modelId; Object.keys(_cbStore[rn]).forEach(function (k) { if (k !== m.modelId) _cbStore[rn][k].setValue(false); }); } else { if (regionModelMap[rn] === m.modelId) regionModelMap[rn] = null; } });
                _cbStore[rn][m.modelId] = cb;
                var eye = ui.Button({ label: ' o ', style: styles.btn_gray, onClick: function () {
                    var key = rn + '_' + m.modelId;
                    if (!regionEyeState[key]) regionEyeState[key] = false;
                    regionEyeState[key] = !regionEyeState[key];
                    if (regionEyeState[key]) { updateManagedLayer('class_' + key, ee.Image(m.assetId).select(0).divide(10).toByte().selfMask(), { min: 0, max: 100, palette: ['#ffcccc', '#ff6666', '#cc0000', '#660000'] }, m.modelId + ' | ' + rn); this.style = styles.btn_blue; }
                    else { if (managedLayers['class_' + key]) { Map.layers().remove(managedLayers['class_' + key]); delete managedLayers['class_' + key]; } this.style = styles.btn_gray; }
                } });
                card.add(ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.model_row, widgets: [cb, eye] }));
            });
            scroll.add(card);
        });
        panel_body.add(scroll);
    });
}

// ─── TAB: CONFIRM ────────────────────────────────────────────────────────────

function buildConfirmTab() {
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });
    var fullName = collectionName + '-ft00';
    card.add(ui.Label(L.lbl_confirm_title, { fontSize: '14px', fontWeight: 'bold', color: '#333', margin: '4px' }));
    card.add(ui.Label(L.lbl_collection_name + ': ' + fullName, { fontSize: '12px', color: '#1a73e8', fontWeight: 'bold', fontFamily: 'monospace', margin: '4px' }));
    card.add(ui.Label('Periodo: ' + currentPeriodKey, { fontSize: '11px', margin: '4px' }));

    var regionNames = Object.keys(regionModelMap).sort();
    var hasAll = true;
    regionNames.forEach(function (r) { var m = regionModelMap[r]; card.add(ui.Label('  ' + r.replace('region', 'Region ') + ': ' + (m ? L.lbl_status_one + ' (' + m + ')' : L.lbl_status_none), m ? styles.status_ok : styles.status_err)); if (!m) hasAll = false; });
    if (regionNames.length === 0) card.add(ui.Label(L.lbl_no_selection, styles.status_err));

    var metaStr = 'region_models: ' + regionNames.map(function (r) { return r + ':' + (regionModelMap[r] || '?'); }).join(', ');
    card.add(ui.Label(metaStr, { fontSize: '9px', color: '#888', margin: '4px', fontFamily: 'monospace' }));
    card.add(ui.Label('', { margin: '4px' }));

    var br = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { stretch: 'horizontal' } });
    br.add(ui.Button({ label: L.lbl_confirm_cancel, style: styles.btn_gray, onClick: function () { showTab('regions'); } }));
    br.add(ui.Button({ label: L.lbl_btn_export, style: styles.btn_green, onClick: function () { showPrePopup(fullName); }, disabled: !hasAll || regionNames.length === 0 }));
    card.add(br);
    panel_body.add(card);
}

// ─── PRE-POPUP ──────────────────────────────────────────────────────────────

function showPrePopup(fullName) {
    panel_body.clear();
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.pre_popup_bg });
    card.add(ui.Label('⚠ ' + L.lbl_pre_popup_title, { fontSize: '14px', fontWeight: 'bold', color: '#cc8800', margin: '4px' }));
    card.add(ui.Label(L.lbl_pre_popup_body, { fontSize: '12px', color: '#333', margin: '4px 0px 0px 0px' }));
    card.add(ui.Label('FILTERED/' + fullName + '/' + currentPeriodKey, { fontSize: '12px', fontWeight: 'bold', fontFamily: 'monospace', color: '#1a73e8', margin: '2px 0px', padding: '4px', backgroundColor: '#fff' }));
    card.add(ui.Label(L.lbl_pre_popup_warn, { fontSize: '10px', color: '#888', margin: '6px 0px' }));
    var br = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { stretch: 'horizontal', margin: '6px 0px 0px 0px' } });
    br.add(ui.Button({ label: L.lbl_confirm_cancel, style: styles.btn_gray, onClick: function () { showTab('confirm'); } }));
    br.add(ui.Button({ label: L.lbl_pre_popup_continue, style: styles.btn_green, onClick: function () { executeExport(); } }));
    card.add(br);
    panel_body.add(card);
}

// ─── EXPORT ──────────────────────────────────────────────────────────────────

function executeExport() {
    panel_body.clear();
    panel_body.add(ui.Label(L.lbl_exporting, { fontSize: '12px', color: '#1a73e8', margin: '8px' }));

    var fullName = collectionName + '-ft00';
    var destPath = CLASSIFICATIONS_ROOT + 'FILTERED/' + fullName;
    ensureFolder('FILTERED/' + fullName);

    var regionNames = Object.keys(regionModelMap).filter(function (r) { return !!regionModelMap[r]; });
    if (regionNames.length === 0) { print('Nenhuma regiao configurada.'); return; }

    var nationalImg = ee.Image(0).rename('probability');
    var doyImg = ee.Image(0).rename('dayOfYear');
    var modelList = [];

    regionNames.forEach(function (regionName) {
        var modelId = regionModelMap[regionName];
        modelList.push(regionName + ':' + modelId);
        var assets = availableModels[currentPeriodKey] && availableModels[currentPeriodKey][regionName];
        if (!assets) return;
        var found = null;
        for (var i = 0; i < assets.length; i++) { if (assets[i].modelId === modelId) { found = assets[i]; break; } }
        if (!found) return;
        var regionMask = ee.Image(0).paint(REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName)), 1);
        var src = ee.Image(found.assetId);
        nationalImg = nationalImg.where(regionMask.eq(1), src.select(0));
        doyImg = doyImg.where(regionMask.eq(1), src.select(1));
    });

    nationalImg = nationalImg.addBands(doyImg).selfMask().set({
        'region_models': modelList.join(','),
        'campaign': CAMPAIGN,
        'filter_stage': 'ft00',
        'period': currentPeriodKey,
    });

    var imgName = currentPeriodKey;
    var destAsset = destPath + '/' + imgName;

    Map.addLayer(nationalImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['#ffcccc', '#ff0000', '#660000'] }, 'National ' + currentPeriodKey, false);

    try { ee.data.getAsset(destAsset); print('Ja existe: ' + destAsset); }
    catch (e) {
        print('Exportando: ' + destAsset);
        Export.image.toAsset({ image: nationalImg.toInt16(), description: imgName.replace(/_/g, ''), assetId: destAsset, pyramidingPolicy: 'mode', region: REGIONS.geometry().bounds(), scale: SCALE, maxPixels: 1e13 });
    }

    panel_body.clear();
    panel_body.add(ui.Label(L.lbl_done, { fontSize: '13px', color: '#0f9d58', fontWeight: 'bold', margin: '8px' }));
    panel_body.add(ui.Label('FILTERED/' + fullName + '/' + imgName, { fontSize: '10px', color: '#555', fontFamily: 'monospace', margin: '2px' }));
    panel_body.add(ui.Button({ label: '<- Voltar', style: styles.btn_blue, onClick: function () { showTab('config'); } }));
}

// ─── INIT ────────────────────────────────────────────────────────────────────

buildUI();
print('M7_00 2.1 carregado. Collection: ' + collectionName);
