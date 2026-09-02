# MapBiomas Fire Monitor — M7 / M8 / M9 Scripts

JavaScript (GEE Code Editor) scripts for MONITOR_01 post-classification pipeline.
Sincronizado com `mapbiomas-fire/5-Monitor-Fuego` (M7 v4.7, M8 v1.0, M9 v2.0).

## Scripts

| Script | Stage | Description |
|---|---|---|
| `M7_00_selection_merge.js` | M7 — UI | Form (campaign + collection + period) + model-per-region selection + national image export |
| `M7_01_morphology_filters.js` | M7 — ft01 | Opening/closing filters |
| `M7_02_lulc_filters.js` | M7 — ft02 | LULC mask by region (Collection 3) |
| `M7_03_hotspot_filters.js` | M7 — ft03 | Hotspot buffer exemption (regions 1-4) |
| `M8_statistics.js` | M8 — Stats | Universal statistics generator (area + LULC) for Looker Studio |
| `M9_00_promote_ui.js` | M9 — UI | Promote candidates from CANDIDATES/ to PRE_PUBLIC/ |

## Naming

- Folders: `FILTERED/`, `CANDIDATES/`, `PRE_PUBLIC/` (UPPER)
- Collections: `{collection}/ft{NN}` (lower), ex: `propuesta_a/ft00`
- Images: `{ano}` or `{ano}_{mes}` (lower)
- Bands: `probability` + `dayOfYear`

## Multiple collections

`propuesta_a` e apenas o default. Para criar outra colecao:

- `M7_00`: digite o nome em "Criar nova" (ou selecione uma existente)
- `M7_01/02/03`: edite `COLLECTION_BASE` no topo do script (copie/duplique por colecao)
- `M8_statistics`: universal — `COLLECTIONS = []` varre todas automaticamente
- `M9_00`: dropdown de colecao carrega tudo que existe em `CANDIDATES/`

## Asset paths

```
CATALOG_01/MONITOR_01/LIBRARY_CLASSIFICATIONS/
├── FILTERED/{collection}/ft{00..03}/{period}
├── CANDIDATES/{collection}/{period}
├── PRE_PUBLIC/{campanha}/{period}
└── LIBRARY_STATISTICS/m8_{collection}.csv   (GCS)
```

## Time properties

Todos os assets exportados por M7/M8 carregam `system:time_start` e
`system:time_end` (periodo mensal) — usado pelo Looker Studio e ordenacao temporal.