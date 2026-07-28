# MapBiomas Fire Monitor — M7/M8/M9 Scripts

JavaScript scripts for the MapBiomas Fire Monitor (MONITOR_01 campaign, Sentinel-2, Peru).

## Overview

| Script | Stage | Description |
|---|---|---|
| `M7_00_selection_merge.js` | M7 - UI | Selection interface: view min NBR mosaic, list available classifications per region, select with checkboxes, export to named folder |
| `M7_01_run_merge.js` | M7 - Merge | Merge 2+ classifications for same region using `where(img.gt(0), img)` pixel-level logic |
| `M7_02_morphology_filters.js` | M7 - Morph | Opening/closing filters (`focalMin` + `focalMax`), configurable radius, national or per-region |
| `M7_03_lulc_filters.js` | M7 - LULC | Land cover mask by region (MapBiomas Peru Collection 3), 90m water buffer, solitary pixel removal |
| `M7_04_hotspot_filters.js` | M7 - Hotspots | Hotspot buffer exemption (5km) for classes [66,12,13] in regions 1-4 |
| `M8_01_promote_candidate.js` | M8 - Candidate | Promote filtered version to M8_CANDIDATES/, compute burned area stats per region |
| `M8_02_traceability.js` | M8 - Trace | Compare consecutive filter stages, compute gain/loss per stage |
| `M8_03_export_looker.js` | M8 - Export | Consolidate stats CSV for Looker Studio dashboard |
| `M9_01_evaluation.js` | M9 - Evaluate | Quality checklist: area threshold, visual consistency, MODIS overlap, spatial coverage |
| `M9_02_promote_prepublic.js` | M9 - Publish | Promote approved candidate to M9_PRE_PUBLIC/ with full provenance metadata |

## Configuration

All scripts use top-level variables for configuration. Edit the block marked `═══ EDITE AQUI ═══` in each script:

- `FASE`: M7 filter phase name (e.g. `fase_agosto_v1`)
- `SUFIXO_ENTRADA`: input stage suffix (e.g. `_m7_01`, `_m7_02`)
- `CAMPAIGN`: campaign name (default: `MONITOR_01`)
- Additional filter-specific params (radius, mask dict, hotspot buffer, etc.)

## Directory Structure (GEE/GCS)

```
CATALOG_01/MONITOR_01/LIBRARY_CLASSIFICATIONS/
├── REGIONAL/{model_id}/              ← M6 output (existing)
├── M7_FILTERED/
│   └── {fase}/
│       ├── {mod}_{reg}_{per}.tif            (M7_00)
│       ├── {mod}_{reg}_{per}_m7_01.tif      (M7_01 merge)
│       ├── {mod}_{reg}_{per}_m7_02.tif      (M7_02 morph)
│       ├── {mod}_{reg}_{per}_m7_03.tif      (M7_03 LULC)
│       └── {mod}_{reg}_{per}_m7_04.tif      (M7_04 hotspots)
├── M8_CANDIDATES/
│   └── {mod}_{reg}_{per}_candidate.tif      (M8_01)
└── M9_PRE_PUBLIC/
    └── {mod}_{reg}_{per}_prepublic.tif      (M9_02)
```

## Naming Convention

| Stage | Suffix | Example |
|---|---|---|
| M7_00 | (none) | `training_0001_region3_2025_08` |
| M7_01 | `_m7_01` | `training_0001_region3_2025_08_m7_01` |
| M7_02 | `_m7_02` | `training_0001_region3_2025_08_m7_02` |
| M7_03 | `_m7_03` | `training_0001_region3_2025_08_m7_03` |
| M7_04 | `_m7_04` | `training_0001_region3_2025_08_m7_04` |
| M8_01 | `_candidate` | `training_0001_region3_2025_08_candidate` |
| M9_02 | `_prepublic` | `training_0001_region3_2025_08_prepublic` |

## Operational Workflow

```
Period  Analyst 1: M0 -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 (publish)
        Analyst 2: M7_00 (select + export to folder)
        Analyst 2: M7_01 -> M7_02 -> M7_03 -> M7_04 (apply filters)
        Analyst 3: M8_01 (promote to candidate)
        Analyst 3: M8_02 (traceability) -> M8_03 (Looker Studio export)
    Supervisor: M9_01 (evaluate checklist)
    Supervisor: M9_02 (approve -> PRE_PUBLIC)
```

## Languages

UI scripts (M7_00) support: `pt`, `es`, `en`, `fr`, `id`.  
Set `APP_LANG` variable at the top of the script.

## References

- Legacy Collection 1: `4-Collection_anual_final_products/peru/` (Landsat 30m annual)
- M3 Toolkit: `5-Monitor-Fuego/Toolkit_Monitor_Fuego` (UI pattern reference)
- MapBiomas Peru Collection 3 LULC: `projects/mapbiomas-public/assets/peru/collection3/`
- Fire regions: `projects/mapbiomas-peru/assets/FIRE/AUXILIARY_DATA/regiones_fuego_peru_v1`
- Hotspots: `projects/workspace-ipam/assets/FOGO/monthly-focus-sul-america/`
