# MapBiomas Fire Monitor — M7 / M8 / M9 Scripts

JavaScript (GEE Code Editor) scripts for MONITOR_01 post-classification pipeline.

## Scripts

| Script | Stage | Description |
|---|---|---|
| `M7_00_selection_merge.js` | M7 — UI | Form (campaign/sensor/mosaic/periodicity/version) + period selection + national image export |
| `M7_01_run_merge.js` | M7 — Merge | Merge 2+ models into single national image |
| `M7_02_morphology_filters.js` | M7 — Morph | Opening/closing filters |
| `M7_03_lulc_filters.js` | M7 — LULC | LULC mask by region (Collection 3) |
| `M7_04_hotspot_filters.js` | M7 — Hotspots | Hotspot buffer exemption (regions 1-4) |
| `M8_01_promote_candidate.js` | M8 — Candidate | Promote -ft04 to CANDIDATES/ |
| `M8_02_traceability.js` | M8 — Trace | Filter stage gain/loss |
| `M8_03_export_looker.js` | M8 — Looker | CSV for Looker Studio |
| `M9_01_evaluation.js` | M9 — Evaluate | Quality checklist |
| `M9_02_promote_prepublic.js` | M9 — Pre-public | Promote to PRE_PUBLIC/ |

## Naming

- Folders: `FILTERED/`, `CANDIDATES/`, `PRE_PUBLIC/` (UPPER)
- Collections: `{campanha}-{sensor}_{mosaico}_{periodicidade}_{versao}[-ft{N}]` (lower)
- Images: `{ano}` or `{ano}_{mes}` (lower)
- Bands: `probability` + `dayOfYear`

## Asset paths

```
CATALOG_01/MONITOR_01/LIBRARY_CLASSIFICATIONS/
├── FILTERED/{collection}-ft{0..4}/{period}
├── CANDIDATES/{collection}/{period}
└── PRE_PUBLIC/{campanha}/{period}
```
