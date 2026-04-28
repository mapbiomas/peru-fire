/********************************************
v10: Ferramenta Exclusiva de Coleta e Exportação de Amostras (Vetores)
- UI Ultra-Compacta e Margens (0~1px)
- Multi-País Dinâmico (Chile, Peru...)
- Busca automática de regiões via .aggregate_array().distinct().sort()
- Atualização dinâmica dos Assets de Destino/Origem
********************************************/

// Define o mapa base como Satélite
Map.setOptions('SATELLITE');

// --- CONFIGURAÇÃO DOS PAÍSES ---
var countryConfigs = {
    // 'Chile': {
    //   asset_regions: 'projects/mapbiomas-chile/assets/FIRE/AUXILIARY_DATA/regiones_fuego_chile_v1',
    //   asset_samples: 'projects/mapbiomas-chile/assets/FIRE/COLLECTION1/SAMPLES',
    //   property: 'region_nam'
    // },
    'Peru': {
        asset_regions: 'projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1',
        asset_samples: 'projects/mapbiomas-peru/assets/FIRE/MONITOR/VERSION_01/RAWSAMPLES',
        bucket: 'mapbiomas-fire',
        gcs_samples: 'sudamerica/peru/monitor/samples',
        property: 'region_nam'
    }
};

// Variável global para armazenar a coleção de regiões ativa
var current_regiones = ee.FeatureCollection(countryConfigs['Peru'].asset_regions);

// --- CAMADAS DE VISUALIZAÇÃO DOS LIMITES ---
var visAsset = { bands: ['swir1', 'nir', 'red'], min: 3, max: 40 };
var visRaw = { bands: ['swir1', 'nir', 'red'], min: 3, max: 40 };

var layersAsset = {
    'sentinel2': ui.Map.Layer(ee.Image().select(), visAsset, 'Asset - Sentinel 2', true),
    'landsat': ui.Map.Layer(ee.Image().select(), visAsset, 'Asset - Landsat', false),
    'hls': ui.Map.Layer(ee.Image().select(), visAsset, 'Asset - HLS', false),
    'modis': ui.Map.Layer(ee.Image().select(), visAsset, 'Asset - MODIS', false)
};

var layersRaw = {
    'sentinel2': ui.Map.Layer(ee.Image().select(), visRaw, 'Raw - Sentinel 2', false),
    'landsat': ui.Map.Layer(ee.Image().select(), visRaw, 'Raw - Landsat', false),
    'hls': ui.Map.Layer(ee.Image().select(), visRaw, 'Raw - HLS', false),
    'modis': ui.Map.Layer(ee.Image().select(), visRaw, 'Raw - MODIS', false),
    'planet': ui.Map.Layer(ee.Image().select(), { "opacity": 1, "bands": ["red", "green", "blue"], "min": 125, "max": 1858, "gamma": 1 }, 'Planet NICFI', false)
};

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

var layersExtra = {};
Object.keys(extraDatasets).forEach(function (key) {
    layersExtra[key] = ui.Map.Layer(ee.Image().select(), extraDatasets[key].vis, extraDatasets[key].name, false);
});

var extraCheckboxes = {};

var layerAllRegions = ui.Map.Layer(ee.Image(), {}, 'Todas las Regiones');
var layerSelectedRegion = ui.Map.Layer(ee.Image(), {}, 'Región Seleccionada');

Map.layers().add(layersAsset['landsat']);
Map.layers().add(layersAsset['sentinel2']);
Map.layers().add(layersAsset['hls']);
Map.layers().add(layersAsset['modis']);

Map.layers().add(layersRaw['landsat']);
Map.layers().add(layersRaw['sentinel2']);
Map.layers().add(layersRaw['hls']);
Map.layers().add(layersRaw['modis']);
Map.layers().add(layersRaw['planet']);

Object.keys(layersExtra).forEach(function (key) {
    Map.layers().add(layersExtra[key]);
});

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
        return dates;
    }

    // --- DICIONÁRIO DE ESTILOS (0~1px) ---
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

    // --- ESTRUTURA BASE ---
    var panel = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.main_panel });
    panel.style().set({ width: '350px' });
    ui.root.insert(0, panel);

    var panel_head = ui.Panel({ layout: ui.Panel.Layout.flow('vertical'), style: styles.row });
    var panel_body = ui.Panel({ style: { margin: '0px', padding: '0px' } });
    panel.add(panel_head).add(panel_body);

    var logo = ui.Button({ imageUrl: b64.get('logo_mapbiomas_fuego'), style: { margin: '1px', padding: '0px' } });
    var title = ui.Label('🔥 MapBiomas-Fuego | Coleta', { fontSize: '15px', fontWeight: 'bold', color: '#222', margin: '1px', stretch: 'horizontal' });
    panel_head.add(logo).add(title);

    var panel_control = ui.Panel({ style: styles.card });
    var panel_samples = ui.Panel({ style: styles.card });
    panel_body.add(panel_control).add(panel_samples);

    // ==========================================
    // FUNÇÕES GERAIS DE MAPA / DESENHO
    // ==========================================

    function updateMosaic() {
        var periodType = select_periodicity.getValue().toUpperCase();
        var folderPeriod = (periodType === 'MENSAL') ? 'MONTHLY' : 'ANNUAL';
        var dateStr = select_period.getValue() ? String(select_period.getValue()) : '';
        var pais = select_pais.getValue().toLowerCase();

        var bands = ['swir1', 'nir', 'red'];

        var year = parseInt(dateStr.split('_')[0], 10);
        var month = dateStr.indexOf('_') !== -1 ? parseInt(dateStr.split('_')[1], 10) : null;

        var start = month ? ee.Date.fromYMD(year, month, 1) : ee.Date.fromYMD(year, 1, 1);
        var end = month ? start.advance(1, 'month') : start.advance(1, 'year');

        var geom = current_regiones;
        if (select_region.getValue()) {
            geom = current_regiones.filter(ee.Filter.eq(countryConfigs[select_pais.getValue()].property, select_region.getValue()));
        }
        var bounds = geom.geometry().bounds();

        ['sentinel2', 'landsat', 'modis', 'hls', 'planet'].forEach(function (s) {
            if (s !== 'planet') {
                var name = s + '_fire_' + pais + '_' + dateStr;
                var imgAsset = ee.Image().select();
                try {
                    bands.forEach(function (b) {
                        var colId = 'projects/mapbiomas-mosaics/assets/FIRE/' + s.toUpperCase() + '/' + folderPeriod + '/' + b + '/' + name + '_' + b;
                        var bImg = ee.Image(colId);
                        imgAsset = imgAsset.addBands(bImg);
                    });
                    layersAsset[s].setEeObject(imgAsset.select(bands));
                } catch (e) {
                    print('Erro ao carregar asset: ' + name, e);
                    layersAsset[s].setEeObject(ee.Image().select());
                }
            }

            if (rawCheckboxes[s] && rawCheckboxes[s].getValue()) {
                if (s === 'planet') {
                    var planetCol = ee.ImageCollection('projects/planet-nicfi/assets/basemaps/americas')
                        .filterDate(start, end).filterBounds(bounds)
                        .map(function (img) { return img.select(['B', 'G', 'R', 'N'], ['blue', 'green', 'red', 'nir']); });
                    layersRaw[s].setEeObject(planetCol.mosaic().select(['red', 'green', 'blue']));
                    return;
                }

                var rawCol = ee.ImageCollection([]);
                var multiplier = 100;

                if (s === 'landsat') {
                    var sensor_logic = {
                        '1984_1998': ['L5'],
                        '1999_2012': ['L5', 'L7'],
                        '2013_2021': ['L7', 'L8'],
                        '2022_2026': ['L8', 'L9']
                    };
                    var current_constellation = year < 1999 ? sensor_logic['1984_1998'] :
                        year <= 2012 ? sensor_logic['1999_2012'] :
                            year <= 2021 ? sensor_logic['2013_2021'] :
                                sensor_logic['2022_2026'];

                    if (current_constellation.indexOf('L9') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS89));
                    if (current_constellation.indexOf('L8') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS89));
                    if (current_constellation.indexOf('L7') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LE07/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS57));
                    if (current_constellation.indexOf('L5') !== -1) rawCol = rawCol.merge(ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").filterDate(start, end).filterBounds(bounds).map(processLS57));
                    multiplier = 100;
                } else if (s === 'sentinel2') {
                    rawCol = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate(start, end).filterBounds(bounds)
                        .linkCollection(ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED'), ['cs']).map(processS2);
                    multiplier = 0.01;
                } else if (s === 'modis') {
                    rawCol = ee.ImageCollection("MODIS/061/MOD09A1").merge(ee.ImageCollection("MODIS/061/MYD09A1"))
                        .filterDate(start, end).filterBounds(bounds).map(processMODIS);
                    multiplier = 0.01;
                } else if (s === 'hls') {
                    var s30_col = ee.ImageCollection("NASA/HLS/HLSS30/v002").filterDate(start, end).filterBounds(bounds).map(processHLS_S30);
                    var l30_col = ee.ImageCollection("NASA/HLS/HLSL30/v002").filterDate(start, end).filterBounds(bounds).map(processHLS_L30);
                    rawCol = s30_col.merge(l30_col);
                    multiplier = 100;
                }

                var mosaicRaw = rawCol.qualityMosaic('nbr');
                var spectral = mosaicRaw.select(['blue', 'green', 'red', 'nir', 'swir1', 'swir2']).multiply(multiplier).byte();
                layersRaw[s].setEeObject(spectral.select(bands));
            } else {
                layersRaw[s].setEeObject(ee.Image().select());
            }
        });

        Object.keys(extraDatasets).forEach(function (key) {
            if (typeof extraCheckboxes !== 'undefined' && extraCheckboxes[key] && extraCheckboxes[key].getValue()) {
                layersExtra[key].setEeObject(extraDatasets[key].build(start, end, bounds, year, month));
            } else {
                layersExtra[key].setEeObject(ee.Image().select());
            }
        });
    }

    function updateSelectedRegionMap(regionName) {
        if (!regionName) return;
        var selectedFc = current_regiones.filter(ee.Filter.eq(countryConfigs[select_pais.getValue()].property, regionName));
        layerSelectedRegion.setEeObject(selectedFc.style({ color: 'ff0000', fillColor: '00000000', width: 3 }));
        Map.centerObject(selectedFc);
    }

    function clearDrawingTools() {
        var layers = Map.drawingTools().layers();
        for (var i = layers.length() - 1; i >= 0; i--) {
            var l = layers.get(i);
            if (l.getName() === 'fire' || l.getName() === 'notFire') {
                layers.remove(l);
            }
        }
    }

    // ==========================================
    // LÓGICA DE TROCA DE PAÍS (Multi-Country)
    // ==========================================
    function loadCountryData(countryName) {
        var conf = countryConfigs[countryName];
        current_regiones = ee.FeatureCollection(conf.asset_regions);

        // Atualiza bordas de todas as regiões no mapa
        layerAllRegions.setEeObject(current_regiones.style({ color: 'ffffff', fillColor: '00000000', width: 1 }));
        layerSelectedRegion.setEeObject(ee.Image()); // Limpa o vermelho

        // Trava o dropdown enquanto carrega
        select_region.setPlaceholder('Cargando regiones...');
        select_region.setDisabled(true);
        select_region.items().reset([]);

        // Busca regiões de forma dinâmica
        current_regiones.aggregate_array(conf.property).distinct().sort().evaluate(function (list) {
            select_region.setDisabled(false);
            if (!list || list.length === 0) {
                select_region.setPlaceholder('No se encontraron regiones');
                return;
            }
            select_region.items().reset(list);
            select_region.setValue(list[0]);
        });

        // Atualiza a lista de amostras no Asset para a aba IMPORTAR
        try {
            var sample_list = ee.data.listAssets(conf.asset_samples).assets;
            var items = sample_list ? sample_list.map(function (obj) { return { label: obj.id.split('/').slice(-1)[0], value: obj.id }; }) : [];
            select_address.items().reset(items);
            select_address.setPlaceholder('Elija muestra antigua...');
        } catch (e) {
            select_address.items().reset([]);
            select_address.setPlaceholder('Sin muestras en Asset');
        }
    }

    // ==========================================
    // CARD 1: FILTROS
    // ==========================================
    panel_control.add(ui.Label('⚙️ FILTROS', styles.title));

    var select_pais = ui.Select({
        items: Object.keys(countryConfigs), value: 'Peru',
        onChange: function (value) { loadCountryData(value); },
        style: styles.input
    });

    var select_region = ui.Select({
        onChange: function (value) {
            updateSelectedRegionMap(value);
            updateExportLabel(); updateMosaic();
        },
        style: styles.input
    });

    var btt_center = ui.Button({
        label: '📍 Centralizar', style: styles.btn_blue,
        onClick: function () { Map.centerObject(current_regiones.filter(ee.Filter.eq(countryConfigs[select_pais.getValue()].property, select_region.getValue()))); }
    });

    var row0 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row0.add(ui.Label('País:', { margin: '1px', padding: '0px', fontSize: '12px', width: '45px' })).add(select_pais);
    row0.add(ui.Label('Región:', { margin: '1px', padding: '0px', fontSize: '12px', width: '45px' })).add(select_region).add(btt_center);

    var select_periodicity = ui.Select({
        items: ['Anual', 'Mensal'], value: 'Mensal',
        onChange: function (val) {
            var newDates = getDynamicDates(val.toLowerCase());
            select_period.items().reset(newDates);
            select_period.setValue(newDates[newDates.length - 1]);
            updateExportLabel(); updateMosaic();
        },
        style: styles.input
    });

    var select_period = ui.Select({
        items: getDynamicDates('mensal'),
        value: getDynamicDates('mensal').slice(-1)[0],
        style: styles.input,
        onChange: function (value) {
            updateExportLabel();
            updateMosaic();
        }
    });

    var row1 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row1.add(ui.Label('Periodo:', { margin: '1px', padding: '0px', fontSize: '12px', width: '45px' })).add(select_periodicity).add(select_period);

    panel_control.add(row0).add(row1);

    // ==========================================
    // MÓDULO DE GAVETAS DE CAMADAS (EXPANSÍVEL)
    // ==========================================
    function createLayerDrawer(title, options) {
        var panel = ui.Panel({ style: { margin: '2px 0px', padding: '2px', border: '1px solid #ccc', backgroundColor: '#f9f9f9' } });

        var flowPanel = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal', true), style: { margin: '0px', padding: '0px', backgroundColor: '#f9f9f9' } });
        var checkboxes = {};

        options.forEach(function (opt) {
            var chk = ui.Checkbox({
                label: opt.label,
                value: opt.value || false,
                onChange: function (checked) {
                    if (opt.layer) opt.layer.setShown(checked);
                    if (opt.onChange) opt.onChange(checked);
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

    // Gaveta 1: Mosaicos Oficiais (Asset)
    var drawerAsset = createLayerDrawer('Mosaicos Oficiais (Asset)', [
        { id: 'sentinel2', label: 'S2', value: true, layer: layersAsset['sentinel2'] },
        { id: 'landsat', label: 'L8/9', value: false, layer: layersAsset['landsat'] },
        { id: 'modis', label: 'MODIS', value: false, layer: layersAsset['modis'] },
        { id: 'hls', label: 'HLS', value: false, layer: layersAsset['hls'] }
    ]);
    panel_control.add(drawerAsset.panel);

    // Gaveta 2: Mosaicos Originais (Raw - Lento)
    var drawerRaw = createLayerDrawer('Mosaicos Originais (Raw - Lento)', [
        { id: 'sentinel2', label: 'S2', value: false, layer: layersRaw['sentinel2'], onChange: function () { updateMosaic(); } },
        { id: 'landsat', label: 'L8/9', value: false, layer: layersRaw['landsat'], onChange: function () { updateMosaic(); } },
        { id: 'modis', label: 'MODIS', value: false, layer: layersRaw['modis'], onChange: function () { updateMosaic(); } },
        { id: 'hls', label: 'HLS', value: false, layer: layersRaw['hls'], onChange: function () { updateMosaic(); } },
        { id: 'planet', label: 'Planet', value: false, layer: layersRaw['planet'], onChange: function () { updateMosaic(); } }
    ]);
    panel_control.add(drawerRaw.panel);

    // Alimenta a variável global para que updateMosaic() saiba quais processar
    rawCheckboxes = drawerRaw.checkboxes;

    // Gaveta 3: Dados de Referência
    var extraOptions = Object.keys(extraDatasets).map(function (key) {
        return {
            id: key,
            label: extraDatasets[key].name,
            value: false,
            layer: layersExtra[key],
            onChange: function () { updateMosaic(); }
        };
    });
    var drawerExtra = createLayerDrawer('Dados de Referência', extraOptions);
    panel_control.add(drawerExtra.panel);

    extraCheckboxes = drawerExtra.checkboxes;

    // ==========================================
    // CARD 2: AMOSTRAS (IMPORT / EXPORT)
    // ==========================================
    var row_samples_title = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_samples_title.add(ui.Label('🖍️ MUESTRAS (Polígonos)', { margin: '1px', padding: '2px', fontSize: '13px', fontWeight: 'bold', color: '#333', stretch: 'horizontal' }));

    var btt_clear = ui.Button({ label: '🧹 Limpiar', style: styles.btn_red, onClick: clearDrawingTools });
    row_samples_title.add(btt_clear);
    panel_samples.add(row_samples_title);

    var panel_tabs = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    var panel_tab_body = ui.Panel({ style: { margin: '0px', padding: '0px' } });
    panel_samples.add(panel_tabs).add(panel_tab_body);

    var btt_imp = ui.Button({ label: '📥 IMPORTAR', style: styles.tab_active });
    var btt_exp = ui.Button({ label: '📤 EXPORTAR', style: styles.tab_inactive });
    panel_tabs.add(btt_imp).add(btt_exp);

    var panel_import = ui.Panel({ style: { margin: '0px', padding: '0px' } });
    var panel_export = ui.Panel({ style: { margin: '0px', padding: '0px' } });
    panel_tab_body.add(panel_import);

    btt_imp.onClick(function () {
        btt_imp.style().set(styles.tab_active); btt_exp.style().set(styles.tab_inactive);
        panel_tab_body.clear(); panel_tab_body.add(panel_import);
    });
    btt_exp.onClick(function () {
        btt_exp.style().set(styles.tab_active); btt_imp.style().set(styles.tab_inactive);
        panel_tab_body.clear(); panel_tab_body.add(panel_export);
    });

    // --- ABA: IMPORTAR ---
    var select_address = ui.Select({ style: styles.input });

    var btt_import_action = ui.Button({
        label: 'Carregar', style: styles.btn_blue,
        onClick: function () {
            var id = select_address.getValue();
            if (!id) return;
            var parts = id.split('_');
            var lastPart = parts[parts.length - 1], penultPart = parts[parts.length - 2];
            var recoveredPeriod = (!isNaN(penultPart) && !isNaN(lastPart)) ? (penultPart + '_' + lastPart) : lastPart;
            select_periodicity.setValue((!isNaN(penultPart) && !isNaN(lastPart)) ? 'Mensal' : 'Anual', false);

            var newDates = getDynamicDates(select_periodicity.getValue().toLowerCase());
            select_period.items().reset(newDates); select_period.setValue(recoveredPeriod, false);

            // Busca inteligente da região (Não precisa mais de dicionário hardcoded)
            var matchedRegion = null;
            var currentRegionsList = select_region.items().get();
            for (var i = 0; i < currentRegionsList.length; i++) {
                if (id.indexOf(currentRegionsList[i]) !== -1) {
                    matchedRegion = currentRegionsList[i];
                    break;
                }
            }

            if (matchedRegion) {
                select_region.setValue(matchedRegion, false);
                updateSelectedRegionMap(matchedRegion);
            }
            updateExportLabel();

            clearDrawingTools();

            ee.FeatureCollection(id).filter(ee.Filter.eq('fire', 1)).geometry().coordinates().map(function (list) { return ee.Geometry.Polygon(list); })
                .evaluate(function (geomList) { Map.drawingTools().addLayer({ geometries: geomList, name: 'fire', color: 'ff0000', shown: true }); });
            ee.FeatureCollection(id).filter(ee.Filter.eq('fire', 0)).geometry().coordinates().map(function (list) { return ee.Geometry.Polygon(list); })
                .evaluate(function (geomList) { Map.drawingTools().addLayer({ geometries: geomList, name: 'notFire', color: '0000ff', shown: true }); });
        }
    });

    var row_imp = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_imp.add(select_address).add(btt_import_action);
    panel_import.add(row_imp);

    // --- ABA: EXPORTAR ---
    var txt_version_export = ui.Textbox({ placeholder: 'v1', value: 'v1', onChange: updateExportLabel, style: { margin: '1px', padding: '0px', width: '40px' } });
    var lab_export_preview = ui.Label({ value: '', style: { margin: '1px', fontSize: '11px', fontWeight: 'bold', color: '#0f9d58', stretch: 'horizontal' } });

    function updateExportLabel() {
        var safeRegion = select_region.getValue() ? select_region.getValue() : 'Cargando...';
        var safePeriod = select_period.getValue() ? select_period.getValue() : 'YYYY';
        lab_export_preview.setValue(redundanceReplace('samples_fire_' + txt_version_export.getValue() + '_' + safePeriod));
    }

    function getLandcoverVector() {
        var fireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'fire' });
        var notFireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'notFire' });
        if (fireLayer.length === 0 || notFireLayer.length === 0) {
            print('Erro: Faltam camadas "fire" ou "notFire".');
            return null;
        }

        var safeRegion = select_region.getValue();
        var safePeriod = select_period.getValue();

        var fireFeatures = ee.FeatureCollection(
            fireLayer[0].getEeObject().geometries().map(function (g) {
                return ee.Feature(ee.Geometry(g), { 'fire': 1, 'region': safeRegion, 'period': safePeriod });
            })
        );

        var notFireFeatures = ee.FeatureCollection(
            notFireLayer[0].getEeObject().geometries().map(function (g) {
                return ee.Feature(ee.Geometry(g), { 'fire': 0, 'region': safeRegion, 'period': safePeriod });
            })
        );

        return fireFeatures.merge(notFireFeatures);
    }

    var btt_export_asset = ui.Button({
        label: '💾 Salvar no Asset (GEE)', style: styles.btn_green,
        onClick: function () {
            var landcover_vector = getLandcoverVector();
            if (!landcover_vector) return;
            var conf = countryConfigs[select_pais.getValue()];
            var desc = lab_export_preview.getValue();
            Export.table.toAsset({
                collection: landcover_vector,
                description: 'samples_vector_toAsset-' + desc,
                assetId: conf.asset_samples + '/' + desc
            });
            print('🚀 ATENÇÃO! Vá à aba "Tasks" no GEE para exportar Asset: ' + desc);
        }
    });

    var btt_export_gcs = ui.Button({
        label: '☁️ Salvar no GCS (CSV)', style: styles.btn_blue,
        onClick: function () {
            var landcover_vector = getLandcoverVector();
            if (!landcover_vector) return;
            var conf = countryConfigs[select_pais.getValue()];
            var desc = lab_export_preview.getValue();
            Export.table.toCloudStorage({
                collection: landcover_vector,
                description: 'samples_vector_toGCS-' + desc,
                bucket: conf.bucket,
                fileNamePrefix: conf.gcs_samples + '/' + desc,
                fileFormat: 'CSV'
            });
            print('🚀 ATENÇÃO! Vá à aba "Tasks" no GEE para exportar CSV: ' + desc);
        }
    });

    var row_exp1 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_exp1.add(ui.Label('Versión:', styles.label)).add(txt_version_export).add(lab_export_preview);

    var row_exp2 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_exp2.add(btt_export_asset).add(btt_export_gcs);

    panel_export.add(row_exp1).add(row_exp2);

    // INICIA O APP (Gatilho inicial)
    loadCountryData('Peru');
    updateMosaic();
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
