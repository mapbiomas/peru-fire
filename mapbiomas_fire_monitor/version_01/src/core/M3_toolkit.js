/********************************************
v10: Exclusive Tool for Sample Collection and Export (Vectors)
- Ultra-Compact UI and Margins (0~1px)
- Dynamic Multi-Country (Chile, Peru...)
- Automatic region search via .aggregate_array().distinct().sort()
- Dynamic update of Destination/Source Assets
********************************************/

// ─── GLOBAL CONFIGURATION ───────────────────────────────────────────────────
var PERSONAL_TASK_FLAG = 'CATALOG';
var SAMPLING_CAMPAIGN = 'monitor_01';

// ─── LANGUAGE CONFIGURATION ─────────────────────────────────────────────────
// Change APP_LANG to switch the interface language: 'es', 'pt', 'en'
var APP_LANG = 'es';

var L = (function () {
    var dict = {
        es: {
            title: 'MapBiomas-Fuego | Monitor',
            cab_config: 'CONFIGURACION',
            cab_temporal: 'TEMPORAL',
            cab_layers: 'CAPAS',
            cab_samples: 'MUESTRAS',
            lbl_country: 'Pais',
            lbl_regions: 'Regiones',
            lbl_periodicity: 'Periodicidad',
            opt_annual: 'Anual',
            opt_monthly: 'Mensual',
            lbl_asset_mosaics: 'Mosaicos classificados',
            lbl_raw_mosaics: 'Mosaicos on the fly',
            lbl_ref_cats: 'Categorias de Referencia',
            lbl_burned: 'Area Quemada',
            lbl_hotspots: 'Focos / Buffers',
            cab_instructions: 'Como usar este modulo',
            instructions: '1. Use las herramientas de dibujo en el mapa.\n' +
                '2. Capa "fire" (rojo) = area quemada.\n' +
                '3. Capa "notFire" (azul) = area no quemada.\n' +
                '4. Complete los metadatos en la pestana EXPORTAR.\n' +
                '5. Haga clic en EXPORTAR para guardar en Asset y GCS.\n' +
                '6. Vaya a la pestana Tasks en GEE para ejecutar.',
            tab_import: 'IMPORTAR',
            tab_export: 'EXPORTAR',
            btn_load: 'Cargar',
            lbl_version: 'Sample id:',
            lbl_shortname: 'Nombre corto (opcional):',
            lbl_comment: 'Comentario (metadato):',
            lbl_date: 'Fecha representada:',
            lbl_satellites: 'Valido para satelites (opcional):',
            placeholder_date: 'Seleccionar fecha...',
            placeholder_asset: 'Elegir muestra existente...',
            placeholder_sn: 'apodo (ej: norte_amazonia)',
            placeholder_cmt: 'comentario (metadato libre)',
            btn_export: 'EXPORTAR (Asset + GCS)',
            ver_checking: 'Verificando...',
            ver_suggested: 'sugerida: ',
            ver_empty: 'asset vacio',
            task_created: 'Tareas creadas: ',
            task_hint: ' (vaya a la pestana Tasks para ejecutar)',
            err_layers: 'Faltan capas "fire" o "notFire" en el mapa.',
            err_no_sat: 'Seleccione al menos un satelite como metadato.',
            err_no_date: 'Seleccione la fecha representada.',
            lbl_stats: 'Resumen de Muestras:',
            lbl_fire: 'Fuego',
            lbl_not_fire: 'No Fuego',
            lbl_total: 'Total',
            lbl_area: 'Area (ha)',
            lbl_count: 'Cant.',
            lbl_satellites_toggle: 'Satelites',
            lbl_vis_preset: 'Visualizacion',
            opt_rgb_fire: '[SWIR1/NIR/RED] A',
            opt_rgb_coverage: '[SWIR1/NIR/RED] B',
            opt_rgb_false: '[NIR/SWIR1/RED]',
            opt_rgb_natural: '[RED/GREEN/BLUE]',
            opt_gray_nir: 'NIR',
            opt_gray_swir1: 'SWIR1',
            opt_gray_swir2: 'SWIR2',
            opt_gray_nbr: 'NBR',
            opt_gray_ndvi: 'NDVI',
            opt_rgb_swir_alt: '[SWIR2/SWIR1/NIR]',
            cab_satellites: 'Satelite',
            cab_reference: 'Referencia',
            cab_classifications: 'Clasificaciones Regionales',
            short_guide: 'Guia',
            short_import: 'Importar',
            short_export: 'Exportar',
            loading: ''
        },
        pt: {
            title: 'MapBiomas-Fogo | Monitor',
            cab_config: 'CONFIGURACAO',
            cab_temporal: 'TEMPORAL',
            cab_layers: 'CAMADAS',
            cab_samples: 'AMOSTRAS',
            lbl_country: 'Pais',
            lbl_regions: 'Regioes',
            lbl_periodicity: 'Periodicidade',
            opt_annual: 'Anual',
            opt_monthly: 'Mensal',
            lbl_asset_mosaics: 'Mosaicos classificados',
            lbl_raw_mosaics: 'Mosaicos on the fly',
            lbl_ref_cats: 'Categorias de Referencia',
            lbl_burned: 'Area Queimada',
            lbl_hotspots: 'Focos / Buffers',
            cab_instructions: 'Como usar este modulo',
            instructions: '1. Use as ferramentas de desenho no mapa.\n' +
                '2. Camada "fire" (vermelho) = area queimada.\n' +
                '3. Camada "notFire" (azul) = area nao queimada.\n' +
                '4. Preencha os metadados na aba EXPORTAR.\n' +
                '5. Clique em EXPORTAR para salvar no Asset e GCS.\n' +
                '6. Acesse a aba Tasks no GEE para executar.',
            tab_import: 'IMPORTAR',
            tab_export: 'EXPORTAR',
            btn_load: 'Carregar',
            lbl_version: 'Sample id:',
            lbl_shortname: 'Shortname (opcional):',
            lbl_comment: 'Comentario (metadado):',
            lbl_date: 'Data representada:',
            lbl_satellites: 'Valido para os satelites (opcional):',
            placeholder_date: 'Selecionar data...',
            placeholder_asset: 'Escolher amostra existente...',
            placeholder_sn: 'apelido (ex: norte_amazonia)',
            placeholder_cmt: 'comentario (metadado livre)',
            btn_export: 'EXPORTAR (Asset + GCS)',
            ver_checking: 'Verificando...',
            ver_suggested: 'sugerida: ',
            ver_empty: 'asset vazio',
            task_created: 'Tasks criadas: ',
            task_hint: ' (va a aba Tasks para executar)',
            err_layers: 'Faltam camadas "fire" ou "notFire" no mapa.',
            err_no_sat: 'Selecione ao menos um satelite como metadato.',
            err_no_date: 'Selecione a data representada.',
            lbl_stats: 'Resumo das Amostras:',
            lbl_fire: 'Fogo',
            lbl_not_fire: 'Nao Fogo',
            lbl_total: 'Total',
            lbl_area: 'Area (ha)',
            lbl_count: 'Qtd.',
            lbl_satellites_toggle: 'Satelites',
            lbl_vis_preset: 'Visualizacao',
            opt_rgb_fire: '[SWIR1/NIR/RED] A',
            opt_rgb_coverage: '[SWIR1/NIR/RED] B',
            opt_rgb_false: '[NIR/SWIR1/RED]',
            opt_rgb_natural: '[RED/GREEN/BLUE]',
            opt_gray_nir: 'NIR',
            opt_gray_swir1: 'SWIR1',
            opt_gray_swir2: 'SWIR2',
            opt_gray_nbr: 'NBR',
            opt_gray_ndvi: 'NDVI',
            opt_rgb_swir_alt: '[SWIR2/SWIR1/NIR]',
            cab_satellites: 'Satelite',
            cab_reference: 'Referencia',
            cab_classifications: 'Classificacoes Regionais',
            short_guide: 'Guia',
            short_import: 'Importar',
            short_export: 'Exportar',
            loading: ''
        },
        en: {
            title: 'MapBiomas-Fire | Monitor',
            cab_config: 'CONFIGURATION',
            cab_temporal: 'TEMPORAL',
            cab_layers: 'LAYERS',
            cab_samples: 'SAMPLES',
            lbl_country: 'Country',
            lbl_regions: 'Regions',
            lbl_periodicity: 'Periodicity',
            opt_annual: 'Annual',
            opt_monthly: 'Monthly',
            lbl_asset_mosaics: 'Mosaicos classificados',
            lbl_raw_mosaics: 'Mosaicos on the fly',
            lbl_ref_cats: 'Reference Categories',
            lbl_burned: 'Burned Area',
            lbl_hotspots: 'Hotspots / Buffers',
            cab_instructions: 'How to use this module',
            instructions: '1. Use the map drawing tools.\n' +
                '2. Layer "fire" (red) = burned area.\n' +
                '3. Layer "notFire" (blue) = unburned area.\n' +
                '4. Fill in metadata in the EXPORT tab.\n' +
                '5. Click EXPORT to save to Asset and GCS.\n' +
                '6. Go to the Tasks tab in GEE to run.',
            tab_import: 'IMPORT',
            tab_export: 'EXPORT',
            btn_load: 'Load',
            lbl_version: 'Sample id:',
            lbl_shortname: 'Short name (optional):',
            lbl_comment: 'Comment (metadata):',
            lbl_date: 'Represented date:',
            lbl_satellites: 'Valid for satellites (optional):',
            placeholder_date: 'Select date...',
            placeholder_asset: 'Choose existing sample...',
            placeholder_sn: 'alias (e.g. north_amazonia)',
            placeholder_cmt: 'comment (free metadata)',
            btn_export: 'EXPORT (Asset + GCS)',
            ver_checking: 'Checking...',
            ver_suggested: 'suggested: ',
            ver_empty: 'empty asset',
            task_created: 'Tasks created: ',
            task_hint: ' (go to Tasks tab to run)',
            err_layers: 'Missing "fire" or "notFire" layers on map.',
            err_no_sat: 'Select at least one satellite as metadata.',
            err_no_date: 'Select the represented date.',
            lbl_stats: 'Sample Summary:',
            lbl_fire: 'Fire',
            lbl_not_fire: 'Not Fire',
            lbl_total: 'Total',
            lbl_area: 'Area (ha)',
            lbl_count: 'Qty.',
            lbl_satellites_toggle: 'Satellites',
            lbl_vis_preset: 'Visualization',
            opt_rgb_fire: '[SWIR1/NIR/RED] A',
            opt_rgb_coverage: '[SWIR1/NIR/RED] B',
            opt_rgb_false: '[NIR/SWIR1/RED]',
            opt_rgb_natural: '[RED/GREEN/BLUE]',
            opt_gray_nir: 'NIR',
            opt_gray_swir1: 'SWIR1',
            opt_gray_swir2: 'SWIR2',
            opt_gray_nbr: 'NBR',
            opt_gray_ndvi: 'NDVI',
            opt_rgb_swir_alt: '[SWIR2/SWIR1/NIR]',
            cab_satellites: 'Satellite',
            cab_reference: 'Reference',
            cab_classifications: 'Regional Classifications',
            short_guide: 'Guide',
            short_import: 'Import',
            short_export: 'Export',
            loading: ''
        }
    };
    return dict[APP_LANG] || dict['es'];
})();

// ─── ICON REPOSITORY ────────────────────────────────────────────────────────
// Using base64 strings for simple, self-contained UI icons
var ICONS = {
    load: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAdUlEQVR4nGNgGAWjYBSMglEwCkbBSAMMDA0Nf//+Zf7//z8DIyNjOxBnoig8DMUuKPLBUPyGog8NixMQp4EIFIDiNBB9vBSNdMAwNDTEAwMDA6Dof0SGYuC/BCh+Q5EvAMVpIPrpUDTSAEPDQ0M8MNAAoPANAOfdJAmhH1mMAAAAAElFTkSuQmCC',
    download: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAgklEQVR4nO2UOQqAMBQF5xpWFhY2FlpYeXuDHkLQwkKwEI8QCViI+5IgaAYeBAJvyA8J/IkMkGOECYGcxQoWSCv4nqBaKd1KeUcQA92J8h5I7p4iAtqdcrUX8hAfqFfKGyBAEy5QTMrV/XhoxgHy8VdVa4t+xIWHJQ8iTAtSAwN4iQH5pnQ8NtSv6QAAAABJRU5ErkJggg==",

};

Map.setOptions('SATELLITE');

// --- COUNTRY CONFIGURATIONS ---
var countryConfigs = {
    // 'Chile': {
    //   asset_regions: 'projects/mapbiomas-chile/assets/FIRE/AUXILIARY_DATA/regiones_fuego_chile_v1',
    //   asset_samples: 'projects/mapbiomas-chile/assets/FIRE/COLLECTION1/SAMPLES',
    //   property: 'region_nam'
    // },
    'Peru': {
        asset_regions: 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',
        asset_samples: 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_SAMPLES',
        bucket: 'mapbiomas-fire',
        gcs_samples: 'sudamerica/peru/CATALOG_01/LIBRARY_SAMPLES',
        property: 'region_nam'
    }
};

// Global variable to store active regions collection
var current_regiones = ee.FeatureCollection(countryConfigs['Peru'].asset_regions);

// --- VISUALIZATION SETTINGS ---
var VIS_PRESETS = {
    'fire': { bands: ['swir1', 'nir', 'red'], min: 3, max: 40 },
    'coverage': { 'bands': ['swir1', 'nir', 'red'], 'gain': [8, 6, 20], 'gamma': 0.85 },
    'false': { bands: ['nir', 'swir1', 'red'], min: 3, max: 40 },
    'swir_alt': { bands: ['swir2', 'swir1', 'nir'], min: 3, max: 40 },
    'natural': { bands: ['red', 'green', 'blue'], min: 4, max: 14, gamma: 2 },
    'nir': { bands: ['nir'], min: 16, max: 48 },
    'swir1': { bands: ['swir1'], min: 16, max: 48 },
    'swir2': { bands: ['swir2'], min: 16, max: 48 },
    'nbr': { bands: ['nbr'], min: -0.1, max: 0.5 },
    'ndvi': { bands: ['ndvi'], min: 0.1, max: 0.8 }
};

var currentVisMode = 'fire';
var visAsset = VIS_PRESETS[currentVisMode];
var visRaw = VIS_PRESETS[currentVisMode];

var managedLayers = {};
var rawCheckboxes = {};

var extraDatasets = {
    'mcd64a1': {
        name: 'MODIS Burned Area',
        vis: { min: 0, max: 1, palette: ['fc6000'] },
        build: function (start, end, bounds, year, month) {
            return ee.ImageCollection('MODIS/061/MCD64A1')
                .filterDate(start, end).filterBounds(bounds)
                .select('BurnDate').mean().gte(1).selfMask();
        }
    },
    'gabam': {
        name: 'GABAM',
        vis: { min: 0, max: 1, palette: ['b200ac'] },
        build: function (start, end, bounds, year, month) {
            return ee.ImageCollection('projects/sat-io/open-datasets/GABAM')
                .filterDate(start, end).filterBounds(bounds)
                .mosaic().selfMask();
        }
    },
    'firms': {
        name: 'FIRMS',
        vis: { min: 0, max: 1, palette: ['823b15'] },
        build: function (start, end, bounds, year, month) {
            return ee.ImageCollection('FIRMS')
                .filterDate(start, end).filterBounds(bounds)
                .select('T21').mosaic().selfMask();
        }
    },
    'fire_cci': {
        name: 'FIRE_CCI',
        vis: { min: 0, max: 1, palette: ['5149ba'] },
        build: function (start, end, bounds, year, month) {
            return ee.ImageCollection('ESA/CCI/FireCCI/5_1')
                .filterDate(start, end).filterBounds(bounds)
                .select('BurnDate').mosaic().selfMask();
        }
    },
    'peru_ref': {
        name: 'Cicatrizes Peru',
        vis: { min: 0, max: 1, palette: ['804000'] },
        build: function (start, end, bounds, year, month) {
            try {
                var img = ee.Image("projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/REFERENCES/cicatrizes_fuego_reference_2016_2024/cicatriz_fuego_" + year);
                return img.selfMask();
            } catch (e) {
                return ee.Image().select();
            }
        }
    },
    'buffer_inpe': {
        name: 'Buffer Focos INPE',
        vis: { min: 0, max: 1, palette: ['ff0000'] },
        build: function (start, end, bounds, year, month) {
            var buffer = ee.ImageCollection("projects/workspace-ipam/assets/BUFFER-DOUBLE-MONTHLY-FOCUS-OF-INPE-SULAMERICA")
                .filter(ee.Filter.eq('year', year));
            if (month) buffer = buffer.filter(ee.Filter.eq('month', month));
            return buffer.mean().selfMask();
        }
    },
    // 'buffer_inpe_inv': {
    //     name: 'Buffer Focos INPE (Invertido)',
    //     vis: { min: 0, max: 1, palette: ['000000'] },
    //     build: function (start, end, bounds, year, month) {
    //         var buffer = ee.ImageCollection("projects/workspace-ipam/assets/BUFFER-DOUBLE-MONTHLY-FOCUS-OF-INPE-SULAMERICA")
    //             .filter(ee.Filter.eq('year', year));
    //         if (month) buffer = buffer.filter(ee.Filter.eq('month', month));
    //         var bImg = buffer.mean().unmask(0);
    //         // Inverted: 1 where there is no buffer, masked where there is
    //         return ee.Image(1).updateMask(bImg.not());
    //     }
    // },
    'hotspots_inpe': {
        name: 'Hotspots INPE (Pontos)',
        vis: { color: '0f03fc' },
        build: function (start, end, bounds, year, month) {
            if (!month) return ee.Image().select();
            try {
                var assets = ee.data.listAssets('projects/mapbiomas-fire-485203/assets/DATABASE/monthly-focus-sul-america').assets;
                for (var i = 0; i < assets.length; i++) {
                    var filename = assets[i].id.split('/').slice(-1)[0];
                    if (filename.indexOf('_') > -1) {
                        var split = filename.split('_')[1].split('-');
                        if (split.length >= 2) {
                            var aYear = parseInt(split[0], 10);
                            var aMonth = parseInt(split[1], 10);
                            if (aYear === year && aMonth === month) {
                                return ee.FeatureCollection(assets[i].id).style({ color: '0f03fc', pointSize: 2 });
                            }
                        }
                    }
                }
            } catch (e) { print("Erro Hotspots:", e); }
            return ee.Image().select();
        }
    }
};

// ─── CLASSIFICAÇÕES REGIONAIS ─────────────────────────────────────────────────
var REGIONAL_FOLDER = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_CLASSIFICATIONS/REGIONAL';

var CLASS_PALETTE = [
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
    '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
    '#469990', '#dcbeff', '#9A6324', '#fffAC8', '#800000',
    '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9',
    '#e6beff', '#d2f53c', '#ff46b7', '#008080', '#e6beff',
    '#aa6e28', '#ffcce0', '#808080', '#ffe119', '#911eb4',
    '#46f0f0', '#f032e6', '#d2f53c', '#fabebe', '#008080',
    '#e6beff', '#aa6e28', '#fffAC8', '#800000', '#aaffc3',
    '#808000', '#ffd8b1', '#000075', '#a9a9a9', '#e6194b',
    '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4'
];

var PROB_PALETTE = ['#ffcccc', '#ff6666', '#cc0000', '#660000'];

var classCheckboxes = {};
var classBandCheckboxes = {};

var regionCheckboxes = {};
var layerAllRegions = ui.Map.Layer(ee.Image(), {}, 'All Regions');
var layerSelectedRegion = ui.Map.Layer(ee.Image(), {}, 'Selected Region');

// Layers are now dynamically managed via managedLayers and Map.layers().add/remove
Map.layers().add(layerAllRegions);
Map.layers().add(layerSelectedRegion);

function user_interface() {

    function getDynamicDates(period) {
        var dates = [];
        var today = new Date();
        var currentYear = today.getFullYear();
        var currentMonth = today.getMonth() + 1;

        var maxYear = currentYear;
        var maxMonth = currentMonth - 1;
        if (maxMonth === 0) { maxMonth = 12; maxYear--; }

        if (period === 'anual') {
            for (var y = 2019; y <= maxYear; y++) dates.push(y.toString());
        } else {
            for (var y = 2019; y <= maxYear; y++) {
                var mEnd = (y === maxYear) ? maxMonth : 12;
                for (var m = 1; m <= mEnd; m++) {
                    var mm = m < 10 ? '0' + m : m.toString();
                    dates.push(y + '_' + mm);
                }
            }
        }
        return dates.reverse();
    }

    // --- STYLES DICTIONARY (0~1px) ---
    var styles = {
        main_panel: { margin: '0px', padding: '1px', backgroundColor: '#ffffff', border: '1px solid #d0d0d0' },
        card: { margin: '1px', padding: '2px', border: '1px solid #e0e0e0', backgroundColor: '#fcfcfc' },
        row: { margin: '0px', padding: '0px', stretch: 'horizontal', backgroundColor: 'ffffff00' },
        title: { margin: '1px', padding: '2px', fontSize: '13px', fontWeight: 'bold', color: '#333' },
        label: { margin: '1px', padding: '0px', fontSize: '12px', color: '#555' },
        input: { margin: '1px', padding: '0px', stretch: 'horizontal' },
        btn_blue: { margin: '2px', padding: '0px', color: '#1a73e8', fontWeight: 'bold' },
        btn_green: { margin: '1px', padding: '0px', color: '#0f9d58', fontWeight: 'bold' },
        btn_red: { margin: '1px', padding: '0px', color: '#d32f2f', fontWeight: 'bold' },
        tab_active: { margin: '0px', padding: '1px', border: '1px solid #1a73e8', color: '#1a73e8', fontWeight: 'bold', backgroundColor: '#e8f0fe', stretch: 'horizontal' },
        tab_inactive: { margin: '0px', padding: '1px', border: '1px solid #d3d3d3', color: '#70757a', backgroundColor: '#f1f3f4', stretch: 'horizontal' }
    };

    var b64 = require('users/workspaceipam/packages:mapbiomas-toolkit/utils/b64');

    // --- BASE STRUCTURE ---
    var panel = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.main_panel });
    panel.style().set({ width: '350px' });
    ui.root.insert(0, panel);

    var panel_head = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.row });
    var panel_body = ui.Panel({ style: { margin: '0px', padding: '0px' } });
    panel.add(panel_head).add(panel_body);

    var logo = ui.Button({ imageUrl: b64.get('logo_mapbiomas_fuego'), style: { margin: '1px', padding: '0px' } });
    var title = ui.Label(L.title, { fontSize: '15px', fontWeight: 'bold', color: '#222', margin: '1px', stretch: 'horizontal' });
    panel_head.add(logo).add(title);

    var panel_control = ui.Panel({ style: styles.card });
    var panel_samples = ui.Panel({ style: styles.card });
    panel_body.add(panel_control);

    // ==========================================
    // GENERAL MAP / DRAWING FUNCTIONS
    // ==========================================
    var updateTimer = null;
    var lab_loading = ui.Label({ imageUrl: b64.get('load_gif'), style: { margin: '4px', shown: false } });

    function debouncedUpdateMosaic() {
        lab_loading.style().set('shown', true);
        if (updateTimer) {
            ui.util.clearTimeout(updateTimer);
        }
        updateTimer = ui.util.setTimeout(function () {
            updateMosaic();
            lab_loading.style().set('shown', false);
        }, 1000);
    }

    function getSelectedCountry() {
        var pais = 'Peru';
        if (typeof countryCheckboxes !== 'undefined') {
            Object.keys(countryCheckboxes).forEach(function (k) {
                if (countryCheckboxes[k].getValue()) pais = k;
            });
        }
        return pais;
    }

    function getSelectedPeriodicity() {
        if (typeof periodicityCheckboxes === 'undefined') return 'Mensal';
        return periodicityCheckboxes['mensal'].getValue() ? 'Mensal' : 'Anual';
    }

    function getSelectedPeriods() {
        var periods = [];
        if (typeof periodCheckboxes === 'undefined') return [];
        Object.keys(periodCheckboxes).forEach(function (k) {
            if (periodCheckboxes[k].getValue()) periods.push(k);
        });
        return periods;
    }

    function getSelectedVis() {
        var selected = [];
        if (typeof visCheckboxes === 'undefined') return [];
        Object.keys(visCheckboxes).forEach(function (k) {
            if (visCheckboxes[k].getValue()) selected.push(k);
        });
        return selected;
    }

    function getSelectedRegionNames() {
        var selected = [];
        if (typeof regionCheckboxes === 'undefined') return [];
        Object.keys(regionCheckboxes).forEach(function (k) {
            if (regionCheckboxes[k].getValue()) selected.push(k);
        });
        return selected;
    }

    function updateMosaic() {
        var checkedPeriods = getSelectedPeriods();
        var checkedVisKeys = getSelectedVis();
        var pais = getSelectedCountry().toLowerCase();

        // Base bands needed for loading
        var baseBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'dayOfYear'];

        // Lógica de Regiões Selecionadas
        var selectedNames = getSelectedRegionNames();

        var geom = current_regiones;
        if (selectedNames.length > 0) {
            geom = current_regiones.filter(ee.Filter.inList(countryConfigs[getSelectedCountry()].property, selectedNames));
        }
        var bounds = geom.geometry().bounds();
        var spatialMask = ee.Image(0).paint(geom, 1);

        var desiredLayerIds = [];

        checkedPeriods.forEach(function (dateStr) {
            var year = parseInt(dateStr.split('_')[0], 10);
            var month = dateStr.indexOf('_') !== -1 ? parseInt(dateStr.split('_')[1], 10) : null;
            var start = month ? ee.Date.fromYMD(year, month, 1) : ee.Date.fromYMD(year, 1, 1);
            var end = month ? start.advance(1, 'month') : start.advance(1, 'year');
            var folderPeriod = month ? 'MONTHLY' : 'YEARLY';
            var periodicity = month ? 'monthly' : 'yearly';

            checkedVisKeys.forEach(function (visKey) {
                var vis = VIS_PRESETS[visKey];
                var requestedBands = vis.bands;
                var visSuffix = ' [' + visKey.toUpperCase() + ']';

                // --- GESTÃO DE ASSETS (Mosaicos Oficiais) ---
                ['sentinel2', 'sentinel2_buffer'].forEach(function (s) {
                    if (assetCheckboxes[s] && assetCheckboxes[s].getValue()) {
                        var layerId = 'asset_' + s + '_' + dateStr + '_' + visKey;
                        desiredLayerIds.push(layerId);

                        var isBuffer = s.indexOf('buffer') !== -1;
                        var sensorFolder = 'SENTINEL2'; // Sensor base
                        var mosaicType = isBuffer ? 'MINNBR_BUFFER' : 'MINNBR';
                        var periodFolder = folderPeriod.toUpperCase();

                        var assetBase = 'projects/mapbiomas-peru/assets/FIRE/CATALOG_01/LIBRARY_IMAGES';
                        var imgAsset = ee.Image().select();

                        try {
                            baseBands.forEach(function (b) {
                                // Estrutura Corrigida: {base}/SENSOR/PERIOD/MOSAIC/band (lowercase)
                                var colId = [assetBase, sensorFolder, periodFolder, mosaicType, b.toLowerCase()].join('/');
                                var col = ee.ImageCollection(colId);

                                // Filtra a imagem pelo nome institucional
                                var dateKey = periodicity === 'monthly' ? year + '_' + ('0' + month).slice(-2) : year;
                                var imgName = 'image_peru_fire_sentinel2_' + mosaicType.toLowerCase() + '_' + b.toLowerCase() + '_' + dateKey;

                                // Tenta carregar a imagem (safe-load via mosaic)
                                var bandImg = col.filter(ee.Filter.eq('system:index', imgName)).mosaic();
                                
                                // Garante que a banda tenha o nome correto mesmo que esteja vazia
                                var safeImg = ee.Image(ee.Algorithms.If(
                                    bandImg.bandNames().size().gt(0),
                                    bandImg,
                                    ee.Image(0).rename(b.toLowerCase()).updateMask(0)
                                ));
                                
                                imgAsset = imgAsset.addBands(safeImg.select([0], [b.toLowerCase()]), null, true);
                            });

                            imgAsset = addIndices(imgAsset);
                            var label = (isBuffer ? 'Asset S2 Buffer - ' : 'Asset S2 - ') + dateStr + visSuffix;
                            updateManagedLayer(layerId, imgAsset.select(requestedBands).updateMask(spatialMask), vis, label);
                        } catch (e) {
                            updateManagedLayer(layerId, ee.Image().select(), {}, 'Asset ' + s + ' - ' + dateStr + ' [Err]');
                        }
                    }
                });

                // --- GESTÃO DE RAW ---
                ['sentinel2', 'landsat', 'modis', 'hls', 'planet'].forEach(function (s) {
                    if (rawCheckboxes[s] && rawCheckboxes[s].getValue()) {
                        var layerId = 'raw_' + s + '_' + dateStr + '_' + visKey;
                        desiredLayerIds.push(layerId);

                        if (s === 'planet') {
                            var planetCol = ee.ImageCollection('projects/planet-nicfi/assets/basemaps/americas')
                                .filterDate(start, end).filterBounds(bounds)
                                .map(function (img) { return img.select(['B', 'G', 'R', 'N'], ['blue', 'green', 'red', 'nir']); });

                            var planetImg = planetCol.mosaic();
                            var planetVis = { "opacity": 1, "bands": ["red", "green", "blue"], "min": 125, "max": 1858, "gamma": 1 };
                            var planetBands = ["red", "green", "blue"];

                            // Fallback for Planet if SWIR is requested
                            if (requestedBands.indexOf('swir1') === -1 && requestedBands.indexOf('swir2') === -1 && requestedBands.indexOf('nbr') === -1) {
                                planetImg = addIndices(planetImg);
                                planetVis = vis;
                                planetBands = requestedBands;
                            }

                            updateManagedLayer(layerId, planetImg.select(planetBands).updateMask(spatialMask), planetVis, 'Planet - ' + dateStr + visSuffix);
                            return;
                        }

                        var rawCol = ee.ImageCollection([]);
                        var multiplier = 100;
                        if (s === 'landsat') {
                            var sensor_logic = { '1984_1998': ['L5'], '1999_2012': ['L5', 'L7'], '2013_2021': ['L7', 'L8'], '2022_2026': ['L8', 'L9'] };
                            var current_constellation = year < 1999 ? sensor_logic['1984_1998'] : year <= 2012 ? sensor_logic['1999_2012'] : year <= 2021 ? sensor_logic['2013_2021'] : sensor_logic['2022_2026'];
                            if (current_constellation.indexOf('L9') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS89));
                            if (current_constellation.indexOf('L8') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS89));
                            if (current_constellation.indexOf('L7') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS57));
                            if (current_constellation.indexOf('L5') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS57));
                        } else if (s === 'sentinel2') {
                            rawCol = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate(start, end).filterBounds(bounds).linkCollection(ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED'), ['cs']).map(processS2);
                            multiplier = 0.01;
                        } else if (s === 'modis') {
                            rawCol = ee.ImageCollection("MODIS/061/MOD09A1") // Terra
                                // .merge(ee.ImageCollection("MODIS/061/MYD09A1")) // Aqua (comentado)
                                .filterDate(start, end).filterBounds(bounds).map(processMODIS);
                            multiplier = 0.01;
                        } else if (s === 'hls') {
                            rawCol = ee.ImageCollection("NASA/HLS/HLSS30/v002").filterDate(start, end).filterBounds(bounds).map(processHLS_S30).merge(ee.ImageCollection("NASA/HLS/HLSL30/v002").filterDate(start, end).filterBounds(bounds).map(processHLS_L30));
                        }
                        var spectral = rawCol.qualityMosaic('nbr').select(['blue', 'green', 'red', 'nir', 'swir1', 'swir2']).multiply(multiplier);
                        spectral = addIndices(spectral);
                        updateManagedLayer(layerId, spectral.select(requestedBands).updateMask(spatialMask), vis, 'Raw ' + s + ' - ' + dateStr + visSuffix);
                    }
                });
            });

            // --- GESTÃO DE REFERÊNCIA ---
            Object.keys(extraDatasets).forEach(function (key) {
                if (extraCheckboxes[key] && extraCheckboxes[key].getValue()) {
                    var layerId = 'extra_' + key + '_' + dateStr;
                    desiredLayerIds.push(layerId);
                    var extraImg = extraDatasets[key].build(start, end, bounds, year, month);
                    updateManagedLayer(layerId, extraImg.updateMask(spatialMask), extraDatasets[key].vis, extraDatasets[key].name + ' - ' + dateStr);
                }
            });

            // --- CLASSIFICAÇÕES REGIONAIS ---
            var classBandCls = classBandCheckboxes['cls'] && classBandCheckboxes['cls'].getValue();
            var classBandPrb = classBandCheckboxes['prb'] && classBandCheckboxes['prb'].getValue();
            if (classBandCls || classBandPrb) {
                var selectedRegions = getSelectedRegionNames();
                var modelList = Object.keys(classCheckboxes).sort();
                Object.keys(classCheckboxes).forEach(function (modelId) {
                    if (!classCheckboxes[modelId].getValue()) return;
                    var modelIdx = modelList.indexOf(modelId);
                    var color = CLASS_PALETTE[modelIdx % 50] || '#e6194b';
                    var col = ee.ImageCollection(REGIONAL_FOLDER + '/' + modelId);
                    selectedRegions.forEach(function (regionName) {
                        var assetName = regionName + '_' + dateStr;
                        var filtered = col.filter(ee.Filter.stringContains('system:index', regionName))
                            .filter(ee.Filter.stringContains('system:index', dateStr));
                        var img = filtered.mosaic();
                        var clsImg = img.select([0], ['classification']).byte().selfMask().updateMask(spatialMask);
                        var prbImg = img.select([1], ['probability']).multiply(100).byte().selfMask().updateMask(spatialMask);
                        if (classBandCls) {
                            var lId = 'class_' + modelId + '_' + assetName + '_cls';
                            desiredLayerIds.push(lId);
                            updateManagedLayer(lId,
                                clsImg,
                                { min: 0, max: 1, palette: ['00000000', color] },
                                modelId + ' ' + assetName);
                        }
                        if (classBandPrb) {
                            var lId = 'class_' + modelId + '_' + assetName + '_prb';
                            desiredLayerIds.push(lId);
                            updateManagedLayer(lId,
                                prbImg,
                                { min: 0, max: 100, palette: PROB_PALETTE },
                                modelId + ' prob ' + assetName);
                        }
                    });
                });
            }
        });

        // Remover camadas que não estão mais marcadas
        Object.keys(managedLayers).forEach(function (id) {
            if (desiredLayerIds.indexOf(id) === -1) {
                Map.layers().remove(managedLayers[id]);
                delete managedLayers[id];
            }
        });
    }

    function updateClassificationsDrawer() {
        drawerClassModels.panel.clear();
        classCheckboxes = {};
        var selectedNames = getSelectedRegionNames();
        if (selectedNames.length === 0) return;

        var labelLoading = ui.Label('(carregando...)', { fontSize: '10px', color: '#888' });
        drawerClassModels.panel.add(labelLoading);

        // Deffere listAssets para nao travar a UI antes do label renderizar
        ee.Number(0).evaluate(function () {
            var collections = ee.data.listAssets(REGIONAL_FOLDER);
            var modelAssets = collections ? collections.assets : [];

            if (!modelAssets || modelAssets.length === 0) {
                labelLoading.setValue('(sin modelos)');
                return;
            }

            var totalAdded = 0;
            modelAssets.forEach(function (c, idx) {
                var modelId = c.id.split('/').pop();
                var colPath = REGIONAL_FOLDER + '/' + modelId;
                var images = ee.data.listAssets(colPath);
                if (!images || !images.assets) return;

                var imageNames = images.assets.map(function (i) { return i.id.split('/').pop(); });
                var hasData = selectedNames.some(function (r) {
                    return imageNames.some(function (img) { return img.indexOf(r) !== -1; });
                });

                if (hasData) {
                    totalAdded++;
                    var chk = ui.Checkbox({
                        label: modelId,
                        value: false,
                        onChange: function () { debouncedUpdateMosaic(); },
                        style: { margin: '1px 3px', padding: '0px', fontSize: '10px', color: CLASS_PALETTE[idx % 50] }
                    });
                    classCheckboxes[modelId] = chk;
                    drawerClassModels.panel.add(chk);
                }
            });

            if (totalAdded === 0) {
                labelLoading.setValue('(sem modelos para esta regiao)');
            } else {
                labelLoading.parent().remove(labelLoading);
            }
        });
    }

    function updateManagedLayer(id, eeObject, vis, name) {
        if (managedLayers[id]) {
            managedLayers[id].setEeObject(eeObject);
            managedLayers[id].setVisParams(vis);
            managedLayers[id].setName(name);
        } else {
            var l = ui.Map.Layer(eeObject, vis, name);
            managedLayers[id] = l;
            // Insere antes das regiões (que estão no topo)
            var idx = Math.max(0, Map.layers().length() - 2);
            Map.layers().insert(idx, l);
        }
    }

    function updateSelectedRegionsMap() {
        var selectedNames = [];
        Object.keys(regionCheckboxes).forEach(function (key) {
            if (regionCheckboxes[key].getValue()) selectedNames.push(key);
        });
        if (selectedNames.length === 0) {
            layerSelectedRegion.setEeObject(ee.Image());
            return;
        }
        var selectedFc = current_regiones.filter(ee.Filter.inList(countryConfigs[getSelectedCountry()].property, selectedNames));
        layerSelectedRegion.setEeObject(selectedFc.style({ color: 'ff0000', fillColor: '00000000', width: 3 }));
        Map.centerObject(selectedFc);
    }

    function clearDrawingTools() {
        var layers = Map.drawingTools().layers();
        // Remove existing fire/notFire layers
        for (var i = layers.length() - 1; i >= 0; i--) {
            var l = layers.get(i);
            if (l.getName() === 'fire' || l.getName() === 'notFire') {
                layers.remove(l);
            }
        }
        // Create new empty geometry layers for collection
        Map.drawingTools().addLayer({ geometries: [], name: 'fire', color: 'ff0000', shown: true });
        Map.drawingTools().addLayer({ geometries: [], name: 'notFire', color: '0000ff', shown: true });
    }

    function initDrawingTools() {
        var layers = Map.drawingTools().layers();
        var hasFire = false;
        var hasNotFire = false;
        for (var i = 0; i < layers.length(); i++) {
            var name = layers.get(i).getName();
            if (name === 'fire') hasFire = true;
            if (name === 'notFire') hasNotFire = true;
        }
        if (!hasFire) Map.drawingTools().addLayer({ geometries: [], name: 'fire', color: 'ff0000', shown: true });
        if (!hasNotFire) Map.drawingTools().addLayer({ geometries: [], name: 'notFire', color: '0000ff', shown: true });
    }

    function centerDrawingTools() {
        var fireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'fire'; })[0];
        var notFireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'notFire'; })[0];
        var fireGeom = fireLayer ? fireLayer.getEeObject().geometries() : ee.List([]);
        var notFireGeom = notFireLayer ? notFireLayer.getEeObject().geometries() : ee.List([]);
        var totalFc = ee.FeatureCollection(fireGeom.map(function (g) { return ee.Feature(ee.Geometry(g)); }))
            .merge(ee.FeatureCollection(notFireGeom.map(function (g) { return ee.Feature(ee.Geometry(g)); })));

        totalFc.size().evaluate(function (size) {
            if (size > 0) Map.centerObject(totalFc);
        });
    }

    // --- Sample Stats Panel ---

    // --- Sample Stats Panel ---
    var panel_stats = ui.Panel({
        style: { margin: '4px 0px', padding: '4px', border: '1px solid #e0e0e0', backgroundColor: '#f9f9f9' }
    });

    function updateStats() {
        panel_stats.clear();
        panel_stats.add(ui.Label(L.lbl_stats, { fontSize: '11px', fontWeight: 'bold', margin: '2px 0px' }));

        var layers = Map.drawingTools().layers();
        var fireLayer = null;
        var notFireLayer = null;
        for (var i = 0; i < layers.length(); i++) {
            var ly = layers.get(i);
            if (ly.getName() === 'fire') fireLayer = ly;
            if (ly.getName() === 'notFire') notFireLayer = ly;
        }

        if (!fireLayer || !notFireLayer) return;

        var fireGeoms = fireLayer.getEeObject().geometries();
        var notFireGeoms = notFireLayer.getEeObject().geometries();

        var stats = ee.Dictionary({
            'fire_count': fireGeoms.length(),
            'fire_area': ee.Number(fireGeoms.map(function (g) { return ee.Geometry(g).area(); }).reduce(ee.Reducer.sum())).divide(10000),
            'notFire_count': notFireGeoms.length(),
            'notFire_area': ee.Number(notFireGeoms.map(function (g) { return ee.Geometry(g).area(); }).reduce(ee.Reducer.sum())).divide(10000)
        });

        panel_stats.add(ui.Label({ imageUrl: b64.get('load_gif'), style: { margin: '4px' } }));

        stats.evaluate(function (s, err) {
            if (err) {
                panel_stats.clear();
                panel_stats.add(ui.Label('Error recalculando stats', { fontSize: '10px', color: 'red' }));
                return;
            }
            if (!s) return;
            panel_stats.clear();
            panel_stats.add(ui.Label(L.lbl_stats, { fontSize: '11px', fontWeight: 'bold', margin: '2px 0px' }));

            var totalCount = s.fire_count + s.notFire_count;
            var totalArea = s.fire_area + s.notFire_area;

            function makeRow(label, count, area, color, isHeader) {
                var pctArea = totalArea > 0 ? (area / totalArea * 100).toFixed(1) : '0.0';
                var pctCount = totalCount > 0 ? (count / totalCount * 100).toFixed(1) : '0.0';
                var fSize = '9px';
                var fw = isHeader ? 'bold' : 'normal';

                return ui.Panel({
                    layout: ui.Panel.Layout.flow('horizontal'),
                    style: { margin: '0px', padding: '0px', backgroundColor: 'ffffff00' },
                    widgets: [
                        ui.Label(label, { width: '55px', color: color, fontSize: fSize, fontWeight: 'bold' }),
                        ui.Label(isHeader ? count : count.toString(), { width: '30px', textAlign: 'right', fontSize: fSize, fontWeight: fw }),
                        ui.Label(isHeader ? 'Qty%' : pctCount + '%', { width: '40px', textAlign: 'right', color: '#888', fontSize: fSize, fontWeight: fw }),
                        ui.Label(isHeader ? area : area.toFixed(1), { width: '60px', textAlign: 'right', fontSize: fSize, fontWeight: fw }),
                        ui.Label(isHeader ? 'Area%' : pctArea + '%', { width: '40px', textAlign: 'right', color: '#888', fontSize: fSize, fontWeight: fw })
                    ]
                });
            }

            panel_stats.add(makeRow('CLASE', 'QTY', 'HA', '#333', true));
            panel_stats.add(makeRow(L.lbl_fire, s.fire_count, s.fire_area, '#d32f2f', false));
            panel_stats.add(makeRow(L.lbl_not_fire, s.notFire_count, s.notFire_area, '#1a73e8', false));
            panel_stats.add(ui.Label('──────────────────────────────', { margin: '0px', color: '#ccc' }));
            panel_stats.add(makeRow(L.lbl_total, totalCount, totalArea, '#333', false));
        });
    }

    Map.drawingTools().onEdit(updateStats);
    Map.drawingTools().onLayerAdd(updateStats);
    Map.drawingTools().onLayerRemove(updateStats);


    // ==========================================
    // LÓGICA DE TROCA DE PAÍS (Multi-Country)
    // ==========================================
    function loadCountryData(countryName) {
        var conf = countryConfigs[countryName];
        current_regiones = ee.FeatureCollection(conf.asset_regions);

        // Atualiza bordas de todas as regiões no mapa
        layerAllRegions.setEeObject(current_regiones.style({ color: 'ffffff', fillColor: '00000000', width: 1 }));
        layerSelectedRegion.setEeObject(ee.Image()); // Limpa o vermelho

        // Busca regiões de forma dinâmica e popula a gaveta
        drawerRegions.panel.clear();

        var header = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '0px', padding: '0px', backgroundColor: '#f0f0f0' } });

        var titleLabel = ui.Label('Regiones', { fontSize: '11px', fontWeight: 'bold', margin: '4px', backgroundColor: '#f0f0f0' });

        var btt_all_regions = ui.Button({
            label: '[ All ]',
            style: { margin: '0px', padding: '0px', fontSize: '10px' },
            onClick: function () {
                var anyUnchecked = Object.keys(regionCheckboxes).some(function (k) { return !regionCheckboxes[k].getValue(); });
                Object.keys(regionCheckboxes).forEach(function (k) { regionCheckboxes[k].setValue(anyUnchecked, false); });
                updateSelectedRegionsMap();
                updateExportLabel();
                debouncedUpdateMosaic();
                updateShortnameSuggestion();
            }
        });

        // Botão Centralizar
        var btt_center_icon = ui.Button({
            label: 'C',
            style: { margin: '0px', padding: '0px' },
            onClick: function () {
                var selectedNames = [];
                Object.keys(regionCheckboxes).forEach(function (key) {
                    if (regionCheckboxes[key].getValue()) selectedNames.push(key);
                });
                if (selectedNames.length > 0) {
                    Map.centerObject(current_regiones.filter(ee.Filter.inList(countryConfigs[getSelectedCountry()].property, selectedNames)));
                } else {
                    Map.centerObject(current_regiones);
                }
            }
        });

        header.add(titleLabel).add(btt_all_regions).add(btt_center_icon).add(lab_loading);
        drawerRegions.panel.add(header);

        var flowPanel = ui.Panel({
            layout: ui.Panel.Layout.flow('horizontal', true),
            style: { margin: '0px', padding: '0px', backgroundColor: '#f9f9f9', maxHeight: '100px' }
        });
        drawerRegions.panel.add(flowPanel);

        current_regiones.aggregate_array(conf.property).distinct().sort().evaluate(function (list) {
            lab_loading.style().set('shown', false);
            regionCheckboxes = {};
            list.forEach(function (name, i) {
                var chk = ui.Checkbox({
                    label: name,
                    value: i === 0, // Apenas a primeira região ligada por default
                    onChange: function () {
                        updateSelectedRegionsMap();
                        updateExportLabel();
                        debouncedUpdateMosaic();
                        updateShortnameSuggestion();
                        updateClassificationsDrawer();
                    },
                    style: { margin: '1px 3px', padding: '0px', fontSize: '10px', backgroundColor: '#f9f9f9' }
                });
                regionCheckboxes[name] = chk;
                flowPanel.add(chk);
            });
            updateSelectedRegionsMap();
            updateExportLabel();
            debouncedUpdateMosaic();
            updateShortnameSuggestion();
            updateClassificationsDrawer();
        });

        // Atualiza a gaveta de períodos
        updatePeriodDrawer();

        // Atualiza as Campanhas Disponíveis em ambos os seletores
        try {
            var sampleRoot = conf.asset_samples;
            var rootList = ee.data.listAssets(sampleRoot);
            var folders = rootList ? rootList.assets.filter(function (a) { return a.type === 'FOLDER'; }) : [];
            var campaignItems = folders.map(function (f) { return f.id.split('/').slice(-1)[0]; });

            if (campaignItems.indexOf(SAMPLING_CAMPAIGN) === -1) campaignItems.push(SAMPLING_CAMPAIGN);

            var sortedItems = campaignItems.sort();
            select_campaign_imp.items().reset(sortedItems);
            select_campaign_exp.items().reset(sortedItems);
            
            select_campaign_imp.setValue(SAMPLING_CAMPAIGN, false);
            select_campaign_exp.setValue(SAMPLING_CAMPAIGN, false);
        } catch (e) {
            select_campaign_imp.items().reset([SAMPLING_CAMPAIGN]);
            select_campaign_exp.items().reset([SAMPLING_CAMPAIGN]);
            select_campaign_imp.setValue(SAMPLING_CAMPAIGN, false);
            select_campaign_exp.setValue(SAMPLING_CAMPAIGN, false);
        }

        updateImportList(conf);
        updateClassificationsDrawer();
    }

    function updateImportList(conf) {
        // Atualiza a lista de amostras no Asset para a aba IMPORTAR
        try {
            var campaignPath = conf.asset_samples + '/' + SAMPLING_CAMPAIGN;
            var assetList = ee.data.listAssets(campaignPath);
            var sample_list = assetList ? assetList.assets : [];
            var items = sample_list ? sample_list.map(function (obj) { return { label: obj.id.split('/').slice(-1)[0], value: obj.id }; }) : [];
            select_address.items().reset(items);
            if (items.length > 0) {
                select_address.setPlaceholder('Elija muestra antigua...');
            } else {
                select_address.setPlaceholder('Sin muestras en la campaña');
            }
        } catch (e) {
            select_address.items().reset([]);
            select_address.setPlaceholder('Campanha não encontrada no Asset');
        }
    }

    // ==========================================
    // CARD 1: FILTROS
    // ==========================================
    function createCabinet(title, isOpen, customMargin) {
        var panel = ui.Panel({ style: { margin: customMargin || '4px 0px', padding: '2px', border: '1px solid #dcdcdc', borderRadius: '4px', backgroundColor: '#fdfdfd' } });
        var content = ui.Panel({ style: { margin: '0px', padding: '0px', backgroundColor: '#fdfdfd' } });
        var header = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '2px 0px', padding: '1px', backgroundColor: '#f0f0f0', border: '1px solid #ddd' } });

        var iconKey = isOpen ? 'arraw_v' : 'arraw_>';
        var toggleBtn = ui.Button({ imageUrl: b64.get(iconKey), style: { margin: '0px', padding: '0px', backgroundColor: 'ffffff00' } });

        var fontSize = customMargin ? '15px' : '18px';
        header.add(toggleBtn).add(ui.Label(title, { fontSize: fontSize, fontWeight: 'bold', margin: '1px 4px', color: '#444', backgroundColor: 'ffffff00' }));
        panel.add(header).add(content);
        content.style().set('shown', isOpen);
        toggleBtn.onClick(function () {
            var isShown = content.style().get('shown');
            content.style().set('shown', !isShown);
            toggleBtn.setImageUrl(!isShown ? b64.get('arraw_v') : b64.get('arraw_>'));
        });
        return { panel: panel, content: content };
    }

    function createLayerDrawer(title, options) {
        var panel = ui.Panel({ style: { margin: '2px 0px', padding: '1px', border: '1px solid #e0e0e0', backgroundColor: '#f9f9f9' } });
        var flowPanel = ui.Panel({
            layout: ui.Panel.Layout.flow('horizontal', true),
            style: { margin: '0px', padding: '0px', backgroundColor: '#f9f9f9', maxHeight: '100px' }
        });
        var checkboxes = {};
        options.forEach(function (opt) {
            var chk = ui.Checkbox({
                label: opt.label, value: opt.value || false,
                onChange: function (checked) {
                    if (opt.onChange) opt.onChange(checked);
                    debouncedUpdateMosaic();
                },
                style: { margin: '1px 3px', padding: '0px', fontSize: '10px', backgroundColor: '#f9f9f9' }
            });
            checkboxes[opt.id] = chk;
            flowPanel.add(chk);
        });
        var titleLabel = ui.Label(title, { fontSize: '11px', fontWeight: 'bold', margin: '1px 2px', backgroundColor: '#f9f9f9' });
        panel.add(titleLabel).add(flowPanel);
        return { panel: panel, checkboxes: checkboxes };
    }

    // --- CABINET 1: CONFIGURATION ---
    var cabConfig = createCabinet(L.cab_config, false);
    panel_control.add(cabConfig.panel);

    var drawerCountry = createLayerDrawer(L.lbl_country, Object.keys(countryConfigs).map(function (c) {
        return {
            id: c, label: c, value: c === 'Peru', onChange: function (checked) {
                if (checked) {
                    Object.keys(countryCheckboxes).forEach(function (k) { if (k !== c) countryCheckboxes[k].setValue(false, false); });
                    loadCountryData(c);
                }
            }
        };
    }));
    var countryCheckboxes = drawerCountry.checkboxes;
    cabConfig.content.add(drawerCountry.panel);

    var drawerRegions = { panel: ui.Panel({ style: { margin: '2px 0px', padding: '2px', border: '1px solid #e0e0e0', backgroundColor: '#f9f9f9' } }) };
    cabConfig.content.add(drawerRegions.panel);

    // --- CABINET 2: TEMPORAL ---
    var cabTemporal = createCabinet(L.cab_temporal, false);
    panel_control.add(cabTemporal.panel);

    var drawerPeriodicity = createLayerDrawer(L.lbl_periodicity, [
        { id: 'anual', label: L.opt_annual, value: false, onChange: function (checked) { updatePeriodDrawer(); } },
        { id: 'mensal', label: L.opt_monthly, value: true, onChange: function (checked) { updatePeriodDrawer(); } }
    ]);
    var periodicityCheckboxes = drawerPeriodicity.checkboxes;
    cabTemporal.content.add(drawerPeriodicity.panel);

    var drawerPeriodAnual = { panel: ui.Panel({ style: { margin: '1px 0px', padding: '1px' } }) };
    var drawerPeriodMensal = { panel: ui.Panel({ style: { margin: '1px 0px', padding: '1px' } }) };
    cabTemporal.content.add(drawerPeriodAnual.panel).add(drawerPeriodMensal.panel);

    var periodCheckboxes = {};
    function updatePeriodDrawer() {
        drawerPeriodAnual.panel.clear(); drawerPeriodMensal.panel.clear();
        var showAnual = periodicityCheckboxes['anual'].getValue();
        var showMensal = periodicityCheckboxes['mensal'].getValue();

        periodCheckboxes = {}; // Reinicia para não acumular períodos de categorias desmarcadas

        if (showAnual) populatePeriodPanel(drawerPeriodAnual.panel, 'anual');
        if (showMensal) populatePeriodPanel(drawerPeriodMensal.panel, 'mensal');
        updateExportLabel(); debouncedUpdateMosaic();
    }

    function populatePeriodPanel(pnl, type) {
        var dates = getDynamicDates(type);
        pnl.add(ui.Label(type.toUpperCase(), { fontSize: '10px', fontWeight: 'bold', margin: '2px' }));
        var flow = ui.Panel({
            layout: ui.Panel.Layout.flow('horizontal', true),
            style: { margin: '0px', backgroundColor: '#f9f9f9', maxHeight: '120px' }
        });
        pnl.add(flow);
        dates.forEach(function (d, i) {
            var chk = ui.Checkbox({
                label: d, value: (type === 'mensal' && i === 0), // O primeiro agora é o mais recente
                onChange: function () { updateExportLabel(); debouncedUpdateMosaic(); },
                style: { margin: '1px 3px', fontSize: '10px', backgroundColor: '#f9f9f9' }
            });
            periodCheckboxes[d] = chk;
            flow.add(chk);
        });
    }

    function getSelectedPeriods() {
        var selected = [];
        Object.keys(periodCheckboxes).forEach(function (k) {
            if (periodCheckboxes[k].getValue()) selected.push(k);
        });
        return selected;
    }

    // --- CABINET: LAYERS (Satellites + Reference) ---
    var cabLayers = createCabinet(L.cab_layers, true);
    panel_control.add(cabLayers.panel);

    var subCabSat = createCabinet(L.cab_satellites, true, '2px 2px 2px 10px');
    var subCabRef = createCabinet(L.cab_reference, false, '2px 2px 2px 10px');
    cabLayers.content.add(subCabSat.panel).add(subCabRef.panel);

    // 1. Define sub-drawers for Reference
    var extraCheckboxes = {};
    var drawerAQ = createLayerDrawer(L.lbl_burned, [
        { id: 'mcd64a1', label: 'MODIS MCD64A1', value: false },
        { id: 'gabam', label: 'GABAM', value: false },
        { id: 'fire_cci', label: 'FIRE_CCI', value: false },
        { id: 'peru_ref', label: 'Cicatrizes Peru', value: false }
    ]);
    var drawerFocos = createLayerDrawer(L.lbl_hotspots, [
        { id: 'buffer_inpe', label: 'Buffer Focos', value: false },
        { id: 'hotspots_inpe', label: 'Hotspots INPE', value: false }
    ]);
    drawerAQ.panel.style().set('shown', true); drawerFocos.panel.style().set('shown', true);
    subCabRef.content.add(drawerAQ.panel).add(drawerFocos.panel);

    // 2. Define sub-drawers for Satellites
    var drawerVis = createLayerDrawer(L.lbl_vis_preset, [
        { id: 'fire', label: L.opt_rgb_fire, value: true },
        { id: 'coverage', label: L.opt_rgb_coverage, value: false },
        { id: 'false', label: L.opt_rgb_false, value: false },
        { id: 'swir_alt', label: L.opt_rgb_swir_alt, value: false },
        { id: 'natural', label: L.opt_rgb_natural, value: false },
        { id: 'nir', label: L.opt_gray_nir, value: false },
        { id: 'swir1', label: L.opt_gray_swir1, value: false },
        { id: 'swir2', label: L.opt_gray_swir2, value: false },
        { id: 'nbr', label: L.opt_gray_nbr, value: false },
        { id: 'ndvi', label: L.opt_gray_ndvi, value: false }
    ]);
    var visCheckboxes = drawerVis.checkboxes;

    subCabSat.content.add(drawerVis.panel);

    var drawerAsset = createLayerDrawer(L.lbl_asset_mosaics, [
        { id: 'sentinel2', label: 'Sentinel2', value: false },
        { id: 'sentinel2_buffer', label: 'Sentinel2 Buffer', value: true }
    ]);
    var assetCheckboxes = drawerAsset.checkboxes;

    var drawerRaw = createLayerDrawer(L.lbl_raw_mosaics, [
        { id: 'sentinel2', label: 'Sentinel2', value: false },
        { id: 'landsat', label: 'Landsat', value: false },
        { id: 'modis', label: 'MODIS', value: false },
        { id: 'hls', label: 'HLS', value: false },
        { id: 'planet', label: 'Planet', value: false }
    ]);
    rawCheckboxes = drawerRaw.checkboxes;

    subCabSat.content.add(drawerAsset.panel).add(drawerRaw.panel);

    // Mesclar os checkboxes para o gerenciamento global
    Object.keys(drawerAQ.checkboxes).forEach(function (k) { extraCheckboxes[k] = drawerAQ.checkboxes[k]; });
    Object.keys(drawerFocos.checkboxes).forEach(function (k) { extraCheckboxes[k] = drawerFocos.checkboxes[k]; });

    // --- SUB-CABINET: CLASSIFICAÇÕES REGIONAIS ---
    var subCabClass = createCabinet(L.cab_classifications, false, '2px 2px 2px 10px');
    cabLayers.content.add(subCabClass.panel);

    var drawerClassToggle = createLayerDrawer('Bandas', [
        { id: 'cls', label: 'classification', value: true, onChange: function () { debouncedUpdateMosaic(); } },
        { id: 'prb', label: 'probability', value: false, onChange: function () { debouncedUpdateMosaic(); } }
    ]);
    classBandCheckboxes = drawerClassToggle.checkboxes;
    subCabClass.content.add(drawerClassToggle.panel);

    var drawerClassModels = { panel: ui.Panel({ style: { margin: '2px 0px', padding: '1px', backgroundColor: '#f9f9f9' } }) };
    subCabClass.content.add(drawerClassModels.panel);

    // --- CABINET 4: SAMPLES ---
    var cabSamples = createCabinet(L.cab_samples, true);
    panel_control.add(cabSamples.panel);

    // Sub-drawers panels
    var drawerInst = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };
    var drawerImp = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };
    var drawerAmo = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };
    var drawerExp = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };

    var drawerControl = createLayerDrawer('Dashboard', [
        { id: 'inst', label: L.short_guide, value: false, onChange: function (v) { drawerInst.panel.style().set('shown', v); } },
        { id: 'imp', label: L.short_import, value: false, onChange: function (v) { drawerImp.panel.style().set('shown', v); } },
        { id: 'amo', label: L.cab_samples, value: true, onChange: function (v) { drawerAmo.panel.style().set('shown', v); if (v) updateStats(); } },
        { id: 'exp', label: L.short_export, value: true, onChange: function (v) { drawerExp.panel.style().set('shown', v); if (v) { suggestNextVersion(); syncDateSelect(); } } }
    ]);
    drawerExp.panel.style().set('shown', true);
    drawerAmo.panel.style().set('shown', true);

    // --- CAMPAIGN SELECTORS (Synced) ---
    function makeCampaignSelector() {
        return ui.Select({
            items: [SAMPLING_CAMPAIGN],
            placeholder: 'Campaña...',
            value: SAMPLING_CAMPAIGN,
            onChange: function (v) {
                SAMPLING_CAMPAIGN = v;
                // Sincroniza ambos os seletores
                select_campaign_imp.setValue(v, false);
                select_campaign_exp.setValue(v, false);
                // Atualiza as listas
                suggestNextVersion();
                syncDateSelect();
                var conf = countryConfigs[getSelectedCountry()];
                updateImportList(conf);
            },
            style: { margin: '2px', stretch: 'horizontal' }
        });
    }

    var select_campaign_imp = makeCampaignSelector();
    var select_campaign_exp = makeCampaignSelector();

    cabSamples.content.add(drawerControl.panel);
    cabSamples.content.add(drawerInst.panel);
    cabSamples.content.add(drawerImp.panel);
    cabSamples.content.add(drawerAmo.panel);
    cabSamples.content.add(drawerExp.panel);

    // Populate Sub-drawers
    drawerInst.panel.add(ui.Label(L.instructions, { fontSize: '10px', color: '#555', margin: '2px', whiteSpace: 'pre' }));

    // Drawing control buttons row
    var rowDraw = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '2px 0px', stretch: 'horizontal' } });

    function setLayerMode(name) {
        var layers = Map.drawingTools().layers();
        for (var i = 0; i < layers.length(); i++) {
            if (layers.get(i).getName() === name) {
                Map.drawingTools().setShape('polygon');
                Map.drawingTools().setSelected(layers.get(i));
                return;
            }
        }
    }

    var btnFire = ui.Button({ label: 'Fire', style: { color: '#d32f2f', margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: function () { setLayerMode('fire'); } });
    var btnNotFire = ui.Button({ label: 'Not Fire', style: { color: '#1a73e8', margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: function () { setLayerMode('notFire'); } });
    var btnHand = ui.Button({ label: 'Hand', style: { margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: function () { Map.drawingTools().setShape(null); } });
    var btnClear = ui.Button({ label: 'Delete', style: { margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: clearDrawingTools });
    var btnCenter = ui.Button({ label: 'C', style: { margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: centerDrawingTools });

    rowDraw.add(btnFire).add(btnNotFire).add(btnHand).add(btnClear).add(btnCenter);

    drawerAmo.panel.add(rowDraw);
    drawerAmo.panel.add(panel_stats);
    // Export and Import will be populated below...

    // ==========================================
    // ABA: IMPORTAR
    // ==========================================
    var select_address = ui.Select({ style: styles.input });

    var btt_import_action = ui.Button({
        imageUrl: ICONS.download, style: styles.btn_blue,
        onClick: function () {
            var id = select_address.getValue();
            if (!id) return;
            var parts = id.split('_');
            var lastPart = parts[parts.length - 1], penultPart = parts[parts.length - 2];
            var recoveredPeriod = (!isNaN(penultPart) && !isNaN(lastPart)) ? (penultPart + '_' + lastPart) : lastPart;
            periodicityCheckboxes['mensal'].setValue((!isNaN(penultPart) && !isNaN(lastPart)), false);
            periodicityCheckboxes['anual'].setValue(!periodicityCheckboxes['mensal'].getValue(), false);
            updatePeriodDrawer();
            Object.keys(periodCheckboxes).forEach(function (k) {
                if (periodCheckboxes[k]) periodCheckboxes[k].setValue(k === recoveredPeriod, false);
            });
            var matchedRegion = null;
            var regionNames = Object.keys(regionCheckboxes);
            for (var i = 0; i < regionNames.length; i++) {
                if (id.indexOf(regionNames[i]) !== -1) { matchedRegion = regionNames[i]; break; }
            }
            if (matchedRegion) {
                Object.keys(regionCheckboxes).forEach(function (k) { regionCheckboxes[k].setValue(k === matchedRegion, false); });
                updateSelectedRegionsMap();
            }
            updateExportPreview();
            clearDrawingTools();
            var layers = Map.drawingTools().layers();
            var fireLayer, notFireLayer;
            for (var i = 0; i < layers.length(); i++) {
                if (layers.get(i).getName() === 'fire') fireLayer = layers.get(i);
                if (layers.get(i).getName() === 'notFire') notFireLayer = layers.get(i);
            }

            ee.FeatureCollection(id).filter(ee.Filter.eq('fire', 1)).geometry().coordinates().map(function (list) { return ee.Geometry.Polygon(list); })
                .evaluate(function (geomList) { if (fireLayer && geomList) fireLayer.geometries().reset(geomList); });
            ee.FeatureCollection(id).filter(ee.Filter.eq('fire', 0)).geometry().coordinates().map(function (list) { return ee.Geometry.Polygon(list); })
                .evaluate(function (geomList) { if (notFireLayer && geomList) notFireLayer.geometries().reset(geomList); });
        }
    });

    var row_imp = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_imp.add(ui.Label('Campana:', { fontSize: '10px', margin: '5px 2px' }));
    row_imp.add(select_campaign_imp);
    row_imp.add(select_address).add(btt_import_action);
    drawerImp.panel.add(row_imp);

    // ==========================================
    // ABA: EXPORTAR
    // ==========================================

    // --- Versão automática ---
    var lab_version_status = ui.Label(L.ver_checking, { fontSize: '10px', color: '#888', margin: '1px' });
    var txt_version = ui.Textbox({ placeholder: '0001', value: 'v0001', onChange: updateExportPreview, style: { margin: '1px', padding: '0px', width: '55px' } });

    function suggestNextVersion() {
        lab_version_status.setValue(L.ver_checking).style().set('color', '#888');
        var conf = countryConfigs[getSelectedCountry()];

        try {
            var campaignPath = conf.asset_samples + '/' + SAMPLING_CAMPAIGN;
            var assetList = ee.data.listAssets(campaignPath);
            var assets = assetList ? assetList.assets : [];

            if (!assets || assets.length === 0) {
                txt_version.setValue('0001');
                lab_version_status.setValue(L.ver_empty).style().set('color', '#e65100');
                updateExportPreview();
                return;
            }

            var maxV = 0;

            assets.forEach(function (a) {
                var fname = a.id.split('/').slice(-1)[0];

                var m = fname.match(/^samples_(\d{4})$/);

                if (m) {
                    var n = parseInt(m[1], 10);
                    if (n > maxV) maxV = n;
                }
            });

            var nextNumber = ('000' + (maxV + 1)).slice(-4);
            var next = 'samples_' + nextNumber;

            txt_version.setValue(nextNumber);

            lab_version_status
                .setValue(L.ver_suggested + next)
                .style().set('color', '#0f9d58');

        } catch (e) {
            txt_version.setValue('0001');
            lab_version_status.setValue(L.ver_empty).style().set('color', '#e65100');
        }

        updateExportPreview();
    }

    // --- Shortname (opcional) ---
    var txt_shortname = ui.Textbox({ placeholder: L.placeholder_sn, onChange: updateExportPreview, style: { margin: '1px', padding: '0px', stretch: 'horizontal' } });
    var txt_comment = ui.Textbox({ placeholder: L.placeholder_cmt, style: { margin: '1px', padding: '0px', stretch: 'horizontal' } });
    var select_date_export = ui.Select({ placeholder: L.placeholder_date, onChange: updateExportPreview, style: { margin: '1px', stretch: 'horizontal' } });

    function buildDateSelectItems() {
        var items = [];
        var today = new Date();
        // Limitamos ao ano atual real, não permitindo datas futuras inconsistentes
        var maxYear = today.getFullYear();
        var maxMonth = today.getMonth();
        if (maxMonth === 0) { maxMonth = 12; maxYear--; }

        // Se estivermos em 2026 no sistema, mas os dados reais param antes, 
        // vamos forçar um limite conservador (ex: 2025_12) se necessário,
        // ou deixar o usuário escolher. Aqui vamos apenas garantir que a ordem é inversa.

        // Meses
        for (var y = maxYear; y >= 2019; y--) {
            var mEnd = (y === maxYear) ? Math.min(maxMonth, 12) : 12;
            for (var m = mEnd; m >= 1; m--) {
                var mm = m < 10 ? '0' + m : m.toString();
                items.push({ label: y + '_' + mm, value: y + '_' + mm });
            }
        }
        // Anos
        for (var yr = maxYear; yr >= 2019; yr--) {
            items.push({ label: '' + yr, value: '' + yr });
        }
        return items;
    }

    function syncDateSelect() {
        select_date_export.items().reset(buildDateSelectItems());
        var periods = getSelectedPeriods();
        // PRIORIDADE: Se houver um período selecionado na aba TEMPORAL, usa ele!
        if (periods.length > 0) {
            select_date_export.setValue(periods[0]);
        }
        updateExportPreview();
    }

    // --- Satélites (apenas metadado) ---
    var satLabels = ['Sentinel2', 'Landsat', 'MODIS', 'HLS', 'Planet'];
    var satValues = ['sentinel2', 'landsat', 'modis', 'hls', 'planet'];
    var satCheckboxes = {};
    var satRow = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal', true), style: { margin: '0px', padding: '0px', maxHeight: '50px' } });
    satValues.forEach(function (sv, i) {
        var chk = ui.Checkbox({ label: satLabels[i], value: sv === 'sentinel2', onChange: updateExportPreview, style: { margin: '1px 3px', fontSize: '10px' } });
        satCheckboxes[sv] = chk;
        satRow.add(chk);
    });

    // --- Preview do nome ---
    var lab_export_preview = ui.Label({ value: '', style: { margin: '1px', fontSize: '10px', fontWeight: 'bold', color: '#1a73e8', stretch: 'horizontal' } });
    var lab_date_error = ui.Label(L.err_no_date, { fontSize: '10px', color: 'red', margin: '0px 2px', shown: false });

    function getSelectedSatellites() {
        var sats = [];
        satValues.forEach(function (sv) { if (satCheckboxes[sv].getValue()) sats.push(sv); });
        return sats;
    }
    function getSampleName() {
        var num = txt_version.getValue() || '0001';
        num = num.replace(/^samples_/, '');
        return 'samples_' + num;
    }
    function updateExportPreview() {
        var ver = getSampleName();
        var sn = txt_shortname.getValue() ? redundanceReplace(txt_shortname.getValue()) : '';
        var dt = select_date_export.getValue();

        lab_date_error.style().set('shown', !dt);

        var dt_label = dt || 'YYYY';
        var parts = [ver];

        if (sn) parts.push(sn);
        parts.push(redundanceReplace(dt_label));

        lab_export_preview.setValue(parts.join('_'));
    }

    // Alias para compatibilidade com outros módulos que chamam updateExportLabel
    function updateExportLabel() { updateExportPreview(); }

    function updateShortnameSuggestion() {
        var selected = [];
        Object.keys(regionCheckboxes).forEach(function (k) {
            if (regionCheckboxes[k].getValue()) selected.push(k);
        });
        if (selected.length === 0) return;
        var suggestion = selected.length === 1 ? selected[0] : 'multi_' + selected.length + '_regiones';
        txt_shortname.setValue(redundanceReplace(suggestion));
        updateExportPreview();
    }

    // --- getLandcoverVector com metadados ricos ---
    function getLandcoverVector(satellite) {
        var fireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'fire'; });
        var notFireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'notFire'; });
        if (fireLayer.length === 0 || notFireLayer.length === 0) {
            print(L.err_layers);
            return null;
        }
        var selectedNames = [];
        Object.keys(regionCheckboxes).forEach(function (k) { if (regionCheckboxes[k].getValue()) selectedNames.push(k); });
        var safeRegion = selectedNames.length === 1 ? selectedNames[0] : (selectedNames.length > 1 ? 'multi' : 'none');
        var datePeriod = select_date_export.getValue() || 'YYYY';
        var ver = getSampleName();
        var sn = txt_shortname.getValue() || '';
        var comment = txt_comment.getValue() || '';
        var now = new Date();
        var createdAt = now.getFullYear() + '-' + (now.getMonth() + 1) + '-' + now.getDate();

        function makeProps(fireVal) {
            return {
                'fire': fireVal, 'region': safeRegion, 'period': datePeriod,
                'satellite': satellite || 'unspecified', 'version': ver,
                'shortname': sn, 'comment': comment, 'created_at': createdAt
            };
        }

        var fire = ee.FeatureCollection(
            fireLayer[0].getEeObject().geometries().map(function (g) {
                return ee.Feature(ee.Geometry(g), makeProps(1));
            })
        );
        var notFire = ee.FeatureCollection(
            notFireLayer[0].getEeObject().geometries().map(function (g) {
                return ee.Feature(ee.Geometry(g), makeProps(0));
            })
        );
        return fire.merge(notFire);
    }

    // --- Botão unificado de exportação ---
    var btt_export = ui.Button({
        label: L.btn_export,
        style: { margin: '2px 0px', fontWeight: 'bold', color: '#0f9d58', stretch: 'horizontal' },
        onClick: function () {
            var dt = select_date_export.getValue();
            if (!dt) {
                print(L.err_no_date);
                return;
            }

            var sats = getSelectedSatellites();
            if (sats.length === 0) { print(L.err_no_sat); return; }
            var conf = countryConfigs[getSelectedCountry()];
            var ver = getSampleName();
            var sn = txt_shortname.getValue() ? redundanceReplace(txt_shortname.getValue()) : '';
            var dt_formatted = redundanceReplace(dt || 'YYYY');

            // Join all selected satellites into a single string for metadata
            var satelliteStr = sats.join(',');

            var vec = getLandcoverVector(satelliteStr);
            if (!vec) return;

            var parts = [ver];
            if (sn) parts.push(sn);
            parts.push(dt);

            var desc = parts.join('_');
            var conf = countryConfigs[getSelectedCountry()];

            Export.table.toAsset({
                collection: vec,
                description: PERSONAL_TASK_FLAG + '_ASSET_' + desc,
                assetId: conf.asset_samples + '/' + SAMPLING_CAMPAIGN + '/' + desc
            });
            Export.table.toCloudStorage({
                collection: vec,
                description: PERSONAL_TASK_FLAG + '_GCS_' + desc,
                bucket: conf.bucket,
                fileNamePrefix: conf.gcs_samples + '/' + SAMPLING_CAMPAIGN + '/' + desc,
                fileFormat: 'CSV'
            });
            print(L.task_created + desc + L.task_hint);
        }
    });

    // --- Montar o panel_export ---
    drawerExp.panel.add(ui.Label('Seleccionar Campana:', { fontSize: '11px', fontWeight: 'bold', margin: '4px 2px 2px 2px' }));
    drawerExp.panel.add(select_campaign_exp);
    drawerExp.panel.add(ui.Label(L.lbl_version, styles.label));
    var rowVer = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    rowVer.add(txt_version).add(lab_version_status);
    drawerExp.panel.add(rowVer);

    drawerExp.panel.add(ui.Label(L.lbl_shortname, styles.label));
    drawerExp.panel.add(txt_shortname);

    drawerExp.panel.add(ui.Label(L.lbl_comment, styles.label));
    drawerExp.panel.add(txt_comment);

    drawerExp.panel.add(ui.Label(L.lbl_date, styles.label));
    drawerExp.panel.add(select_date_export);
    drawerExp.panel.add(lab_date_error);

    drawerExp.panel.add(ui.Label(L.lbl_satellites, styles.label));
    drawerExp.panel.add(satRow);

    drawerExp.panel.add(lab_export_preview);
    drawerExp.panel.add(btt_export);


    // INITIALIZE APP (Initial trigger)
    loadCountryData('Peru');
    updateMosaic();
    initDrawingTools();
    syncDateSelect();
    suggestNextVersion();
    updateStats();
}

user_interface();

function redundanceReplace(string) {
    return string.toLowerCase().replace(/ /gi, '_').replace(/-/gi, '_')
        .replace(/â|á|à|ã|ä/gi, 'a').replace(/ê|é|è|ẽ/gi, 'e')
        .replace(/î|í|ì!ĩ/gi, 'i').replace(/ô|ó|ò|õ|ö/gi, 'o')
        .replace(/û|ú|ù|ũ|ü/gi, 'u').replace(/ç/gi, 'c');
}

// ─── FUNÇÕES DE SUPORTE E CORREÇÕES ORIGINAIS (RAW MOSAICS) ─────────────────
function clipBoard_Landsat(image) {
    return image.updateMask(ee.Image().paint(image.geometry().buffer(-3000)).eq(0));
}

function bitwiseExtract(value, fromBit, toBit) {
    if (toBit === undefined) toBit = fromBit;
    var maskSize = ee.Number(1).add(toBit).subtract(fromBit);
    var mask = ee.Number(1).leftShift(maskSize).subtract(1);
    return value.rightShift(fromBit).bitwiseAnd(mask);
}

function addIndices(image) {
    var ndvi = image.normalizedDifference(['nir', 'red']).rename('ndvi');
    var nbr = image.normalizedDifference(['nir', 'swir2']).rename('nbr');
    return image.addBands([ndvi, nbr]);
}

function addBand_NBR(image) {
    var exp = '( b("nir") - b("swir2") ) / ( b("nir") + b("swir2") )';
    var minimoNBR = image.expression(exp).multiply(-1).add(1).multiply(1000).int16().rename("nbr");
    return image.addBands(minimoNBR);
}

function addDOY(image) {
    var doy = ee.Image(ee.Number.parse(image.date().format('D'))).int16().rename('dayOfYear');
    return image.addBands(doy);
}

function corrections_LS57_col2(image) {
    var opticalBands = image.select('SR_B.*').multiply(0.0000275).add(-0.2);
    var thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0);
    image = image.addBands(opticalBands, null, true).addBands(thermalBands, null, true);

    var cloudShadowBitMask = (1 << 3);
    var cloudsBitMask = (1 << 5);
    var qa = image.select('QA_PIXEL');
    var mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).and(qa.bitwiseAnd(cloudsBitMask).eq(0));

    var clear = bitwiseExtract(qa, 6);
    var water = bitwiseExtract(qa, 7);
    var radsatQA = image.select('QA_RADSAT');
    var anySaturated = bitwiseExtract(radsatQA, 0, 6);
    var mask_saturation = clear.or(water).and(anySaturated.not());

    var negative_mask = image.select(['SR_B1']).gt(0).and(image.select(['SR_B2']).gt(0)).and(
        image.select(['SR_B3']).gt(0)).and(image.select(['SR_B4']).gt(0)).and(
            image.select(['SR_B5']).gt(0)).and(image.select(['SR_B7']).gt(0));

    image = image.updateMask(mask).updateMask(mask_saturation).updateMask(negative_mask);
    var oldBands = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7'];
    var newBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];
    return image.select(oldBands, newBands);
}

function corrections_LS8_col2(image) {
    var opticalBands = image.select('SR_B.*').multiply(0.0000275).add(-0.2);
    opticalBands = opticalBands.multiply(10000).subtract(0.0000275 * 0.2 * 1e5 * 100).round().divide(10000);
    var thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0);
    image = image.addBands(opticalBands, null, true).addBands(thermalBands, null, true);

    var qa = image.select('QA_PIXEL');
    var cloud = qa.bitwiseAnd(1 << 3).and(qa.bitwiseAnd(1 << 9)).or(qa.bitwiseAnd(1 << 4));
    var good_pixel = qa.bitwiseAnd(1 << 6).or(qa.bitwiseAnd(1 << 7));
    var radsatQA = image.select('QA_RADSAT');
    var saturated = radsatQA.bitwiseAnd(1 << 0).or(radsatQA.bitwiseAnd(1 << 1)).or(radsatQA.bitwiseAnd(1 << 2))
        .or(radsatQA.bitwiseAnd(1 << 3)).or(radsatQA.bitwiseAnd(1 << 4)).or(radsatQA.bitwiseAnd(1 << 5)).or(radsatQA.bitwiseAnd(1 << 6));

    var negative_mask = image.select(['SR_B2']).gt(0).and(image.select(['SR_B3']).gt(0)).and(
        image.select(['SR_B4']).gt(0)).and(image.select(['SR_B5']).gt(0)).and(
            image.select(['SR_B6']).gt(0)).and(image.select(['SR_B7']).gt(0));

    image = image.updateMask(cloud.not()).updateMask(good_pixel).updateMask(saturated.not()).updateMask(negative_mask);
    var oldBands = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'];
    var newBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];
    return image.select(oldBands, newBands).float();
}

function corrections_modis(image) {
    var oldBands = ['sur_refl_b03', 'sur_refl_b04', 'sur_refl_b01', 'sur_refl_b02', 'sur_refl_b06', 'sur_refl_b07'];
    var newBands = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2'];
    return image.select(oldBands, newBands);
}

var processLS57 = function (img) { return addDOY(addBand_NBR(corrections_LS57_col2(clipBoard_Landsat(img)))); };
var processLS89 = function (img) { return addDOY(addBand_NBR(corrections_LS8_col2(clipBoard_Landsat(img)))); };

var processS2 = function (img) {
    var mask = img.select('cs').gte(0.40);
    var optical = img.updateMask(mask).select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12'], ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']);
    return addDOY(addBand_NBR(optical));
};

var processMODIS = function (img) { return addDOY(addBand_NBR(corrections_modis(img))); };

var processHLS_S30 = function (img) {
    var mask = img.select('Fmask').bitwiseAnd(1 << 1).eq(0);
    var optical = img.updateMask(mask).select(
        ['B2', 'B3', 'B4', 'B8A', 'B11', 'B12'],
        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    );
    return addDOY(addBand_NBR(optical).set({
        'system:time_start': img.get('system:time_start'),
        'system:time_end': img.get('system:time_end')
    }));
};

var processHLS_L30 = function (img) {
    var mask = img.select('Fmask').bitwiseAnd(1 << 1).eq(0);
    var optical = img.updateMask(mask).select(
        ['B2', 'B3', 'B4', 'B5', 'B6', 'B7'],
        ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']
    );
    return addDOY(addBand_NBR(optical).set({
        'system:time_start': img.get('system:time_start'),
        'system:time_end': img.get('system:time_end')
    }));
};
