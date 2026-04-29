/********************************************
v10: Exclusive Tool for Sample Collection and Export (Vectors)
- Ultra-Compact UI and Margins (0~1px)
- Dynamic Multi-Country (Chile, Peru...)
- Automatic region search via .aggregate_array().distinct().sort()
- Dynamic update of Destination/Source Assets
********************************************/

// ─── LANGUAGE CONFIGURATION ─────────────────────────────────────────────────
// Change APP_LANG to switch the interface language: 'es', 'pt', 'en'
var APP_LANG = 'es';

var L = (function () {
    var dict = {
        es: {
            title: 'MapBiomas-Fuego | Monitor',
            cab_config: '🌍 CONFIGURACIÓN',
            cab_temporal: '📅 TEMPORAL',
            cab_layers: '🗺️ CAPAS',
            cab_samples: '🖍️ MUESTRAS',
            lbl_country: 'País',
            lbl_regions: 'Regiones',
            lbl_periodicity: 'Periodicidad',
            opt_annual: 'Anual',
            opt_monthly: 'Mensual',
            lbl_asset_mosaics: 'Mosaicos classificados buffer',
            lbl_raw_mosaics: 'Mosaicos on the fly',
            lbl_ref_cats: 'Categorías de Referencia',
            lbl_burned: 'Área Quemada',
            lbl_hotspots: 'Focos / Buffers',
            cab_instructions: 'ℹ️ Cómo usar este módulo',
            instructions: '1. Use las herramientas de dibujo en el mapa.\n' +
                '2. Capa "fire" (rojo) = área quemada.\n' +
                '3. Capa "notFire" (azul) = área no quemada.\n' +
                '4. Complete los metadatos en la pestaña EXPORTAR.\n' +
                '5. Haga clic en EXPORTAR para guardar en Asset y GCS.\n' +
                '6. Vaya a la pestaña Tasks en GEE para ejecutar.',
            tab_import: '📥 IMPORTAR',
            tab_export: '📤 EXPORTAR',
            btn_load: 'Cargar',
            lbl_version: 'Versión:',
            lbl_shortname: 'Nombre corto (opcional):',
            lbl_comment: 'Comentario (metadato):',
            lbl_date: 'Fecha representada:',
            lbl_satellites: 'Válido para satélites (opcional):',
            placeholder_date: 'Seleccionar fecha...',
            placeholder_asset: 'Elegir muestra existente...',
            placeholder_sn: 'apodo (ej: norte_amazonia)',
            placeholder_cmt: 'comentario (metadato libre)',
            btn_export: '🚀 EXPORTAR (Asset + GCS)',
            ver_checking: '🔄 Verificando...',
            ver_suggested: '✓ sugerida: ',
            ver_empty: '⚠ asset vacío',
            task_created: '🚀 Tareas creadas: ',
            task_hint: ' (vaya a la pestaña Tasks para ejecutar)',
            err_layers: '⚠️ Faltan capas "fire" o "notFire" en el mapa.',
            err_no_sat: '⚠️ Seleccione al menos un satélite como metadato.',
            err_no_date: '⚠️ Seleccione la fecha representada.',
            lbl_stats: 'Resumen de Muestras:',
            lbl_fire: 'Fuego',
            lbl_not_fire: 'No Fuego',
            lbl_total: 'Total',
            lbl_area: 'Área (ha)',
            lbl_count: 'Cant.',
            lbl_satellites_toggle: 'Satélites',
            loading: '🔄️'
        },
        pt: {
            title: 'MapBiomas-Fogo | Monitor',
            cab_config: '🌍 CONFIGURAÇÃO',
            cab_temporal: '📅 TEMPORAL',
            cab_layers: '🗺️ CAMADAS',
            cab_samples: '🖍️ AMOSTRAS',
            lbl_country: 'País',
            lbl_regions: 'Regiões',
            lbl_periodicity: 'Periodicidade',
            opt_annual: 'Anual',
            opt_monthly: 'Mensal',
            lbl_asset_mosaics: 'Mosaicos classificados buffer',
            lbl_raw_mosaics: 'Mosaicos on the fly',
            lbl_ref_cats: 'Categorias de Referência',
            lbl_burned: 'Área Queimada',
            lbl_hotspots: 'Focos / Buffers',
            cab_instructions: 'ℹ️ Como usar este módulo',
            instructions: '1. Use as ferramentas de desenho no mapa.\n' +
                '2. Camada "fire" (vermelho) = área queimada.\n' +
                '3. Camada "notFire" (azul) = área não queimada.\n' +
                '4. Preencha os metadados na aba EXPORTAR.\n' +
                '5. Clique em EXPORTAR para salvar no Asset e GCS.\n' +
                '6. Acesse a aba Tasks no GEE para executar.',
            tab_import: '📥 IMPORTAR',
            tab_export: '📤 EXPORTAR',
            btn_load: 'Carregar',
            lbl_version: 'Versão:',
            lbl_shortname: 'Shortname (opcional):',
            lbl_comment: 'Comentário (metadado):',
            lbl_date: 'Data representada:',
            lbl_satellites: 'Válido para os satélites (opcional):',
            placeholder_date: 'Selecionar data...',
            placeholder_asset: 'Escolher amostra existente...',
            placeholder_sn: 'apelido (ex: norte_amazonia)',
            placeholder_cmt: 'comentário (metadado livre)',
            btn_export: '🚀 EXPORTAR (Asset + GCS)',
            ver_checking: '🔄 Verificando...',
            ver_suggested: '✓ sugerida: ',
            ver_empty: '⚠ asset vazio',
            task_created: '🚀 Tasks criadas: ',
            task_hint: ' (vá à aba Tasks para executar)',
            err_layers: '⚠️ Faltam camadas "fire" ou "notFire" no mapa.',
            err_no_sat: '⚠️ Selecione ao menos um satélite como metadato.',
            err_no_date: '⚠️ Selecione a data representada.',
            lbl_stats: 'Resumo das Amostras:',
            lbl_fire: 'Fogo',
            lbl_not_fire: 'Não Fogo',
            lbl_total: 'Total',
            lbl_area: 'Área (ha)',
            lbl_count: 'Qtd.',
            lbl_satellites_toggle: 'Satélites',
            loading: '🔄️'
        },
        en: {
            title: 'MapBiomas-Fire | Monitor',
            cab_config: '🌍 CONFIGURATION',
            cab_temporal: '📅 TEMPORAL',
            cab_layers: '🗺️ LAYERS',
            cab_samples: '🖍️ SAMPLES',
            lbl_country: 'Country',
            lbl_regions: 'Regions',
            lbl_periodicity: 'Periodicity',
            opt_annual: 'Annual',
            opt_monthly: 'Monthly',
            lbl_asset_mosaics: 'Mosaicos classificados buffer',
            lbl_raw_mosaics: 'Mosaicos on the fly',
            lbl_ref_cats: 'Reference Categories',
            lbl_burned: 'Burned Area',
            lbl_hotspots: 'Hotspots / Buffers',
            cab_instructions: 'ℹ️ How to use this module',
            instructions: '1. Use the map drawing tools.\n' +
                '2. Layer "fire" (red) = burned area.\n' +
                '3. Layer "notFire" (blue) = unburned area.\n' +
                '4. Fill in metadata in the EXPORT tab.\n' +
                '5. Click EXPORT to save to Asset and GCS.\n' +
                '6. Go to the Tasks tab in GEE to run.',
            tab_import: '📥 IMPORT',
            tab_export: '📤 EXPORT',
            btn_load: 'Load',
            lbl_version: 'Version:',
            lbl_shortname: 'Short name (optional):',
            lbl_comment: 'Comment (metadata):',
            lbl_date: 'Represented date:',
            lbl_satellites: 'Valid for satellites (optional):',
            placeholder_date: 'Select date...',
            placeholder_asset: 'Choose existing sample...',
            placeholder_sn: 'alias (e.g. north_amazonia)',
            placeholder_cmt: 'comment (free metadata)',
            btn_export: '🚀 EXPORT (Asset + GCS)',
            ver_checking: '🔄 Checking...',
            ver_suggested: '✓ suggested: ',
            ver_empty: '⚠ empty asset',
            task_created: '🚀 Tasks created: ',
            task_hint: ' (go to Tasks tab to run)',
            err_layers: '⚠️ Missing "fire" or "notFire" layers on map.',
            err_no_sat: '⚠️ Select at least one satellite as metadata.',
            err_no_date: '⚠️ Select the represented date.',
            lbl_stats: 'Sample Summary:',
            lbl_fire: 'Fire',
            lbl_not_fire: 'Not Fire',
            lbl_total: 'Total',
            lbl_area: 'Area (ha)',
            lbl_count: 'Qty.',
            lbl_satellites_toggle: 'Satellites',
            loading: '🔄️'
        }
    };
    return dict[APP_LANG] || dict['es'];
})();

// ─── ICON REPOSITORY ────────────────────────────────────────────────────────
// Using base64 strings for simple, self-contained UI icons
var ICONS = {
    load: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAdUlEQVR4nGNgGAWjYBSMglEwCkbBSAMMDA0Nf//+Zf7//z8DIyNjOxBnoig8DMUuKPLBUPyGog8NixMQp4EIFIDiNBB9vBSNdMAwNDTEAwMDA6Dof0SGYuC/BCh+Q5EvAMVpIPrpUDTSAEPDQ0M8MNAAoPANAOfdJAmhH1mMAAAAAElFTkSuQmCC'
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
        asset_samples: 'projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/LIBRARY_SAMPLES',
        bucket: 'mapbiomas-fire',
        gcs_samples: 'sudamerica/peru/monitor/library_samples',
        property: 'region_nam'
    }
};

// Global variable to store active regions collection
var current_regiones = ee.FeatureCollection(countryConfigs['Peru'].asset_regions);

// --- VISUALIZATION SETTINGS ---
var visAsset = { bands: ['swir1', 'nir', 'red'], min: 3, max: 40 };
var visRaw = { bands: ['swir1', 'nir', 'red'], min: 3, max: 40 };

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
        btn_blue: { margin: '1px', padding: '0px', color: '#1a73e8', fontWeight: 'bold' },
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
        Object.keys(periodCheckboxes).forEach(function (k) {
            if (periodCheckboxes[k].getValue()) periods.push(k);
        });
        return periods;
    }

    function updateMosaic() {
        var checkedPeriods = getSelectedPeriods();
        var pais = getSelectedCountry().toLowerCase();
        var bands = ['swir1', 'nir', 'red'];

        // Lógica de Regiões Selecionadas
        var selectedNames = [];
        Object.keys(regionCheckboxes).forEach(function (key) {
            if (regionCheckboxes[key].getValue()) selectedNames.push(key);
        });

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
            var folderPeriod = month ? 'MONTHLY' : 'ANNUAL';

            // --- GESTÃO DE ASSETS (Mosaicos Oficiais) ---
            if (assetCheckboxes['sentinel2'] && assetCheckboxes['sentinel2'].getValue()) {
                var layerId = 'asset_s2_' + dateStr;
                desiredLayerIds.push(layerId);
                var name = 'sentinel2_fire_' + pais + '_' + dateStr;
                var imgAsset = ee.Image().select();
                try {
                    bands.forEach(function (b) {
                        var colId = 'projects/mapbiomas-mosaics/assets/FIRE/SENTINEL2/' + folderPeriod + '/' + b + '/' + name + '_' + b;
                        imgAsset = imgAsset.addBands(ee.Image(colId));
                    });
                    updateManagedLayer(layerId, imgAsset.select(bands).updateMask(spatialMask), visAsset, 'Asset S2 - ' + dateStr);
                } catch (e) {
                    updateManagedLayer(layerId, ee.Image().select(), {}, 'Asset S2 - ' + dateStr + ' [Err]');
                }
            }

            // --- GESTÃO DE RAW ---
            ['sentinel2', 'landsat', 'modis', 'hls', 'planet'].forEach(function (s) {
                if (rawCheckboxes[s] && rawCheckboxes[s].getValue()) {
                    var layerId = 'raw_' + s + '_' + dateStr;
                    desiredLayerIds.push(layerId);

                    if (s === 'planet') {
                        var planetCol = ee.ImageCollection('projects/planet-nicfi/assets/basemaps/americas')
                            .filterDate(start, end).filterBounds(bounds)
                            .map(function (img) { return img.select(['B', 'G', 'R', 'N'], ['blue', 'green', 'red', 'nir']); });
                        updateManagedLayer(layerId, planetCol.mosaic().select(['red', 'green', 'blue']).updateMask(spatialMask), { "opacity": 1, "bands": ["red", "green", "blue"], "min": 125, "max": 1858, "gamma": 1 }, 'Planet - ' + dateStr);
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
                    var spectral = rawCol.qualityMosaic('nbr').select(['blue', 'green', 'red', 'nir', 'swir1', 'swir2']).multiply(multiplier).byte();
                    updateManagedLayer(layerId, spectral.select(bands).updateMask(spatialMask), visRaw, 'Raw ' + s + ' - ' + dateStr);
                }
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
        });

        // Remover camadas que não estão mais marcadas
        Object.keys(managedLayers).forEach(function (id) {
            if (desiredLayerIds.indexOf(id) === -1) {
                Map.layers().remove(managedLayers[id]);
                delete managedLayers[id];
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
                panel_stats.add(ui.Label('⚠️ Error recalculando stats', { fontSize: '10px', color: 'red' }));
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
            label: '📍',
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
        });

        // Atualiza a gaveta de períodos
        updatePeriodDrawer();

        // Atualiza a lista de amostras no Asset para a aba IMPORTAR
        try {
            var assetList = ee.data.listAssets(conf.asset_samples);
            var sample_list = assetList ? assetList.assets : [];
            var items = sample_list ? sample_list.map(function (obj) { return { label: obj.id.split('/').slice(-1)[0], value: obj.id }; }) : [];
            select_address.items().reset(items);
            if (items.length > 0) {
                select_address.setPlaceholder('Elija muestra antiga...');
            } else {
                select_address.setPlaceholder('Sin muestras em Asset');
            }
        } catch (e) {
            select_address.items().reset([]);
            select_address.setPlaceholder('Sin muestras em Asset');
            console.log('Error listing assets:', e);
        }
    }

    // ==========================================
    // CARD 1: FILTROS
    // ==========================================
    function createCabinet(title, isOpen) {
        var panel = ui.Panel({ style: { margin: '4px 0px', padding: '2px', border: '1px solid #dcdcdc', borderRadius: '4px', backgroundColor: '#fdfdfd' } });
        var content = ui.Panel({ style: { margin: '0px', padding: '0px', backgroundColor: '#fdfdfd' } });
        var header = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: { margin: '2px 0px', padding: '1px', backgroundColor: '#f0f0f0', border: '1px solid #ddd' } });

        var iconKey = isOpen ? 'arraw_v' : 'arraw_>';
        var toggleBtn = ui.Button({ imageUrl: b64.get(iconKey), style: { margin: '0px', padding: '0px', backgroundColor: 'ffffff00' } });

        header.add(toggleBtn).add(ui.Label(title, { fontSize: '18px', fontWeight: 'bold', margin: '1px 4px', color: '#444', backgroundColor: 'ffffff00' }));
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

    // 1. Define sub-drawers for Reference
    var extraCheckboxes = {};
    var drawerAQ = createLayerDrawer(L.lbl_burned, [
        { id: 'mcd64a1', label: 'MODIS BA', value: false },
        { id: 'gabam', label: 'GABAM', value: false },
        { id: 'fire_cci', label: 'FIRE_CCI', value: false },
        { id: 'peru_ref', label: 'Cicatrizes Peru', value: false }
    ]);
    var drawerFocos = createLayerDrawer(L.lbl_hotspots, [
        { id: 'buffer_inpe', label: 'Buffer Focos', value: false },
        { id: 'hotspots_inpe', label: 'Hotspots INPE', value: false }
    ]);
    drawerAQ.panel.style().set('shown', true); drawerFocos.panel.style().set('shown', true);

    // 2. Define sub-drawers for Satellites
    var drawerAsset = createLayerDrawer(L.lbl_asset_mosaics, [
        { id: 'sentinel2', label: 'Sentinel2', value: true }
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

    // 3. Define the main toggle drawer (now includes Satellites)
    var drawerRefToggle = createLayerDrawer(L.lbl_ref_cats, [
        { id: 'aq', label: L.lbl_burned, value: true, onChange: function (v) { drawerAQ.panel.style().set('shown', v); } },
        { id: 'focos', label: L.lbl_hotspots, value: true, onChange: function (v) { drawerFocos.panel.style().set('shown', v); } },
        { id: 'sats', label: L.lbl_satellites_toggle, value: true, onChange: function (v) { drawerAsset.panel.style().set('shown', v); drawerRaw.panel.style().set('shown', v); } }
    ]);

    // 4. Add to cabinet in the desired order
    cabLayers.content.add(drawerRefToggle.panel);
    cabLayers.content.add(drawerAsset.panel);
    cabLayers.content.add(drawerRaw.panel);
    cabLayers.content.add(drawerAQ.panel).add(drawerFocos.panel);

    // Mesclar os checkboxes para o gerenciamento global
    Object.keys(drawerAQ.checkboxes).forEach(function (k) { extraCheckboxes[k] = drawerAQ.checkboxes[k]; });
    Object.keys(drawerFocos.checkboxes).forEach(function (k) { extraCheckboxes[k] = drawerFocos.checkboxes[k]; });

    // --- CABINET 4: SAMPLES ---
    var cabSamples = createCabinet(L.cab_samples, true);
    panel_control.add(cabSamples.panel);

    // Sub-drawers panels
    var drawerInst = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };
    var drawerImp = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };
    var drawerAmo = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };
    var drawerExp = { panel: ui.Panel({ style: { shown: false, border: '1px solid #eee', margin: '2px' } }) };

    var drawerControl = createLayerDrawer('Dashboard', [
        { id: 'inst', label: L.cab_instructions.split(' ')[1], value: false, onChange: function (v) { drawerInst.panel.style().set('shown', v); } },
        { id: 'imp', label: L.tab_import.split(' ')[1], value: false, onChange: function (v) { drawerImp.panel.style().set('shown', v); } },
        { id: 'amo', label: L.cab_samples.split(' ')[1], value: true, onChange: function (v) { drawerAmo.panel.style().set('shown', v); if (v) updateStats(); } },
        { id: 'exp', label: L.tab_export.split(' ')[1], value: true, onChange: function (v) { drawerExp.panel.style().set('shown', v); if (v) { suggestNextVersion(); syncDateSelect(); } } }
    ]);
    drawerExp.panel.style().set('shown', true);
    drawerAmo.panel.style().set('shown', true);

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
    var btnHand = ui.Button({ label: '✋', style: { margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: function () { Map.drawingTools().setShape(null); } });
    var btnClear = ui.Button({ label: '🧹', style: { margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: clearDrawingTools });
    var btnCenter = ui.Button({ label: '📍', style: { margin: '1px', padding: '0px', stretch: 'horizontal' }, onClick: centerDrawingTools });

    rowDraw.add(btnFire).add(btnNotFire).add(btnHand).add(btnClear).add(btnCenter);

    drawerAmo.panel.add(rowDraw);
    drawerAmo.panel.add(panel_stats);
    // Export and Import will be populated below...

    // ==========================================
    // ABA: IMPORTAR
    // ==========================================
    var select_address = ui.Select({ style: styles.input });

    var btt_import_action = ui.Button({
        imageUrl: ICONS.load, style: styles.btn_blue,
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
    row_imp.add(select_address).add(btt_import_action);
    drawerImp.panel.add(row_imp);

    // ==========================================
    // ABA: EXPORTAR
    // ==========================================

    // --- Versão automática ---
    var lab_version_status = ui.Label(L.ver_checking, { fontSize: '10px', color: '#888', margin: '1px' });
    var txt_version = ui.Textbox({ placeholder: 'v0001', value: 'v0001', onChange: updateExportPreview, style: { margin: '1px', padding: '0px', width: '55px' } });

    function suggestNextVersion() {
        lab_version_status.setValue(L.ver_checking).style().set('color', '#888');
        var conf = countryConfigs[getSelectedCountry()];
        try {
            var assetList = ee.data.listAssets(conf.asset_samples);
            var assets = assetList ? assetList.assets : [];
            if (!assets || assets.length === 0) {
                txt_version.setValue('v0001');
                lab_version_status.setValue(L.ver_empty).style().set('color', '#e65100');
                updateExportPreview();
                return;
            }
            var maxV = 0;
            assets.forEach(function (a) {
                var fname = a.id.split('/').slice(-1)[0];
                var m = fname.match(/v(\d{4})/);
                if (m) {
                    var n = parseInt(m[1], 10);
                    if (n > maxV) maxV = n;
                }
            });
            var next = 'v' + ('000' + (maxV + 1)).slice(-4);
            txt_version.setValue(next);
            lab_version_status.setValue(L.ver_suggested + next).style().set('color', '#0f9d58');
        } catch (e) {
            txt_version.setValue('v0001');
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
        var maxYear = today.getFullYear();
        var maxMonth = today.getMonth(); // 0-indexed, so this is the previous month
        if (maxMonth === 0) { maxMonth = 12; maxYear--; }
        // Meses (mais recente primeiro)
        for (var y = maxYear; y >= 2019; y--) {
            var mEnd = (y === maxYear) ? maxMonth : 12;
            for (var m = mEnd; m >= 1; m--) {
                var mm = m < 10 ? '0' + m : m.toString();
                items.push({ label: y + '_' + mm, value: y + '_' + mm });
            }
        }
        // Anos (mais recente primeiro)
        for (var yr = maxYear; yr >= 2019; yr--) {
            items.push({ label: '' + yr, value: '' + yr });
        }
        return items;
    }

    function syncDateSelect() {
        select_date_export.items().reset(buildDateSelectItems());
        var periods = getSelectedPeriods();
        if (periods.length > 0) select_date_export.setValue(periods[0]);
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

    function updateExportPreview() {
        var ver = txt_version.getValue() || 'v0001';
        var sn = txt_shortname.getValue() ? redundanceReplace(txt_shortname.getValue()) : '';
        var dt = select_date_export.getValue();

        lab_date_error.style().set('shown', !dt);

        var dt_label = dt || 'YYYY';
        var parts = [ver];
        if (sn) parts.push(sn);
        parts.push(redundanceReplace(dt_label));
        lab_export_preview.setValue('📄 ' + parts.join('_'));
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
        var ver = txt_version.getValue() || 'v0001';
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
            var ver = txt_version.getValue() || 'v0001';
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
                description: 'samples_toAsset_' + desc,
                assetId: conf.asset_samples + '/' + desc
            });
            Export.table.toCloudStorage({
                collection: vec,
                description: 'samples_toGCS_' + desc,
                bucket: conf.bucket,
                fileNamePrefix: conf.gcs_samples + '/' + desc,
                fileFormat: 'CSV'
            });
            print(L.task_created + desc + L.task_hint);
        }
    });

    // --- Montar o panel_export ---
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
