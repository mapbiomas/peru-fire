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
        asset_samples: 'projects/mapbiomas-peru/assets/FIRE/MONITOR/RAWSAMPLES',
        property: 'region_nam'
    }
};

// Variável global para armazenar a coleção de regiões ativa
var current_regiones = ee.FeatureCollection(countryConfigs['Peru'].asset_regions);

// --- CAMADAS DE VISUALIZAÇÃO DOS LIMITES ---
var layerMosaic = ui.Map.Layer(ee.Image(), { bands: ['swir1', 'nir', 'red'], min: 3, max: 40 }, 'Mosaico');
var layerAllRegions = ui.Map.Layer(ee.Image(), {}, 'Todas las Regiones');
var layerSelectedRegion = ui.Map.Layer(ee.Image(), {}, 'Región Seleccionada');
Map.layers().add(layerMosaic);
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
    panel.style().set({ position: 'bottom-left' });
    Map.add(panel);

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
        var sensor = select_sensor.getValue().toUpperCase();
        var periodType = select_periodicity.getValue().toUpperCase();
        var folderPeriod = (periodType === 'MENSAL') ? 'MONTHLY' : 'ANNUAL';
        var dateStr = select_period.getValue() ? select_period.getValue() : '';
        var pais = select_pais.getValue().toLowerCase();
        var sensor_lower = select_sensor.getValue().toLowerCase();
        
        var name = sensor_lower + '_fire_' + pais + '_' + dateStr;
        
        var bands = ['swir1', 'nir', 'red'];
        var img = ee.Image();
        
        // Uso de try-catch para evitar crash se a coleção não existir
        try {
            bands.forEach(function(b) {
                var colId = 'projects/mapbiomas-mosaics/assets/FIRE/' + sensor + '/' + folderPeriod + '/' + b;
                var bImg = ee.ImageCollection(colId).filter(ee.Filter.eq('name', name)).mosaic().rename(b);
                img = img.addBands(bImg);
            });
            layerMosaic.setEeObject(img.select(bands));
            layerMosaic.setShown(true);
        } catch(e) {
            print('Aviso: Mosaico não encontrado no Asset para ' + name);
            layerMosaic.setShown(false);
        }
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

    var select_sensor = ui.Select({
        items: ['sentinel2', 'landsat', 'modis', 'hls'], value: 'sentinel2',
        onChange: function (value) { updateExportLabel(); updateMosaic(); },
        style: styles.input
    });
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
    row0.add(ui.Label('Sensor:', { margin: '1px', padding: '0px', fontSize: '12px', width: '50px' })).add(select_sensor);
    row0.add(ui.Label('País:', { margin: '1px', padding: '0px', fontSize: '12px', width: '45px' })).add(select_pais);

    var row1 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row1.add(ui.Label('Región:', { margin: '1px', padding: '0px', fontSize: '12px', width: '45px' })).add(select_region).add(btt_center);

    var select_periodicity = ui.Select({
        items: ['Anual', 'Mensal'], value: 'Anual',
        onChange: function (val) {
            var newDates = getDynamicDates(val.toLowerCase());
            select_period.items().reset(newDates);
            select_period.setValue(newDates[newDates.length - 1]);
            updateExportLabel(); updateMosaic();
        },
        style: styles.input
    });

    var select_period = ui.Select({
        items: getDynamicDates('anual'), value: getDynamicDates('anual').slice(-1)[0],
    });

    var row2 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row2.add(ui.Label('Periodo:', { margin: '1px', padding: '0px', fontSize: '12px', width: '45px' })).add(select_periodicity).add(select_period);

    panel_control.add(row0).add(row1).add(row2);

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
        lab_export_preview.setValue(redundanceReplace('samples_fire_' + txt_version_export.getValue() + '_b24_' + safeRegion + '_' + safePeriod));
    }

    var btt_export_action = ui.Button({
        label: 'Salvar no Asset', style: styles.btn_green,
        onClick: function () {
            var fireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'fire' });
            var notFireLayer = Map.drawingTools().layers().filter(function (ly) { return ly.getName() === 'notFire' });
            if (fireLayer.length === 0 || notFireLayer.length === 0) return print('Erro: Faltam camadas "fire" ou "notFire".');

            var safeRegion = select_region.getValue();
            var safePeriod = select_period.getValue();
            var conf = countryConfigs[select_pais.getValue()];

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

            var landcover_vector = fireFeatures.merge(notFireFeatures);

            var desc = lab_export_preview.getValue();
            Export.table.toAsset({
                collection: landcover_vector,
                description: 'samples_vector_toAsset-' + desc,
                assetId: conf.asset_samples + '/' + desc
            });
            print('🚀 ATENÇÃO! Vá à aba "Tasks" no GEE para exportar: ' + desc);
        }
    });

    var row_exp1 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_exp1.add(ui.Label('Versión:', styles.label)).add(txt_version_export).add(lab_export_preview);

    var row_exp2 = ui.Panel({ layout: ui.Panel.Layout.flow('horizontal'), style: styles.row });
    row_exp2.add(btt_export_action);

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