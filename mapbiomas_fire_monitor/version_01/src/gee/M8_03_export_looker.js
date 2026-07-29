/* ============================================================
MAPBIOMAS FUEGO - MONITOR_01 - M8_03
Export Consolidado para Looker Studio

📅 DATA: julho 2026
🏷️ VERSAO: 4.5
============================================================ */

var CSV_AREA_QUEIMADA = [];
var CSV_RASTREABILIDADE = [];

print('=== M8_03 — Looker Studio Export ===');
print('');
var consolidated = ['period,collection,stage,area_ha,delta_ha,delta_pct,data,tipo'];
if (CSV_AREA_QUEIMADA.length > 1) {
    for (var i = 1; i < CSV_AREA_QUEIMADA.length; i++) {
        var r = CSV_AREA_QUEIMADA[i]; if (!r || r.trim() === '') continue;
        var parts = r.split(',');
        consolidated.push([parts[0] || '', parts[1] || '', 'candidate', parts[2] || '', '', '', parts[3] || '', 'area_final'].join(','));
    }
}
if (CSV_RASTREABILIDADE.length > 1) {
    for (var j = 1; j < CSV_RASTREABILIDADE.length; j++) {
        var r2 = CSV_RASTREABILIDADE[j]; if (!r2 || r2.trim() === '') continue;
        var p = r2.split(',');
        consolidated.push([PERIOD || '', COLLECTION_BASE || '', p[0] + '->' + p[1], p[3] || p[2] || '', p[4] || '', p[5] || '', '', 'traceability'].join(','));
    }
}
print('--- CSV Consolidado ---');
print(consolidated.join('\n'));
print('Cole no Google Sheets e conecte ao Looker Studio.');
print('=== M8_03 done ===');
