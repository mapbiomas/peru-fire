/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8_03
Export Consolidado para Looker Studio

📅 DATA: julho 2026
🏷️ VERSAO: 1.0
👥 EQUIPE: MapBiomas Fuego - IPAM

📌 O QUE FAZ:
1. Consolida estatisticas de area queimada (M8_01) e rastreabilidade (M8_02)
2. Gera CSV unificado para importacao no Looker Studio
3. Salva CSV no GCS

🔧 CONFIGURACAO:
   Configure GCS_BUCKET e GCS_PATH para o destino do CSV.
   Rode M8_01 e M8_02 antes deste script e copie os CSVs do console.
============================================================ */

// ─── CONFIGURACAO ───────────────────────────────────────────────────────────
var GCS_BUCKET = 'mapbiomas-fire';
var GCS_PATH = 'sudamerica/peru/CATALOG_01/MONITOR_01/LIBRARY_CLASSIFICATIONS/M8_STATS/';

// ═══ EDITE AQUI ═══
// Cole aqui os CSVs gerados pelo M8_01 e M8_02 no console

var CSV_AREA_QUEIMADA = [
  // 'model_id,region,period,area_queimada_ha,etapa_filtro,data_promocao,fase_origem',
  // 'training_0001,region3,2025_08,12543.2,m7_03,2026-07-28,fase_agosto_v1',
];

var CSV_RASTREABILIDADE = [
  // 'fase,base,regiao,etapa_antes,etapa_depois,area_antes_ha,area_depois_ha,ganho_ha,perda_ha,delta_ha,delta_pct',
  // 'fase_agosto_v1,training_0001_region3_2025_08,region3,m7_00,m7_01,13200.0,12543.2,0.0,656.8,-656.8,-5.0',
];

// ═══════════════════

// ─── CONSOLIDAR ─────────────────────────────────────────────────────────────

print('=== M8_03 — Export Consolidado Looker Studio ===');
print('');

// Cabecalho do CSV consolidado
var consolidated = [
    'fase,model_id,region,period,etapa_filtro,area_queimada_ha,ganho_ha,perda_ha,delta_ha,delta_pct,data_promocao,tipo',
];

// Mescla area queimada com rastreabilidade
// A area queimada traz o valor FINAL (ultima etapa)
// A rastreabilidade traz o ganho/perda por transicao

// 1. Area queimada (tipo = 'area_final')
if (CSV_AREA_QUEIMADA.length > 1) {
    for (var i = 1; i < CSV_AREA_QUEIMADA.length; i++) {
        var row = CSV_AREA_QUEIMADA[i];
        if (!row || row.trim() === '') continue;
        consolidated.push(row + ',,,,area_final');
    }
}

// 2. Rastreabilidade (tipo = 'rastreabilidade')
if (CSV_RASTREABILIDADE.length > 1) {
    for (var j = 1; j < CSV_RASTREABILIDADE.length; j++) {
        var row2 = CSV_RASTREABILIDADE[j];
        if (!row2 || row2.trim() === '') continue;
        // Extrai model_id da base
        var parts = row2.split(',');
        var base = parts[1];
        var etapaAntes = parts[3];
        var etapaDepois = parts[4];

        // Extrai periodo da base (ultimos 7 caracteres: YYYY_MM ou YYYY)
        var period = base.substring(Math.max(0, base.length - 7)).replace(/_m7.*/, '');
        // Extrai model_id: tudo antes de _region
        var regionIdx = base.indexOf('_region');
        var modelId = regionIdx > 0 ? base.substring(0, regionIdx) : base;

        consolidated.push([
            parts[0],     // fase
            modelId,      // model_id
            parts[2],     // region
            period,       // period
            etapaDepois,  // etapa_filtro
            '',           // area_queimada_ha (vazio, vem do M8_01)
            parts[5],     // ganho_ha
            parts[6],     // perda_ha
            parts[7],     // delta_ha
            parts[8],     // delta_pct
            '',           // data_promocao
            'rastreabilidade',
        ].join(','));
    }
}

print('--- CSV Consolidado (copie para Google Sheets -> Looker Studio) ---');
print(consolidated.join('\n'));

// ─── EXPORTAR PARA GCS ──────────────────────────────────────────────────────

var csvContent = consolidated.join('\n');
var fileName = 'm8_stats_' + new Date().toISOString().split('T')[0].replace(/-/g, '') + '.csv';
var gcsUri = 'gs://' + GCS_BUCKET + '/' + GCS_PATH + fileName;

print('');
print('Para exportar para GCS, execute num notebook Python:');
print('');
print('  from M0_auth_config import _get_fs');
print('  fs = _get_fs()');
print('  csv_content = """' + csvContent.replace(/"/g, '\\"') + '"""');
print('  with fs.open("' + GCS_PATH + fileName + '", "w") as f:');
print('      f.write(csv_content)');
print('');
print('Ou cole o CSV acima diretamente no Google Sheets e conecte ao Looker Studio.');
print('');
print('=== M8_03 concluido ===');
