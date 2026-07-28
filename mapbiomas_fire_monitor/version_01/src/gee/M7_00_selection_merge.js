/********************************************
MAPBIOMAS FUEGO - MONITOR_01 - M7_00
Selecao e Merge de Classificacoes (UI)

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM
   Wallace Silva, Vera Arruda

📌 O QUE FAZ:
1. Seleciona periodo (ano/mes ou anual)
2. Visualiza mosaico min NBR do periodo
3. Lista classificacoes disponiveis por regiao
4. Permite selecionar 1+ classificacoes por regiao
5. Exporta selecoes para pasta nomeada em M7_FILTERED/

🌍 IDIOMAS: ES, PT, EN, FR, ID

🔧 CONFIGURACAO:
- Variaveis no topo: CAMPAIGN, CATALOG_ROOT, etc.
- Interface ocupa ~60% da pagina, mapa ~40%
********************************************/

// ─── CONFIGURAÇÃO GLOBAL ───────────────────────────────────────────────────
var CAMPAIGN = 'MONITOR_01';
var CATALOG_ROOT = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01';
var REGIONAL_FOLDER = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/REGIONAL';
var MOSAIC_BASE = CATALOG_ROOT + '/LIBRARY_IMAGES/SENTINEL2/MONTHLY/MINNBR';
var M7_BASE = CATALOG_ROOT + '/' + CAMPAIGN + '/LIBRARY_CLASSIFICATIONS/M7_FILTERED';
var APP_LANG = 'pt';
var SCALE = 10;
var START_YEAR = 2025;

// ─── IDIOMAS ───────────────────────────────────────────────────────────────
var L = (function () {
    var dict = {
        pt: {
            title: 'MapBiomas-Fogo | M7 — Selecao e Merge',
            tab_period: 'PERIODO',
            tab_regions: 'REGIOES',
            tab_export: 'EXPORTAR',
            lbl_year: 'Ano',
            lbl_month: 'Mes',
            lbl_annual: 'Anual',
            lbl_loading: 'Carregando...',
            lbl_no_data: 'Sem dados para o periodo selecionado.',
            lbl_region: 'Regiao',
            lbl_models: 'Modelos disponiveis',
            lbl_select_all: 'Selecionar todos',
            lbl_deselect_all: 'Limpar todos',
            lbl_folder_name: 'Nome da pasta',
            lbl_folder_placeholder: 'ex: fase_agosto_v1',
            lbl_folder_existing: 'Pastas existentes:',
            lbl_no_folder: '(nenhuma pasta existente)',
            lbl_btn_export: 'Exportar',
            lbl_confirm_title: 'Confirmar Exportacao',
            lbl_confirm_folder: 'Pasta destino',
            lbl_confirm_ok: 'Confirmar Export',
            lbl_confirm_cancel: 'Cancelar',
            lbl_status_one: '1 selecao',
            lbl_status_multi: 'selecionados — sera feito merge',
            lbl_status_none: 'nenhuma selecao',
            lbl_exporting: 'Exportando...',
            lbl_done: 'Concluido!',
            lbl_no_selection: 'Nenhuma regiao selecionada.',
            lbl_err_folder: 'Informe o nome da pasta.',
            lbl_mosaic_loading: 'Carregando mosaico...',
            lbl_class_loading: 'Carregando classificacoes...',
            lbl_geometry: 'Geometria',
        },
        es: {
            title: 'MapBiomas-Fuego | M7 — Seleccion y Merge',
            tab_period: 'PERIODO',
            tab_regions: 'REGIONES',
            tab_export: 'EXPORTAR',
            lbl_year: 'Año',
            lbl_month: 'Mes',
            lbl_annual: 'Anual',
            lbl_loading: 'Cargando...',
            lbl_no_data: 'Sin datos para el periodo seleccionado.',
            lbl_region: 'Region',
            lbl_models: 'Modelos disponibles',
            lbl_select_all: 'Seleccionar todos',
            lbl_deselect_all: 'Limpiar todos',
            lbl_folder_name: 'Nombre de la carpeta',
            lbl_folder_placeholder: 'ej: fase_agosto_v1',
            lbl_folder_existing: 'Carpetas existentes:',
            lbl_no_folder: '(ninguna carpeta existente)',
            lbl_btn_export: 'Exportar',
            lbl_confirm_title: 'Confirmar Exportacion',
            lbl_confirm_folder: 'Carpeta destino',
            lbl_confirm_ok: 'Confirmar Export',
            lbl_confirm_cancel: 'Cancelar',
            lbl_status_one: '1 seleccion',
            lbl_status_multi: 'seleccionados — se hara merge',
            lbl_status_none: 'ninguna seleccion',
            lbl_exporting: 'Exportando...',
            lbl_done: 'Completado!',
            lbl_no_selection: 'Ninguna region seleccionada.',
            lbl_err_folder: 'Informe el nombre de la carpeta.',
            lbl_mosaic_loading: 'Cargando mosaico...',
            lbl_class_loading: 'Cargando clasificaciones...',
            lbl_geometry: 'Geometria',
        },
        en: {
            title: 'MapBiomas-Fire | M7 — Selection and Merge',
            tab_period: 'PERIOD',
            tab_regions: 'REGIONS',
            tab_export: 'EXPORT',
            lbl_year: 'Year',
            lbl_month: 'Month',
            lbl_annual: 'Annual',
            lbl_loading: 'Loading...',
            lbl_no_data: 'No data for selected period.',
            lbl_region: 'Region',
            lbl_models: 'Available models',
            lbl_select_all: 'Select all',
            lbl_deselect_all: 'Deselect all',
            lbl_folder_name: 'Folder name',
            lbl_folder_placeholder: 'e.g. august_phase_v1',
            lbl_folder_existing: 'Existing folders:',
            lbl_no_folder: '(no existing folders)',
            lbl_btn_export: 'Export',
            lbl_confirm_title: 'Confirm Export',
            lbl_confirm_folder: 'Target folder',
            lbl_confirm_ok: 'Confirm Export',
            lbl_confirm_cancel: 'Cancel',
            lbl_status_one: '1 selected',
            lbl_status_multi: 'selected — merge will be performed',
            lbl_status_none: 'no selection',
            lbl_exporting: 'Exporting...',
            lbl_done: 'Done!',
            lbl_no_selection: 'No region selected.',
            lbl_err_folder: 'Enter a folder name.',
            lbl_mosaic_loading: 'Loading mosaic...',
            lbl_class_loading: 'Loading classifications...',
            lbl_geometry: 'Geometry',
        },
        fr: {
            title: 'MapBiomas-Feu | M7 — Selection et Fusion',
            tab_period: 'PERIODE',
            tab_regions: 'REGIONS',
            tab_export: 'EXPORTER',
            lbl_year: 'Annee',
            lbl_month: 'Mois',
            lbl_annual: 'Annuel',
            lbl_loading: 'Chargement...',
            lbl_no_data: 'Pas de donnees pour la periode.',
            lbl_region: 'Region',
            lbl_models: 'Modeles disponibles',
            lbl_select_all: 'Tout selectionner',
            lbl_deselect_all: 'Tout effacer',
            lbl_folder_name: 'Nom du dossier',
            lbl_folder_placeholder: 'ex: phase_aout_v1',
            lbl_folder_existing: 'Dossiers existants:',
            lbl_no_folder: '(aucun dossier existant)',
            lbl_btn_export: 'Exporter',
            lbl_confirm_title: 'Confirmer l\'exportation',
            lbl_confirm_folder: 'Dossier cible',
            lbl_confirm_ok: 'Confirmer l\'export',
            lbl_confirm_cancel: 'Annuler',
            lbl_status_one: '1 selectionne',
            lbl_status_multi: 'selectionnes — fusion sera effectuee',
            lbl_status_none: 'aucune selection',
            lbl_exporting: 'Exportation...',
            lbl_done: 'Termine!',
            lbl_no_selection: 'Aucune region selectionnee.',
            lbl_err_folder: 'Saisissez un nom de dossier.',
            lbl_mosaic_loading: 'Chargement de la mosaique...',
            lbl_class_loading: 'Chargement des classifications...',
            lbl_geometry: 'Geometrie',
        },
        id: {
            title: 'MapBiomas-Api | M7 — Seleksi dan Gabung',
            tab_period: 'PERIODE',
            tab_regions: 'WILAYAH',
            tab_export: 'EKSPOR',
            lbl_year: 'Tahun',
            lbl_month: 'Bulan',
            lbl_annual: 'Tahunan',
            lbl_loading: 'Memuat...',
            lbl_no_data: 'Tidak ada data untuk periode ini.',
            lbl_region: 'Wilayah',
            lbl_models: 'Model tersedia',
            lbl_select_all: 'Pilih semua',
            lbl_deselect_all: 'Hapus semua',
            lbl_folder_name: 'Nama folder',
            lbl_folder_placeholder: 'cth: fase_agustus_v1',
            lbl_folder_existing: 'Folder yang ada:',
            lbl_no_folder: '(tidak ada folder)',
            lbl_btn_export: 'Ekspor',
            lbl_confirm_title: 'Konfirmasi Ekspor',
            lbl_confirm_folder: 'Folder tujuan',
            lbl_confirm_ok: 'Konfirmasi Ekspor',
            lbl_confirm_cancel: 'Batal',
            lbl_status_one: '1 dipilih',
            lbl_status_multi: 'dipilih — penggabungan akan dilakukan',
            lbl_status_none: 'tidak ada pilihan',
            lbl_exporting: 'Mengekspor...',
            lbl_done: 'Selesai!',
            lbl_no_selection: 'Tidak ada wilayah dipilih.',
            lbl_err_folder: 'Masukkan nama folder.',
            lbl_mosaic_loading: 'Memuat mosaik...',
            lbl_class_loading: 'Memuat klasifikasi...',
            lbl_geometry: 'Geometri',
        },
    };
    return dict[APP_LANG] || dict['pt'];
})();

// ─── ICONES BASE64 ──────────────────────────────────────────────────────────
var ICONS = {
    eye: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAbklEQVR4nO2UQQqAIBBFn5vDqkWbLtChiyA4rTtIl67egU5gNS0S2mRQs3Cm+WBmYAaGf2QGSqQIU0IS1iBRIcMBmEopcVxKCqSVtJbSStoBmiP4UMmH8V1ASmm0Q3DPeWdVgQty8ZuyQec/mR/mAPgyf/4fK4FQAAAAAElFTkSuQmCC',
};

// ─── ESTILOS ─────────────────────────────────────────────────────────────────
var styles = {
    main_panel: { margin: '0px', padding: '4px', backgroundColor: '#ffffff', border: '0px' },
    card: { margin: '2px', padding: '4px', border: '1px solid #e0e0e0', backgroundColor: '#fcfcfc', borderRadius: '4px' },
    row: { margin: '0px', padding: '2px', stretch: 'horizontal', backgroundColor: 'ffffff00' },
    title: { margin: '2px', padding: '2px', fontSize: '13px', fontWeight: 'bold', color: '#333' },
    label: { margin: '1px', padding: '0px', fontSize: '11px', color: '#555' },
    input: { margin: '1px', padding: '2px', stretch: 'horizontal' },
    btn_blue: { margin: '2px', padding: '4px 8px', color: '#1a73e8', fontWeight: 'bold', fontSize: '11px' },
    btn_green: { margin: '2px', padding: '4px 8px', color: '#0f9d58', fontWeight: 'bold', fontSize: '11px' },
    btn_red: { margin: '2px', padding: '4px 8px', color: '#d32f2f', fontWeight: 'bold', fontSize: '11px' },
    btn_gray: { margin: '2px', padding: '4px 8px', color: '#70757a', fontWeight: 'bold', fontSize: '11px' },
    tab_active: { margin: '0px', padding: '6px 12px', border: '1px solid #1a73e8', color: '#1a73e8', fontWeight: 'bold', backgroundColor: '#e8f0fe', stretch: 'horizontal', fontSize: '12px' },
    tab_inactive: { margin: '0px', padding: '6px 12px', border: '1px solid #d3d3d3', color: '#70757a', backgroundColor: '#f1f3f4', stretch: 'horizontal', fontSize: '12px' },
    region_card: { margin: '4px 0px', padding: '6px', border: '1px solid #e8e8e8', backgroundColor: '#fafafa', borderRadius: '4px' },
    region_header: { fontSize: '13px', fontWeight: 'bold', color: '#1a73e8', margin: '2px 0px' },
    model_row: { margin: '2px 0px', padding: '2px', stretch: 'horizontal' },
    status_ok: { color: '#0f9d58', fontWeight: 'bold', fontSize: '12px' },
    status_warn: { color: '#e37400', fontWeight: 'bold', fontSize: '12px' },
    status_err: { color: '#d32f2f', fontWeight: 'bold', fontSize: '12px' },
};

// ─── PALETAS ─────────────────────────────────────────────────────────────────
var CLASS_PALETTE = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
    '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
    '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9',
    '#e6beff', '#d2f53c', '#ff46b7', '#008080', '#aa6e28',
    '#ffcce0', '#808080', '#00ffff', '#ff69b4', '#556b2f',
];

// ─── CONFIG DE PAIS ─────────────────────────────────────────────────────────
var countryConfig = {
    asset_regions: 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',
    property: 'region_nam',
    id_property: 'id_region',
};

var current_regiones = ee.FeatureCollection(countryConfig.asset_regions);

// ─── ESTADO GLOBAL ──────────────────────────────────────────────────────────
var managedLayers = {};
var regionCheckboxes = {}; // regionName -> [cb1, cb2, ...]
var regionEyeButtons = {}; // regionName -> { modelId: { btn: btn, active: bool, color: str } }
var selectedByRegion = {}; // regionName -> [modelId, ...]
var currentYear = null;
var currentMonth = null;
var currentPeriodLabel = '';
var currentMosaicAsset = null; // ee.Image do mosaico min NBR atual

var panel_root = null;
var panel_body = null;
var abas = {};
var panel_confirm = null;

// ─── FUNCOES AUXILIARES ────────────────────────────────────────────────────

function createAssetIfNotExists(assetId, type) {
    type = type || 'ImageCollection';
    try {
        ee.data.getAsset(assetId);
    } catch (e) {
        print('Criando ' + type + ':', assetId);
        ee.data.createAsset({ type: type }, assetId);
    }
}

function getDateStr(year, month) {
    if (month !== null) {
        var mm = month < 10 ? '0' + month : '' + month;
        return year + '_' + mm;
    }
    return '' + year;
}

function getPeriodLabel(year, month) {
    if (month !== null) {
        var mm = month < 10 ? '0' + month : '' + month;
        return year + '-' + mm;
    }
    return '' + year;
}

// ─── GERENCIAMENTO DE CAMADAS NO MAPA ──────────────────────────────────────

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

function removeManagedLayer(id) {
    if (managedLayers[id]) {
        Map.layers().remove(managedLayers[id]);
        delete managedLayers[id];
    }
}

function removeAllClassificationLayers() {
    Object.keys(managedLayers).forEach(function (id) {
        if (id.indexOf('class_') === 0) {
            Map.layers().remove(managedLayers[id]);
            delete managedLayers[id];
        }
    });
}

// ─── CARREGAR MOSAICO MIN NBR ──────────────────────────────────────────────

function loadMosaic(year, month) {
    var isAnnual = (month === null);
    var periodFolder = isAnnual ? 'YEARLY' : 'MONTHLY';
    var dateKey = isAnnual ? '' + year : year + '_' + ('0' + month).slice(-2);
    var mosaicBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];

    var mosaicImg = ee.Image().select();
    var anyLoaded = false;

    mosaicBands.forEach(function (b) {
        var colId = [MOSAIC_BASE, b.toLowerCase()].join('/');
        var imgName = 'image_peru_fire_sentinel2_minnbr_' + b.toLowerCase() + '_' + dateKey;
        try {
            var col = ee.ImageCollection(colId);
            var bandImg = col.filter(ee.Filter.eq('system:index', imgName)).mosaic();
            var safeImg = ee.Image(ee.Algorithms.If(
                bandImg.bandNames().size().gt(0),
                bandImg,
                ee.Image(0).rename(b.toLowerCase()).updateMask(0)
            ));
            mosaicImg = mosaicImg.addBands(safeImg.select([0], [b.toLowerCase()]), null, true);
            anyLoaded = true;
        } catch (e) {
            mosaicImg = mosaicImg.addBands(ee.Image(0).rename(b.toLowerCase()).updateMask(0), null, true);
        }
    });

    if (!anyLoaded) {
        print('Aviso: mosaico nao encontrado para ' + dateKey);
        return ee.Image().select();
    }

    currentMosaicAsset = mosaicImg;

    // Adiciona indices
    var nbr = mosaicImg.normalizedDifference(['nir', 'swir2']).rename('nbr');
    var ndvi = mosaicImg.normalizedDifference(['nir', 'red']).rename('ndvi');
    mosaicImg = mosaicImg.addBands(nbr).addBands(ndvi);

    // Layer RGB SWIR1/NIR/RED (visualizacao padrao)
    var visMosaic = { bands: ['swir1', 'nir', 'red'], min: 3, max: 40, gamma: 0.85 };
    updateManagedLayer('mosaic_minnbr', mosaicImg, visMosaic, 'Min NBR ' + dateKey);

    return mosaicImg;
}

// ─── CARREGAR CLASSIFICACOES ────────────────────────────────────────────────

function loadClassifications(year, month, callback) {
    var dateKey = getDateStr(year, month);

    ee.data.listAssets(REGIONAL_FOLDER, {}, function (collections) {
        if (!collections || !collections.assets) {
            callback({});
            return;
        }

        var modelAssets = collections.assets.filter(function (c) {
            return c.type === 'IMAGE_COLLECTION';
        });

        if (modelAssets.length === 0) {
            callback({});
            return;
        }

        var result = {};
        var pending = modelAssets.length;

        modelAssets.forEach(function (c, idx) {
            var modelId = c.id.split('/').pop();
            var colPath = REGIONAL_FOLDER + '/' + modelId;

            ee.data.listAssets(colPath, {}, function (images) {
                if (images && images.assets) {
                    images.assets.forEach(function (img) {
                        var imgName = img.id.split('/').pop();
                        // Nome esperado: {modelo}_{region}_{periodo}
                        // Ex: training_0001_selva_region3_2025_08
                        var parts = imgName.split('_');
                        if (parts.length < 3) return;

                        // Extrai o periodo (ultimos elementos _YYYY ou _YYYY_MM)
                        var imgYear, imgMonth;
                        var lastPart = parts[parts.length - 1];
                        var secondLast = parts[parts.length - 2];

                        if (lastPart.length === 4 && /^\d{4}$/.test(lastPart)) {
                            imgYear = parseInt(lastPart, 10);
                            imgMonth = null;
                        } else if (lastPart.length === 2 && secondLast.length === 4 && /^\d{4}$/.test(secondLast)) {
                            imgYear = parseInt(secondLast, 10);
                            imgMonth = parseInt(lastPart, 10);
                        } else {
                            return;
                        }

                        if (imgYear !== year) return;
                        if (month !== null && imgMonth !== month) return;

                        // Extrai regiao
                        var regionIdx = parts.indexOf('region');
                        if (regionIdx === -1) {
                            // Tenta encontrar parte com "region" no nome
                            for (var i = 0; i < parts.length; i++) {
                                if (parts[i].indexOf('region') === 0) {
                                    regionIdx = i;
                                    break;
                                }
                            }
                        }
                        if (regionIdx === -1) return;
                        var regionName = parts[regionIdx];

                        if (!result[regionName]) {
                            result[regionName] = [];
                        }

                        // Evita duplicatas
                        var alreadyIn = result[regionName].some(function (r) {
                            return r.modelId === modelId && r.assetId === img.id;
                        });
                        if (!alreadyIn) {
                            result[regionName].push({
                                modelId: modelId,
                                assetId: img.id,
                                imgName: imgName,
                                color: CLASS_PALETTE[idx % 30],
                            });
                        }
                    });
                }

                pending--;
                if (pending === 0) {
                    callback(result);
                }
            });
        });

        if (pending === 0) {
            callback(result);
        }
    });
}

// ─── UI ────────────────────────────────────────────────────────────────────

function buildUI() {
    ui.root.clear();

    // Painel principal
    panel_root = ui.Panel({
        layout: ui.Panel.Layout.flow('vertical'),
        style: { width: '580px', margin: '0px', padding: '4px', backgroundColor: '#ffffff' }
    });

    // Header
    var logo = ui.Label('MapBiomas-Fuego | M7', { fontSize: '15px', fontWeight: 'bold', color: '#d32f2f', margin: '4px' });
    var subtitle = ui.Label(L.title, { fontSize: '12px', color: '#555', margin: '2px 4px' });
    panel_root.add(logo).add(subtitle);

    // Container de abas
    var tabBar = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '4px 0px', stretch: 'horizontal' } });

    abas.btnPeriod = ui.Button({ label: L.tab_period, style: styles.tab_active, onClick: function () { showTab('period'); } });
    abas.btnRegions = ui.Button({ label: L.tab_regions, style: styles.tab_inactive, onClick: function () { showTab('regions'); } });
    abas.btnExport = ui.Button({ label: L.tab_export, style: styles.tab_inactive, onClick: function () { showTab('export'); } });

    tabBar.add(abas.btnPeriod).add(abas.btnRegions).add(abas.btnExport);
    panel_root.add(tabBar);

    // Body (conteudo da aba ativa)
    panel_body = ui.Panel({ style: { margin: '4px', padding: '4px', overflowY: 'auto', maxHeight: '600px' } });
    panel_root.add(panel_body);

    // Painel de confirmacao (inicialmente oculto)
    panel_confirm = ui.Panel({ style: { margin: '4px', padding: '8px', shown: false } });
    panel_root.add(panel_confirm);

    // Container de status
    var statusBar = ui.Label('', { fontSize: '10px', color: '#888', margin: '4px' });
    panel_root.add(statusBar);

    ui.root.add(panel_root);
    Map.setOptions('SATELLITE');

    // Inicializa com aba Periodo
    showTab('period');
    loadExistingFolders();
}

function showTab(tabName) {
    // Atualiza estilos das abas
    ['period', 'regions', 'export'].forEach(function (t) {
        var btn = abas['btn' + t.charAt(0).toUpperCase() + t.slice(1)];
        if (t === tabName) {
            btn.style = styles.tab_active;
        } else {
            btn.style = styles.tab_inactive;
        }
    });

    panel_body.clear();

    if (tabName === 'period') {
        buildPeriodTab();
    } else if (tabName === 'regions') {
        buildRegionsTab();
    } else if (tabName === 'export') {
        buildExportTab();
    }
}

// ─── ABA PERIODO ────────────────────────────────────────────────────────────

function buildPeriodTab() {
    // Determina anos disponiveis
    var today = new Date();
    var maxYear = today.getFullYear();
    var maxMonth = today.getMonth(); // Janeiro = 0 -> dezembro do ano passado eh o ultimo completo
    if (maxMonth === 0) {
        maxMonth = 12;
        maxYear--;
    } else {
        // Mes atual - 1 eh o ultimo completo
        maxMonth = maxMonth;
        // Se ainda nao tem dados do mes atual, usa o anterior
    }

    if (maxMonth < 1) {
        maxMonth = 12;
        maxYear--;
    }

    var years = [];
    for (var y = START_YEAR; y <= maxYear; y++) {
        years.push({ label: '' + y, value: y });
    }
    years.reverse();

    var months = [];
    for (var m = maxMonth; m >= 1; m--) {
        var mm = m < 10 ? '0' + m : '' + m;
        months.push({ label: mm, value: m });
    }

    var ddYear = ui.Select({ items: years.map(function (y) { return y.label; }), value: '' + maxYear, style: styles.input });
    var ddMonth = ui.Select({ items: months.map(function (m) { return m.label; }), value: months[0].label, style: styles.input });
    var chkAnnual = ui.Checkbox({ label: L.lbl_annual, value: false, style: { margin: '4px' } });

    currentYear = maxYear;
    currentMonth = months[0].value;

    var lblYear = ui.Label(L.lbl_year, styles.label);
    var lblMonth = ui.Label(L.lbl_month, styles.label);

    var rowYear = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [lblYear, ddYear] });
    var rowMonth = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [lblMonth, ddMonth] });
    var rowAnnual = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row, widgets: [chkAnnual] });

    ddMonth.style().set('shown', true);
    ddMonth.setDisabled(false);

    chkAnnual.onChange(function (v) {
        if (v) {
            ddMonth.style().set('shown', false);
            ddMonth.setDisabled(true);
            currentMonth = null;
        } else {
            ddMonth.style().set('shown', true);
            ddMonth.setDisabled(false);
            currentMonth = parseInt(ddMonth.getValue(), 10);
        }
        refreshAll();
    });

    ddYear.onChange(function (v) {
        currentYear = parseInt(v, 10);
        refreshAll();
    });

    ddMonth.onChange(function (v) {
        currentMonth = parseInt(v, 10);
        if (!chkAnnual.getValue()) {
            refreshAll();
        }
    });

    var btnRefresh = ui.Button({ label: 'Carregar', style: styles.btn_blue, onClick: refreshAll });

    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });
    card.add(rowYear).add(rowMonth).add(rowAnnual).add(btnRefresh);
    panel_body.add(card);

    // Carrega automaticamente na primeira vez
    refreshAll();
}

function refreshAll() {
    removeAllClassificationLayers();
    selectedByRegion = {};
    regionCheckboxes = {};
    regionEyeButtons = {};

    currentPeriodLabel = getPeriodLabel(currentYear, currentMonth);
    var statusLabel = ui.Label(L.lbl_mosaic_loading + ' ' + currentPeriodLabel, { fontSize: '10px', color: '#888' });

    loadMosaic(currentYear, currentMonth);

    panel_body.clear();
    panel_body.add(statusLabel);

    loadClassifications(currentYear, currentMonth, function (classifications) {
        panel_body.clear();
        buildPeriodTab(); // Reconstroi aba periodo com dados carregados
        showTab('period');
    });
}

// ─── ABA REGIOES ────────────────────────────────────────────────────────────

function buildRegionsTab() {
    if (!currentYear) {
        panel_body.add(ui.Label(L.lbl_no_data, { color: '#888' }));
        return;
    }

    panel_body.add(ui.Label(L.lbl_class_loading, { fontSize: '10px', color: '#888' }));

    loadClassifications(currentYear, currentMonth, function (classifications) {
        panel_body.clear();
        var regionNames = Object.keys(classifications).sort();

        if (regionNames.length === 0) {
            panel_body.add(ui.Label(L.lbl_no_data + ' (' + currentPeriodLabel + ')', { color: '#d32f2f', fontSize: '12px', margin: '10px' }));
            return;
        }

        // Painel scrollavel
        var scrollPanel = ui.Panel({ style: { overflowY: 'auto', maxHeight: '520px', margin: '2px', padding: '2px' } });

        // Header com botoes globais
        var headerRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '2px', padding: '4px', stretch: 'horizontal' } });
        var btnAll = ui.Button({ label: L.lbl_select_all, style: styles.btn_blue, onClick: function () { toggleAllRegions(true); } });
        var btnNone = ui.Button({ label: L.lbl_deselect_all, style: styles.btn_gray, onClick: function () { toggleAllRegions(false); } });
        headerRow.add(btnAll).add(btnNone);
        scrollPanel.add(headerRow);

        regionCheckboxes = {};
        regionEyeButtons = {};
        if (!selectedByRegion) selectedByRegion = {};

        regionNames.forEach(function (regionName, regionIdx) {
            var models = classifications[regionName].sort(function (a, b) {
                return a.modelId.localeCompare(b.modelId);
            });

            // Card da regiao
            var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.region_card });

            // Header da regiao
            var regionLabel = ui.Label('Region ' + regionName.replace('region', ''), styles.region_header);
            card.add(regionLabel);

            regionCheckboxes[regionName] = [];
            regionEyeButtons[regionName] = {};
            if (!selectedByRegion[regionName]) selectedByRegion[regionName] = [];

            models.forEach(function (m) {
                var cb = ui.Checkbox({
                    label: m.modelId,
                    value: selectedByRegion[regionName].indexOf(m.modelId) !== -1,
                    style: { fontSize: '10px', margin: '1px 4px', stretch: 'horizontal' }
                });
                regionCheckboxes[regionName].push({ cb: cb, modelId: m.modelId });

                cb.onChange(function (v) {
                    if (v) {
                        if (selectedByRegion[regionName].indexOf(m.modelId) === -1) {
                            selectedByRegion[regionName].push(m.modelId);
                        }
                    } else {
                        var idx = selectedByRegion[regionName].indexOf(m.modelId);
                        if (idx !== -1) selectedByRegion[regionName].splice(idx, 1);
                        // Remove layer se estiver ativa
                        removeClassificationLayer(regionName, m.modelId);
                    }
                });

                // Botao olho
                var eyeActive = false;
                var eyeBtn = ui.Button({
                    label: ' o ',
                    style: styles.btn_gray,
                    onClick: function () {
                        eyeActive = !eyeActive;
                        if (eyeActive) {
                            addClassificationLayer(regionName, m);
                            this.style = styles.btn_blue;
                            this.setLabel(' - ');
                        } else {
                            removeClassificationLayer(regionName, m.modelId);
                            this.style = styles.btn_gray;
                            this.setLabel(' o ');
                        }
                    }
                });
                eyeBtn.style = styles.btn_gray;
                regionEyeButtons[regionName][m.modelId] = { btn: eyeBtn, active: false, model: m };

                var row = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.model_row, widgets: [cb, eyeBtn] });
                card.add(row);
            });

            scrollPanel.add(card);
        });

        panel_body.add(scrollPanel);
    });
}

function toggleAllRegions(select) {
    Object.keys(regionCheckboxes).forEach(function (regionName) {
        regionCheckboxes[regionName].forEach(function (item) {
            item.cb.setValue(select);
        });
    });
}

function addClassificationLayer(regionName, model) {
    var layerId = 'class_' + regionName + '_' + model.modelId;
    var img = ee.Image(model.assetId);

    // Carrega a banda de probabilidade (banda 0) e converte para 0-100
    var probBand = img.select(0).divide(10).toByte();

    updateManagedLayer(layerId, probBand.selfMask(), {
        min: 0, max: 100,
        palette: ['#ffcccc', '#ff6666', '#cc0000', '#660000']
    }, model.modelId + ' | ' + regionName);
}

function removeClassificationLayer(regionName, modelId) {
    var layerId = 'class_' + regionName + '_' + modelId;
    removeManagedLayer(layerId);

    if (regionEyeButtons[regionName] && regionEyeButtons[regionName][modelId]) {
        regionEyeButtons[regionName][modelId].active = false;
        regionEyeButtons[regionName][modelId].btn.style = styles.btn_gray;
        regionEyeButtons[regionName][modelId].btn.setLabel(' o ');
    }
}

// ─── ABA EXPORTAR ───────────────────────────────────────────────────────────

function buildExportTab() {
    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });

    card.add(ui.Label(L.lbl_folder_name, styles.label));

    // Campo de texto para nome da pasta
    var txtFolder = ui.Textbox({
        placeholder: L.lbl_folder_placeholder,
        value: '',
        style: { stretch: 'horizontal', margin: '2px', padding: '4px', fontSize: '12px' }
    });
    card.add(txtFolder);

    // Sugestoes de pastas existentes
    card.add(ui.Label(L.lbl_folder_existing, { fontSize: '10px', color: '#888', margin: '4px 2px 0px 2px' }));

    var ddExisting = ui.Select({
        items: [],
        value: null,
        style: { stretch: 'horizontal', margin: '2px' },
        disabled: true
    });

    loadExistingFoldersDropdown(ddExisting);
    ddExisting.onChange(function (v) {
        if (v && v !== '') {
            txtFolder.setValue(v);
        }
    });
    card.add(ddExisting);

    // Botao Exportar
    var btnExport = ui.Button({
        label: L.lbl_btn_export,
        style: styles.btn_green,
        onClick: function () {
            var folderName = txtFolder.getValue().trim();
            if (!folderName) {
                print(L.lbl_err_folder);
                return;
            }
            showConfirmation(folderName);
        }
    });
    card.add(btnExport);

    panel_body.add(card);
}

// ─── CARREGAR PASTAS EXISTENTES ─────────────────────────────────────────────

function loadExistingFolders() {
    // Tenta listar pastas em M7_FILTERED
    try {
        ee.data.listAssets(M7_BASE, {}, function (result) {
            if (result && result.assets) {
                var folders = result.assets
                    .filter(function (a) { return a.type === 'IMAGE_COLLECTION'; })
                    .map(function (a) { return a.id.split('/').pop(); })
                    .sort();
                // Armazena para uso futuro
                window._m7ExistingFolders = folders;
            } else {
                window._m7ExistingFolders = [];
            }
        });
    } catch (e) {
        window._m7ExistingFolders = [];
    }
}

function loadExistingFoldersDropdown(dd) {
    var folders = window._m7ExistingFolders || [];
    if (folders.length === 0) {
        dd.items().reset([L.lbl_no_folder]);
        dd.setDisabled(true);
    } else {
        dd.items().reset(folders);
        dd.setDisabled(false);
    }
}

// ─── TELA DE CONFIRMACAO ───────────────────────────────────────────────────

function showConfirmation(folderName) {
    panel_body.style().set('shown', false);
    panel_confirm.clear();
    panel_confirm.style().set('shown', true);

    var card = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.card });

    // Titulo
    card.add(ui.Label(L.lbl_confirm_title, { fontSize: '15px', fontWeight: 'bold', color: '#333', margin: '4px' }));
    card.add(ui.Label(L.lbl_confirm_folder + ': ' + folderName, { fontSize: '12px', color: '#1a73e8', fontWeight: 'bold', margin: '4px' }));

    var hasSelection = false;
    var hasMulti = false;
    var hasEmpty = false;

    // Lista regioes e status
    var regionNames = Object.keys(selectedByRegion).sort();
    if (regionNames.length === 0) {
        card.add(ui.Label(L.lbl_no_selection, styles.status_err));
    } else {
        regionNames.forEach(function (regionName) {
            var selected = selectedByRegion[regionName] || [];
            var count = selected.length;
            var statusLabel;
            var statusStyle;

            if (count === 0) {
                statusLabel = L.lbl_status_none;
                statusStyle = styles.status_err;
                hasEmpty = true;
            } else if (count === 1) {
                statusLabel = L.lbl_status_one;
                statusStyle = styles.status_ok;
                hasSelection = true;
            } else {
                statusLabel = count + ' ' + L.lbl_status_multi;
                statusStyle = styles.status_warn;
                hasSelection = true;
                hasMulti = true;
            }

            var row = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
            var label = ui.Label('Region ' + regionName.replace('region', '') + ': ' + selected.join(', '), { fontSize: '11px', margin: '2px' });
            var status = ui.Label(statusLabel, statusStyle);
            row.add(label).add(status);
            card.add(row);
        });
    }

    card.add(ui.Label('', { margin: '4px' }));

    // Botoes
    var btnRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { stretch: 'horizontal', margin: '8px 0px' } });

    var btnCancel = ui.Button({
        label: L.lbl_confirm_cancel,
        style: styles.btn_gray,
        onClick: function () {
            panel_confirm.style().set('shown', false);
            panel_body.style().set('shown', true);
        }
    });

    var btnConfirm = ui.Button({
        label: L.lbl_confirm_ok,
        style: styles.btn_green,
        onClick: function () {
            executeExport(folderName);
        }
    });

    if (!hasSelection) {
        btnConfirm.setDisabled(true);
    }

    btnRow.add(btnCancel).add(btnConfirm);
    card.add(btnRow);

    panel_confirm.add(card);
}

// ─── EXECUTAR EXPORT ───────────────────────────────────────────────────────

function executeExport(folderName) {
    panel_confirm.clear();
    panel_confirm.add(ui.Label(L.lbl_exporting, { fontSize: '12px', color: '#1a73e8', margin: '8px' }));

    var targetFolder = M7_BASE + '/' + folderName;
    createAssetIfNotExists(targetFolder);

    var totalJobs = 0;
    var regionNames = Object.keys(selectedByRegion).sort();

    regionNames.forEach(function (regionName) {
        var selected = selectedByRegion[regionName] || [];
        if (selected.length === 0) return;

        // Para cada selecao, copia o asset para a pasta destino
        selected.forEach(function (modelId) {
            // Encontra o assetId correspondente
            var assetId = null;
            var imgName = null;
            if (regionEyeButtons[regionName] && regionEyeButtons[regionName][modelId]) {
                var m = regionEyeButtons[regionName][modelId].model;
                assetId = m.assetId;
                imgName = m.imgName;
            }

            if (!assetId) return;

            var destAsset = targetFolder + '/' + imgName;

            try {
                // Verifica se ja existe
                ee.data.getAsset(destAsset);
                print('  Ja existe: ' + destAsset);
            } catch (e) {
                totalJobs++;
                print('  Exportando: ' + assetId + ' -> ' + destAsset);

                // Carrega a imagem e re-exporta para a nova pasta
                var img = ee.Image(assetId);
                Export.image.toAsset({
                    image: img,
                    description: imgName.replace(/\./g, '_').substring(0, 80),
                    assetId: destAsset,
                    pyramidingPolicy: 'mode',
                    scale: SCALE,
                    maxPixels: 1e13,
                });
            }
        });
    });

    panel_confirm.clear();
    panel_confirm.add(ui.Label(L.lbl_done + ' (' + totalJobs + ' tarefas)', { fontSize: '13px', color: '#0f9d58', fontWeight: 'bold', margin: '8px' }));

    var btnBack = ui.Button({
        label: '<- Voltar',
        style: styles.btn_blue,
        onClick: function () {
            panel_confirm.style().set('shown', false);
            panel_body.style().set('shown', true);
        }
    });
    panel_confirm.add(btnBack);

    // Atualiza pastas existentes
    loadExistingFolders();
}

// ─── INICIALIZACAO ─────────────────────────────────────────────────────────

buildUI();
Map.centerObject(current_regiones);
Map.addLayer(current_regiones.style({ color: 'ffffff', fillColor: '00000000', width: 1 }), {}, 'Regions');
print('M7_00 — Selecao e Merge carregado.');
print('Periodo: ' + currentPeriodLabel);
