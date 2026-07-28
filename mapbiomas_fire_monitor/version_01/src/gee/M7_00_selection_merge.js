/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M7_00
Selection, Merge and Export (UI)

📅 DATA: julho 2026
🏷️ VERSAO: 2.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Formulario M0-like: campanha, sensor, mosaico, periodicidade, versao
2. Seleciona periodo e visualiza mosaico min NBR
3. Para cada regiao, escolhe qual modelo DNN usar
4. Compõe imagem nacional por periodo (todas as regioes colapsadas)
5. Exporta para FILTERED/{collection_name}-ft00/{period}

🌍 IDIOMAS: pt, es, en, fr, id

🔧 ESTRUTURA DE SAIDA:
  FILTERED/{campanha}-{sensor}_{mosaico}_{periodicidade}_{versao}-ft00/{periodo}
  Ex: FILTERED/monitor_01-sentinel2_minnbr_monthly_01-ft00/2025_08
********************************************/

// ─── CONFIGURAÇÃO GLOBAL ───────────────────────────────────────────────────
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONS = ee.FeatureCollection('projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1');
var REGION_PROPERTY = 'region_nam';
var MOSAIC_SENSORS = { sentinel2: 'SENTINEL2', landsat: 'LANDSAT' };
var MOSAIC_METHODS = { minnbr: 'MINNBR', minnbr_buffer: 'MINNBR_BUFFER', median: 'MEDIAN', minndvi: 'MINNDVI' };
var SCALE = 10;
var START_YEAR = 2025;
var APP_LANG = 'pt';

// ─── IDIOMAS ───────────────────────────────────────────────────────────────
var L = (function () {
    var dict = {
        pt: {
            title: 'MapBiomas-Fogo | M7 — Selecao e Export',
            config: 'CONFIG',
            period: 'PERIODO',
            regions: 'REGIOES',
            confirm: 'CONFIRMAR',
            lbl_campaign: 'Campanha',
            lbl_sensor: 'Sensor',
            lbl_mosaic: 'Mosaico',
            lbl_periodicity: 'Periodicidade',
            lbl_version: 'Versao',
            lbl_year: 'Ano',
            lbl_month: 'Mes',
            lbl_annual: 'Anual',
            lbl_loading: 'Carregando...',
            lbl_no_data: 'Sem dados para o periodo selecionado.',
            lbl_region: 'Regiao',
            lbl_models: 'Modelos disponiveis',
            lbl_select_all: 'Selecionar todos',
            lbl_deselect_all: 'Limpar todos',
            lbl_new_collection: 'Nova colecao',
            lbl_add_existing: 'Adicionar a existente',
            lbl_collection_name: 'Nome da colecao',
            lbl_btn_export: 'Exportar',
            lbl_confirm_title: 'Confirmar Exportacao',
            lbl_confirm_ok: 'Confirmar',
            lbl_confirm_cancel: 'Cancelar',
            lbl_status_one: '1 modelo selecionado',
            lbl_status_none: 'nenhum modelo',
            lbl_exporting: 'Exportando...',
            lbl_done: 'Concluido!',
            lbl_no_selection: 'Nenhuma regiao configurada.',
            lbl_mosaic_loading: 'Carregando mosaico...',
            lbl_class_loading: 'Carregando classificacoes...',
            lbl_gen_name: 'Nome gerado',
            lbl_error_no_region_model: 'Selecione ao menos 1 modelo por regiao.',
        },
        es: {
            title: 'MapBiomas-Fuego | M7 — Seleccion y Export',
            config: 'CONFIG',
            period: 'PERIODO',
            regions: 'REGIONES',
            confirm: 'CONFIRMAR',
            lbl_campaign: 'Campana',
            lbl_sensor: 'Sensor',
            lbl_mosaic: 'Mosaico',
            lbl_periodicity: 'Periodicidad',
            lbl_version: 'Version',
            lbl_year: 'Ano',
            lbl_month: 'Mes',
            lbl_annual: 'Anual',
            lbl_loading: 'Cargando...',
            lbl_no_data: 'Sin datos para el periodo.',
            lbl_region: 'Region',
            lbl_models: 'Modelos disponibles',
            lbl_select_all: 'Seleccionar todos',
            lbl_deselect_all: 'Limpiar todos',
            lbl_new_collection: 'Nueva coleccion',
            lbl_add_existing: 'Agregar a existente',
            lbl_collection_name: 'Nombre de coleccion',
            lbl_btn_export: 'Exportar',
            lbl_confirm_title: 'Confirmar Exportacion',
            lbl_confirm_ok: 'Confirmar',
            lbl_confirm_cancel: 'Cancelar',
            lbl_status_one: '1 modelo seleccionado',
            lbl_status_none: 'ningun modelo',
            lbl_exporting: 'Exportando...',
            lbl_done: 'Completado!',
            lbl_no_selection: 'Ninguna region configurada.',
            lbl_mosaic_loading: 'Cargando mosaico...',
            lbl_class_loading: 'Cargando clasificaciones...',
            lbl_gen_name: 'Nombre generado',
            lbl_error_no_region_model: 'Seleccione al menos 1 modelo por region.',
        },
        en: {
            title: 'MapBiomas-Fire | M7 — Selection and Export',
            config: 'CONFIG',
            period: 'PERIOD',
            regions: 'REGIONS',
            confirm: 'CONFIRM',
            lbl_campaign: 'Campaign',
            lbl_sensor: 'Sensor',
            lbl_mosaic: 'Mosaic',
            lbl_periodicity: 'Periodicity',
            lbl_version: 'Version',
            lbl_year: 'Year',
            lbl_month: 'Month',
            lbl_annual: 'Annual',
            lbl_loading: 'Loading...',
            lbl_no_data: 'No data for selected period.',
            lbl_region: 'Region',
            lbl_models: 'Available models',
            lbl_select_all: 'Select all',
            lbl_deselect_all: 'Clear all',
            lbl_new_collection: 'New collection',
            lbl_add_existing: 'Add to existing',
            lbl_collection_name: 'Collection name',
            lbl_btn_export: 'Export',
            lbl_confirm_title: 'Confirm Export',
            lbl_confirm_ok: 'Confirm',
            lbl_confirm_cancel: 'Cancel',
            lbl_status_one: '1 model selected',
            lbl_status_none: 'no model',
            lbl_exporting: 'Exporting...',
            lbl_done: 'Done!',
            lbl_no_selection: 'No region configured.',
            lbl_mosaic_loading: 'Loading mosaic...',
            lbl_class_loading: 'Loading classifications...',
            lbl_gen_name: 'Generated name',
            lbl_error_no_region_model: 'Select at least 1 model per region.',
        },
        fr: {
            title: 'MapBiomas-Feu | M7 — Selection et Export',
            config: 'CONFIG',
            period: 'PERIODE',
            regions: 'REGIONS',
            confirm: 'CONFIRMER',
            lbl_campaign: 'Campagne',
            lbl_sensor: 'Capteur',
            lbl_mosaic: 'Mosaique',
            lbl_periodicity: 'Periodicite',
            lbl_version: 'Version',
            lbl_year: 'Annee',
            lbl_month: 'Mois',
            lbl_annual: 'Annuel',
            lbl_loading: 'Chargement...',
            lbl_no_data: 'Pas de donnees.',
            lbl_region: 'Region',
            lbl_models: 'Modeles disponibles',
            lbl_select_all: 'Tout selectionner',
            lbl_deselect_all: 'Tout effacer',
            lbl_new_collection: 'Nouvelle collection',
            lbl_add_existing: 'Ajouter a existante',
            lbl_collection_name: 'Nom de la collection',
            lbl_btn_export: 'Exporter',
            lbl_confirm_title: 'Confirmer l\'exportation',
            lbl_confirm_ok: 'Confirmer',
            lbl_confirm_cancel: 'Annuler',
            lbl_status_one: '1 modele selectionne',
            lbl_status_none: 'aucun modele',
            lbl_exporting: 'Exportation...',
            lbl_done: 'Termine!',
            lbl_no_selection: 'Aucune region configuree.',
            lbl_mosaic_loading: 'Chargement mosaique...',
            lbl_class_loading: 'Chargement classifications...',
            lbl_gen_name: 'Nom genere',
            lbl_error_no_region_model: 'Selectionnez au moins 1 modele par region.',
        },
        id: {
            title: 'MapBiomas-Api | M7 — Seleksi dan Ekspor',
            config: 'KONFIG',
            period: 'PERIODE',
            regions: 'WILAYAH',
            confirm: 'KONFIRMASI',
            lbl_campaign: 'Kampanye',
            lbl_sensor: 'Sensor',
            lbl_mosaic: 'Mosaik',
            lbl_periodicity: 'Periodisitas',
            lbl_version: 'Versi',
            lbl_year: 'Tahun',
            lbl_month: 'Bulan',
            lbl_annual: 'Tahunan',
            lbl_loading: 'Memuat...',
            lbl_no_data: 'Tidak ada data.',
            lbl_region: 'Wilayah',
            lbl_models: 'Model tersedia',
            lbl_select_all: 'Pilih semua',
            lbl_deselect_all: 'Hapus semua',
            lbl_new_collection: 'Koleksi baru',
            lbl_add_existing: 'Tambah ke yang ada',
            lbl_collection_name: 'Nama koleksi',
            lbl_btn_export: 'Ekspor',
            lbl_confirm_title: 'Konfirmasi Ekspor',
            lbl_confirm_ok: 'Konfirmasi',
            lbl_confirm_cancel: 'Batal',
            lbl_status_one: '1 model dipilih',
            lbl_status_none: 'tidak ada model',
            lbl_exporting: 'Mengekspor...',
            lbl_done: 'Selesai!',
            lbl_no_selection: 'Tidak ada wilayah dikonfigurasi.',
            lbl_mosaic_loading: 'Memuat mosaik...',
            lbl_class_loading: 'Memuat klasifikasi...',
            lbl_gen_name: 'Nama dibuat',
            lbl_error_no_region_model: 'Pilih minimal 1 model per wilayah.',
        },
    };
    return dict[APP_LANG] || dict['pt'];
})();

// ─── ESTILOS ─────────────────────────────────────────────────────────────────
var styles = {
    main_panel: { margin: '0px', padding: '4px', backgroundColor: '#ffffff' },
    card: { margin: '2px', padding: '4px', border: '1px solid #e0e0e0', backgroundColor: '#fcfcfc', borderRadius: '4px' },
    row: { margin: '0px', padding: '2px', stretch: 'horizontal' },
    title: { margin: '2px', padding: '2px', fontSize: '13px', fontWeight: 'bold', color: '#333' },
    label: { margin: '1px', padding: '0px', fontSize: '11px', color: '#555' },
    input: { margin: '1px', padding: '2px', stretch: 'horizontal' },
    btn_blue: { margin: '2px', padding: '4px 10px', color: '#1a73e8', fontWeight: 'bold', fontSize: '11px' },
    btn_green: { margin: '2px', padding: '4px 10px', color: '#0f9d58', fontWeight: 'bold', fontSize: '11px' },
    btn_red: { margin: '2px', padding: '4px 10px', color: '#d32f2f', fontWeight: 'bold', fontSize: '11px' },
    btn_gray: { margin: '2px', padding: '4px 10px', color: '#70757a', fontWeight: 'bold', fontSize: '11px' },
    tab_active: { margin: '0px', padding: '6px 12px', border: '1px solid #1a73e8', color: '#1a73e8', fontWeight: 'bold', backgroundColor: '#e8f0fe', stretch: 'horizontal', fontSize: '12px' },
    tab_inactive: { margin: '0px', padding: '6px 12px', border: '1px solid #d3d3d3', color: '#70757a', backgroundColor: '#f1f3f4', stretch: 'horizontal', fontSize: '12px' },
    region_card: { margin: '4px 0px', padding: '6px', border: '1px solid #e0e0e0', backgroundColor: '#fafafa', borderRadius: '4px' },
    model_row: { margin: '1px 0px', padding: '2px', stretch: 'horizontal' },
    status_ok: { color: '#0f9d58', fontWeight: 'bold', fontSize: '11px' },
    status_warn: { color: '#e37400', fontWeight: 'bold', fontSize: '11px' },
    status_err: { color: '#d32f2f', fontWeight: 'bold', fontSize: '11px' },
    gen_name: { fontSize: '11px', color: '#1a73e8', fontWeight: 'bold', fontFamily: 'monospace', margin: '2px', padding: '2px', backgroundColor: '#f0f4ff', borderRadius: '3px' },
};

// ─── CLASSIFICATION PALETTE ──────────────────────────────────────────────────
var CLASS_PALETTE = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
    '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
];

// ─── ESTADO GLOBAL ──────────────────────────────────────────────────────────
var managedLayers = {};
var availableModels = {};   // period -> { regionName: [{modelId, assetId, assetName}] }
var regionModelMap = {};    // regionName -> modelId (selected, one per region)
var regionEyeState = {};    // regionName -> { active: bool, color: str }
var currentYear = null;
var currentMonth = null;
var currentPeriodKey = '';  // "YYYY_MM" or "YYYY"
var currentMosaicImg = null;
var collectionBaseName = '';  // computed: {campanha}-{sensor}_{mosaico}_{periodicidade}_{versao}
var _campaigns = [];
var _existingCollections = [];

var panel_root = null;
var panel_body = null;
var abas = {};

// ─── HELPER ──────────────────────────────────────────────────────────────────

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try { ee.data.getAsset(assetId); } catch (e) { ee.data.createAsset({ type: type }, assetId); }
}

function getDateKey(y, m) {
    return m !== null ? y + '_' + ('0' + m).slice(-2) : '' + y;
}

function computeCollectionName(campaign, sensor, mosaic, periodicity, version) {
    return (campaign + '-' + sensor + '_' + mosaic + '_' + periodicity + '_' + version).toLowerCase().replace(' ', '_');
}

// ─── MAP LAYER MANAGEMENT ───────────────────────────────────────────────────

function updateManagedLayer(id, eeObject, vis, name) {
    if (managedLayers[id]) {
        managedLayers[id].setEeObject(eeObject);
        managedLayers[id].setVisParams(vis);
        managedLayers[id].setName(name);
    } else {
        var l = ui.Map.Layer(eeObject, vis, name);
        managedLayers[id] = l;
        Map.layers().add(l);
    }
}

function removeAllClassLayers() {
    Object.keys(managedLayers).forEach(function (id) {
        if (id.indexOf('class_') === 0) {
            Map.layers().remove(managedLayers[id]);
            delete managedLayers[id];
        }
    });
}

// ─── MOSAIC ──────────────────────────────────────────────────────────────────

function loadMosaic(year, month) {
    var dateKey = getDateKey(year, month);
    var mosaicBase = CATALOG_ROOT + '/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR';
    var bands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];

    var mosaicImg = ee.Image().select();
    bands.forEach(function (b) {
        var colId = [mosaicBase, b.toLowerCase()].join('/');
        var imgName = 'image_peru_fire_sentinel2_minnbr_' + b.toLowerCase() + '_' + dateKey;
        try {
            var bandImg = ee.ImageCollection(colId).filter(ee.Filter.eq('system:index', imgName)).mosaic();
            var safe = ee.Image(ee.Algorithms.If(bandImg.bandNames().size().gt(0), bandImg, ee.Image(0).rename(b.toLowerCase()).updateMask(0)));
            mosaicImg = mosaicImg.addBands(safe.select([0], [b.toLowerCase()]), null, true);
        } catch (e) {
            mosaicImg = mosaicImg.addBands(ee.Image(0).rename(b.toLowerCase()).updateMask(0), null, true);
        }
    });

    mosaicImg = mosaicImg.addBands(mosaicImg.normalizedDifference(['nir', 'swir2']).rename('nbr'));
    updateManagedLayer('mosaic_minnbr', mosaicImg, { bands: ['swir1', 'nir', 'red'], min: 3, max: 40, gamma: 0.85 }, 'Min NBR ' + dateKey);
    currentMosaicImg = mosaicImg;
    return mosaicImg;
}

// ─── CLASSIFICATIONS ────────────────────────────────────────────────────────

function loadClassifications(year, month, callback) {
    var dateKey = getDateKey(year, month);
    var regional = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/REGIONAL';

    ee.data.listAssets(regional, {}, function (collections) {
        if (!collections || !collections.assets) { callback({}); return; }
        var modelDirs = collections.assets.filter(function (c) { return c.type === 'IMAGE_COLLECTION'; });
        if (modelDirs.length === 0) { callback({}); return; }

        var result = {};
        var pending = modelDirs.length;

        modelDirs.forEach(function (c, idx) {
            var modelId = c.id.split('/').pop();
            ee.data.listAssets(c.id, {}, function (images) {
                if (images && images.assets) {
                    images.assets.forEach(function (img) {
                        if (img.type !== 'IMAGE') return;
                        var name = img.id.split('/').pop();
                        // Extract region from name: {model}_region{N}_{period}
                        var regionIdx = name.indexOf('_region');
                        if (regionIdx === -1) return;
                        // Find region part
                        var parts = name.split('_');
                        var regionPart = null;
                        for (var i = 0; i < parts.length; i++) {
                            if (parts[i].indexOf('region') === 0) { regionPart = parts[i]; break; }
                        }
                        if (!regionPart) return;
                        // Find period part (YYYY or YYYY_MM)
                        var imgPeriod = null;
                        for (var j = parts.length - 1; j >= 0; j--) {
                            if (/^\d{4}$/.test(parts[j])) {
                                if (j + 1 < parts.length && /^\d{2}$/.test(parts[j + 1])) {
                                    imgPeriod = parts[j] + '_' + parts[j + 1];
                                } else {
                                    imgPeriod = parts[j];
                                }
                                break;
                            }
                        }
                        if (imgPeriod !== dateKey) return;
                        if (!result[regionPart]) result[regionPart] = [];
                        var already = result[regionPart].some(function (r) { return r.modelId === modelId; });
                        if (!already) {
                            result[regionPart].push({ modelId: modelId, assetId: img.id, color: CLASS_PALETTE[idx % 15] });
                        }
                    });
                }
                pending--;
                if (pending === 0) callback(result);
            });
        });
        if (pending === 0) callback(result);
    });
}

// ─── CAMPAIGNS ──────────────────────────────────────────────────────────────

function loadCampaigns(callback) {
    var base = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS';
    ee.data.listAssets(base, {}, function (result) {
        if (!result || !result.assets) { callback([]); return; }
        var camps = result.assets.filter(function (a) { return a.type === 'FOLDER'; }).map(function (a) { return a.id.split('/').pop(); });
        callback(camps);
    });
}

function loadExistingFilteredCollections(callback) {
    var base = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/FILTERED';
    ee.data.listAssets(base, {}, function (result) {
        if (!result || !result.assets) { callback([]); return; }
        var cols = result.assets.filter(function (a) { return a.type === 'IMAGE_COLLECTION'; }).map(function (a) { return a.id.split('/').pop(); });
        callback(cols);
    });
}

// ─── UI ─────────────────────────────────────────────────────────────────────

function buildUI() {
    ui.root.clear();

    panel_root = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: { width: '580px', margin: '0px', padding: '4px', backgroundColor: '#ffffff' } });

    var logo = ui.Label('MapBiomas-Fuego | M7', { fontSize: '15px', fontWeight: 'bold', color: '#d32f2f', margin: '4px' });
    var subtitle = ui.Label(L.title, { fontSize: '12px', color: '#555', margin: '2px 4px' });
    panel_root.add(logo).add(subtitle);

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

    // Campaign dropdown
    card.add(ui.Label(L.lbl_campaign, styles.label));
    var ddCampaign = ui.Select({ items: ['MONITOR_01', 'MONITOR_DEV'], value: 'MONITOR_01', style: styles.input });
    card.add(ddCampaign);

    // Sensor dropdown
    card.add(ui.Label(L.lbl_sensor, styles.label));
    var ddSensor = ui.Select({ items: ['sentinel2', 'landsat'], value: 'sentinel2', style: styles.input });
    card.add(ddSensor);

    // Mosaic dropdown
    card.add(ui.Label(L.lbl_mosaic, styles.label));
    var ddMosaic = ui.Select({ items: ['minnbr', 'minnbr_buffer', 'median', 'minndvi'], value: 'minnbr', style: styles.input });
    card.add(ddMosaic);

    // Periodicity dropdown
    card.add(ui.Label(L.lbl_periodicity, styles.label));
    var ddPeriodicity = ui.Select({ items: ['monthly', 'yearly'], value: 'monthly', style: styles.input });
    card.add(ddPeriodicity);

    // Version (auto-increment)
    card.add(ui.Label(L.lbl_version, styles.label));
    var txtVersion = ui.Textbox({ value: '01', style: { stretch: 'horizontal', margin: '2px', padding: '2px', width: '60px', fontSize: '12px' } });
    card.add(txtVersion);

    // Generated name display
    card.add(ui.Label(L.lbl_gen_name, styles.label));
    var lblGenName = ui.Label('', styles.gen_name);

    function updateGenName() {
        collectionBaseName = computeCollectionName(ddCampaign.getValue(), ddSensor.getValue(), ddMosaic.getValue(), ddPeriodicity.getValue(), txtVersion.getValue());
        lblGenName.setValue(collectionBaseName);
    }
    ddCampaign.onChange(updateGenName);
    ddSensor.onChange(updateGenName);
    ddMosaic.onChange(updateGenName);
    ddPeriodicity.onChange(updateGenName);
    txtVersion.onChange(updateGenName);
    updateGenName();
    card.add(lblGenName);

    // Action buttons
    card.add(ui.Label('', { margin: '2px' }));
    var btnRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    var btnNew = ui.Button({ label: L.lbl_new_collection, style: styles.btn_green, onClick: function () { onCreateNew(); } });
    var btnAdd = ui.Button({ label: L.lbl_add_existing, style: styles.btn_blue, onClick: function () { onAddExisting(); } });
    btnRow.add(btnNew).add(btnAdd);
    card.add(btnRow);

    panel_body.add(card);
}

function onCreateNew() {
    var destFolder = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/FILTERED/' + collectionBaseName + '-ft00';
    createAssetIfNotExists(destFolder);
    print('Colecao criada: ' + destFolder);
    showTab('period');
}

function onAddExisting() {
    // Find all ft00 collections matching this base name
    loadExistingFilteredCollections(function (cols) {
        var matching = cols.filter(function (c) {
            return c.indexOf(collectionBaseName + '-ft00') !== -1;
        });
        if (matching.length === 0) {
            print('Nenhuma colecao ft00 encontrada para ' + collectionBaseName + '. Use "Nova colecao".');
            return;
        }
        print('Colecoes ft00 existentes: ' + matching.join(', '));
        showTab('period');
    });
}

// ─── TAB: PERIOD ─────────────────────────────────────────────────────────────

function buildPeriodTab() {
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });

    var today = new Date();
    var maxY = today.getFullYear();
    var maxM = today.getMonth();
    if (maxM === 0) { maxM = 12; maxY--; }

    var years = [];
    for (var y = START_YEAR; y <= maxY; y++) years.push({ label: '' + y, value: y });
    years.reverse();

    var months = [];
    for (var m = maxM; m >= 1; m--) { var mm = m < 10 ? '0' + m : '' + m; months.push({ label: mm, value: m }); }

    var ddYear = ui.Select({ items: years.map(function (y) { return y.label; }), value: '' + maxY, style: styles.input });
    var ddMonth = ui.Select({ items: months.map(function (m) { return m.label; }), value: months[0].label, style: styles.input });

    currentYear = maxY;
    currentMonth = months[0].value;
    currentPeriodKey = getDateKey(currentYear, currentMonth);

    var rowY = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [ui.Label(L.lbl_year, styles.label), ddYear] });
    var rowM = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [ui.Label(L.lbl_month, styles.label), ddMonth] });

    ddYear.onChange(function (v) { currentYear = parseInt(v, 10); refreshPeriod(); });
    ddMonth.onChange(function (v) { currentMonth = parseInt(v, 10); refreshPeriod(); });

    var btnLoad = ui.Button({ label: 'Carregar periodo', style: styles.btn_blue, onClick: refreshPeriod });

    card.add(rowY).add(rowM).add(btnLoad);
    panel_body.add(card);

    refreshPeriod();
}

function refreshPeriod() {
    currentPeriodKey = getDateKey(currentYear, currentMonth);
    loadMosaic(currentYear, currentMonth);
    Map.centerObject(REGIONS);
    print('Periodo carregado: ' + currentPeriodKey);
}

// ─── TAB: REGIONS ────────────────────────────────────────────────────────────

function buildRegionsTab() {
    panel_body.add(ui.Label(L.lbl_class_loading + ' ' + currentPeriodKey, { fontSize: '10px', color: '#888' }));

    loadClassifications(currentYear, currentMonth, function (data) {
        availableModels = {};
        availableModels[currentPeriodKey] = data;
        panel_body.clear();

        var regionNames = Object.keys(data).sort();
        if (regionNames.length === 0) {
            panel_body.add(ui.Label(L.lbl_no_data, { color: '#d32f2f', fontSize: '12px', margin: '10px' }));
            return;
        }

        var scrollPanel = ui.Panel({ style: { margin: '2px', padding: '2px' } });

        // Select all / clear all
        var headerRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '2px', padding: '4px', stretch: 'horizontal' } });
        var btnAll = ui.Button({ label: L.lbl_select_all, style: styles.btn_blue, onClick: function () { selectFirstEachRegion(data); } });
        var btnNone = ui.Button({ label: L.lbl_deselect_all, style: styles.btn_gray, onClick: function () { clearAllRegions(); } });
        headerRow.add(btnAll).add(btnNone);
        scrollPanel.add(headerRow);

        regionNames.forEach(function (regionName, idx) {
            var models = data[regionName].sort(function (a, b) { return a.modelId.localeCompare(b.modelId); });
            var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.region_card });

            var displayName = regionName.replace('region', 'Region ');
            card.add(ui.Label(displayName, { fontSize: '13px', fontWeight: 'bold', color: '#1a73e8', margin: '2px 0px' }));

            // Auto-select first model for this region if not already set
            if (!regionModelMap[regionName] && models.length > 0) {
                regionModelMap[regionName] = models[0].modelId;
            }

            models.forEach(function (m) {
                var isSelected = (regionModelMap[regionName] === m.modelId);

                var cb = ui.Checkbox({
                    label: m.modelId,
                    value: isSelected,
                    style: { fontSize: '10px', margin: '1px 4px' }
                });
                cb.onChange(function (v) {
                    if (v) {
                        regionModelMap[regionName] = m.modelId;
                        // Uncheck other checkboxes for this region
                        updateRegionCheckboxes(regionName, m.modelId);
                    } else {
                        if (regionModelMap[regionName] === m.modelId) {
                            regionModelMap[regionName] = null;
                        }
                    }
                });

                // Store checkbox reference
                if (!window['_cb_' + regionName]) window['_cb_' + regionName] = {};
                window['_cb_' + regionName][m.modelId] = cb;

                // Eye button
                var eyeBtn = ui.Button({
                    label: ' o ',
                    style: styles.btn_gray,
                    onClick: function () {
                        var key = regionName + '_' + m.modelId;
                        if (!regionEyeState[key]) regionEyeState[key] = { active: false };
                        regionEyeState[key].active = !regionEyeState[key].active;
                        if (regionEyeState[key].active) {
                            regionEyeState[key].color = m.color;
                            var img = ee.Image(m.assetId).select(0).divide(10).toByte();
                            updateManagedLayer('class_' + key, img.selfMask(), { min: 0, max: 100, palette: ['#ffcccc', '#ff6666', '#cc0000', '#660000'] }, m.modelId + ' | ' + regionName);
                            this.style = styles.btn_blue;
                        } else {
                            if (managedLayers['class_' + key]) {
                                Map.layers().remove(managedLayers['class_' + key]);
                                delete managedLayers['class_' + key];
                            }
                            this.style = styles.btn_gray;
                        }
                    }
                });

                var row = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.model_row, widgets: [cb, eyeBtn] });
                card.add(row);
            });

            scrollPanel.add(card);
        });

        panel_body.add(scrollPanel);
    });
}

function selectFirstEachRegion(data) {
    Object.keys(data).forEach(function (regionName) {
        if (data[regionName].length > 0) {
            regionModelMap[regionName] = data[regionName][0].modelId;
        }
    });
    buildRegionsTab();
}

function clearAllRegions() {
    regionModelMap = {};
    buildRegionsTab();
}

function updateRegionCheckboxes(regionName, selectedModelId) {
    var cbs = window['_cb_' + regionName];
    if (!cbs) return;
    Object.keys(cbs).forEach(function (mid) {
        if (mid !== selectedModelId) cbs[mid].setValue(false);
    });
}

// ─── TAB: CONFIRM ────────────────────────────────────────────────────────────

function buildConfirmTab() {
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });
    var fullName = collectionBaseName + '-ft00';

    card.add(ui.Label(L.lbl_confirm_title, { fontSize: '14px', fontWeight: 'bold', color: '#333', margin: '4px' }));
    card.add(ui.Label(L.lbl_collection_name + ': ' + fullName, { fontSize: '12px', color: '#1a73e8', fontWeight: 'bold', fontFamily: 'monospace', margin: '4px' }));
    card.add(ui.Label(L.lbl_periodicity + ': ' + currentPeriodKey, { fontSize: '11px', margin: '4px' }));

    var regionNames = Object.keys(regionModelMap).sort();
    var hasAll = true;

    regionNames.forEach(function (r) {
        var m = regionModelMap[r];
        var status = m ? L.lbl_status_one + ' (' + m + ')' : L.lbl_status_none;
        var style = m ? styles.status_ok : styles.status_err;
        if (!m) hasAll = false;
        card.add(ui.Label('  ' + r.replace('region', 'Region ') + ': ' + status, style));
    });

    if (regionNames.length === 0) {
        card.add(ui.Label(L.lbl_no_selection, styles.status_err));
    }

    // Metadata preview
    var metadataStr = 'region_models: ' + regionNames.map(function (r) { return r + ':' + (regionModelMap[r] || '?'); }).join(', ');
    card.add(ui.Label(metadataStr, { fontSize: '9px', color: '#888', margin: '4px', fontFamily: 'monospace' }));

    card.add(ui.Label('', { margin: '4px' }));

    var btnRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { stretch: 'horizontal' } });
    var btnCancel = ui.Button({ label: L.lbl_confirm_cancel, style: styles.btn_gray, onClick: function () { showTab('regions'); } });
    var btnExport = ui.Button({ label: L.lbl_btn_export, style: styles.btn_green, onClick: function () { executeExport(); } });

    if (!hasAll || regionNames.length === 0) btnExport.setDisabled(true);

    btnRow.add(btnCancel).add(btnExport);
    card.add(btnRow);
    panel_body.add(card);
}

// ─── EXPORT ──────────────────────────────────────────────────────────────────

function executeExport() {
    panel_body.clear();
    panel_body.add(ui.Label(L.lbl_exporting, { fontSize: '12px', color: '#1a73e8', margin: '8px' }));

    var fullName = collectionBaseName + '-ft00';
    var destPath = CATALOG_ROOT + '/MONITOR_01/LIBRARY_CLASSIFICATIONS/FILTERED/' + fullName;
    createAssetIfNotExists(destPath);

    // Build national image: for each region, paint the selected model's classification
    var regionNames = Object.keys(regionModelMap).filter(function (r) { return !!regionModelMap[r]; });

    if (regionNames.length === 0) {
        print('Nenhuma regiao configurada.');
        return;
    }

    var nationalImg = ee.Image(0).rename('probability');
    var doyImg = ee.Image(0).rename('dayOfYear');
    var modelList = [];

    regionNames.forEach(function (regionName) {
        var modelId = regionModelMap[regionName];
        modelList.push(regionName + ':' + modelId);

        // Find the asset for this region + model + period
        var modelAssets = availableModels[currentPeriodKey] && availableModels[currentPeriodKey][regionName];
        if (!modelAssets) return;
        var modelAsset = null;
        for (var i = 0; i < modelAssets.length; i++) {
            if (modelAssets[i].modelId === modelId) { modelAsset = modelAssets[i]; break; }
        }
        if (!modelAsset) return;

        var regionGeom = REGIONS.filter(ee.Filter.eq(REGION_PROPERTY, regionName));
        var regionMask = ee.Image(0).paint(regionGeom, 1);

        var srcImg = ee.Image(modelAsset.assetId);
        var probBand = srcImg.select(0);     // probability
        var doyBand = srcImg.select(1);       // dayOfYear

        nationalImg = nationalImg.where(regionMask.eq(1), probBand);
        doyImg = doyImg.where(regionMask.eq(1), doyBand);
    });

    nationalImg = nationalImg.addBands(doyImg).selfMask();
    nationalImg = nationalImg.set({
        'region_models': modelList.join(','),
        'campaign': 'MONITOR_01',
        'filter_stage': 'ft00',
        'period': currentPeriodKey,
    });

    var imgName = currentPeriodKey;
    var destAsset = destPath + '/' + imgName;

    // Plot
    Map.addLayer(nationalImg.select('probability').selfMask(), { min: 0, max: 1000, palette: ['#ffcccc', '#ff0000', '#660000'] }, 'National ' + currentPeriodKey, false);

    try {
        ee.data.getAsset(destAsset);
        print('Ja existe: ' + destAsset);
    } catch (e) {
        print('Exportando: ' + destAsset);
        Export.image.toAsset({
            image: nationalImg.toInt16(),
            description: imgName.replace(/_/g, ''),
            assetId: destAsset,
            pyramidingPolicy: 'mode',
            region: REGIONS.geometry().bounds(),
            scale: SCALE,
            maxPixels: 1e13,
        });
    }

    panel_body.clear();
    panel_body.add(ui.Label(L.lbl_done, { fontSize: '13px', color: '#0f9d58', fontWeight: 'bold', margin: '8px' }));
    panel_body.add(ui.Label('Destino: FILTERED/' + fullName + '/' + imgName, { fontSize: '10px', color: '#555', fontFamily: 'monospace', margin: '2px' }));
    panel_body.add(ui.Label('Metadata: region_models=' + modelList.join(','), { fontSize: '9px', color: '#888', fontFamily: 'monospace', margin: '2px' }));
    panel_body.add(ui.Button({ label: '<- Voltar', style: styles.btn_blue, onClick: function () { showTab('config'); } }));
}

// ─── INIT ────────────────────────────────────────────────────────────────────

buildUI();
print('M7_00 — Selecao e Export 2.0 carregado.');
