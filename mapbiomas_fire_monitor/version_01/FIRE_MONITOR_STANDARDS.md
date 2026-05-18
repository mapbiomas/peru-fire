# Guide Star: MapBiomas Fire Development Standards

This document systematizes the architecture, interface, and performance standards established during the refactoring of the MapBiomas Fire Pipeline (Peru). The goal is to ensure that all modules (M0 to M7) inherit the same stability and design DNA.

---

## 1. Code Splitting Architecture

All modules should be split into two files for easier maintenance and to avoid Jupyter conflicts:

*   **`M#_logic.py`**: Contains only pure Earth Engine, GDAL, or file manipulation functions. Must NOT contain `ipywidgets`.
*   **`M#_ui.py`**: Contains the class that inherits from `PipelineStepUI`. Manages layout, buttons, and reactivity.

---

## 2. Pipeline Stage Overview (M0-M5)

Each pipeline stage has a well-defined responsibility:

### M0 — Setup and Authentication
Auto-detects Colab vs local environment, installs system dependencies (GDAL) and Python packages (gcsfs, rasterio, earthengine-api), configures GCS bucket and GEE project paths via `set_global_opts()`, authenticates with Earth Engine, sets the language locale, and registers the region featureCollection.

Key files: `M0_auth_config.py`, `M_regions.py`, `M_lang.py`

### M1 — Export (GEE → GCS)
Multi-sensor satellite image export pipeline. Handles Sentinel-2, Landsat 5/7/8/9, MODIS, and HLS collections. Applies sensor-specific radiometric corrections (TOA/SR conversion), cloud masking (QA_PIXEL, Fmask, CS), and exports optimized GeoTIFF chunks to GCS. Supports monthly and annual periods with configurable mosaic types (MINNBR, MINNBR_BUFFER).

Key files: `M1_export_logic.py`, `M1_export_ui.py`

### M2 — Mosaic Assembly (COG)
Assembles exported shards/chunks into full-region Cloud-Optimized GeoTIFFs. Uses GDAL VRT for virtual mosaic stacking, then translates to compressed COGs with DEFLATE compression. The result is a seamless, cloud-optimized raster ready for analysis and model inference.

Key files: `M2_mosaic_logic.py`, `M2_mosaic_ui.py`

### M3 — Sample Collection (GEE Toolkit JavaScript)
Training data collection via a custom GEE JavaScript Toolkit. Users interactively draw fire (burned) and notFire (unburned) polygons on satellite imagery layers. Samples are exported to GEE Assets and GCS with metadata (satellite, date, region, campaign). The toolkit supports multi-country configuration and multi-language UI (EN/ES/PT).

Key files: `M3_sample_ui.py`, `M3_toolkit.js`

### M4 — DNN Training
Deep Neural Network classification training. Uses a flexible band extraction matrix (`M4_data_extractor.py`) to sample pixel values from M2 mosaics using M3 polygon samples. Trains a DNN classifier (`M4_algorithms_dnn.py`) with configurable architecture (layers, neurons, dropout), generates t-SNE audit plots (`M4_analytics.py`), and saves model weights (protobuf) and metadata to GCS.

Key files: `M4_data_extractor.py`, `M4_hub_manager.py`, `M4_algorithms_dnn.py`, `M4_analytics.py`, `M4_ui.py`

### M5 — Classification
Regional tile-based burned area classification. Loads a trained DNN model from GCS, retrieves the cell grid (cim-world) for the target region (`M5_queue.py` manages job queue), and classifies each tile independently via `M5_inference.py`. Produces classified rasters, tile-level statistics (burned area by class), and regional aggregated statistics. Results are published back to GEE as ImageCollections.

Key files: `M5_classifier.py`, `M5_classifier_ui.py`, `M5_queue.py`, `M5_inference.py`, `M5_publisher.py`

---

## 3. Data Structure and Naming

### 3.1 Google Cloud Storage (GCS)
All raw (shards) and processed (COGs) data must follow the hierarchy:
`gs://{bucket}/sudamerica/{country}/CATALOG_01/LIBRARY_IMAGES/{SENSOR}/{PERIODICITY}/{MOSAIC}/{temporal_id}/`

Where:
- `{sensor}`: sentinel2, landsat, etc.
- `{periodicity}`: monthly, yearly.
- `{mosaic}`: minnbr, minnbr_buffer, etc.
- `{temporal_id}`: YYYY_MM (monthly) or YYYY (yearly).

### 3.2 Google Earth Engine (GEE)
Assets must follow the pattern:
`image_{country}_fire_{sensor}_{mosaic}_{band}_{temporal_id}`

Collections (ImageCollections) are organized by band:
`projects/{project}/assets/FIRE/CATALOG_01/LIBRARY_IMAGES/{SENSOR}/{PERIOD}/{MOSAIC}/{band}`

### 3.3 Classification Outputs (M5)
Classified tiles, region mosaics, and statistics are stored under:
`{gcs_catalog_prefix}/LIBRARY_CLASSIFICATIONS/{model_id}/`
- `CLASSIFIED_TILES/` — per-tile classification rasters
- `CLASSIFIED_REGION/` — merged regional mosaics
- `STATS/` — tile and region statistics (CSV)

### 3.4 Region FeatureCollections
Administrative regions for each country are stored in GEE featureCollections. The path follows the pattern:
`projects/mapbiomas-{country}/assets/FIRE/AUXILIARY_DATA/regiones_fuego_{country}_v1`

Country-to-asset mappings are centralized in `M_regions.py`. The actual region names live inside each GEE featureCollection (not hardcoded).

---

## 4. Initial Configuration (M0)

Project initialization is done through `set_global_opts`. The buffer parameter has been removed (now it is a mosaic type) and we added the task flag:

```python
set_global_opts(
    sensor='sentinel2',
    periodicity='monthly',
    personal_task_flag='MONITOR',
    clean_cache=True,
    language='en'
)
```

The `language` parameter accepts `'en'`, `'es'`, `'pt'`, `'fr'`, or `'id'`. All UI-facing text is managed by the `M_lang.L` class, which supports runtime locale switching.

GEE project, GCS bucket, and asset paths are configurable independently from the country via `gee_project`, `gee_asset_repo`, `gcs_bucket`, `gcs_project`, and `gcs_catalog_prefix` in `set_global_opts`.

---

## 5. UI/UX Patterns

### Selection Matrix and Tabs
To simplify the interface, modules like M1 and M2 should use **Tabs** to switch between:
*   **Sensors**: [Sentinel-2] [Landsat] [HLS]
*   **Periodicity**: [Monthly] [Annual]

### M4: Flexible Training
M4 must allow band selection from different mosaics and sensors, breaking the "single drawer" paradigm and offering a rich band selection matrix.

### Internationalization
All user-visible text must use `L.XXX` from `M_lang`. Backend/print messages must be in English. To add a new locale, add a dict to `M_lang.STRINGS_*` and register it in `SUPPORTED_LOCALES`.

### UI Components
Reusable UI components are in `M_ui_components.py`: `PipelineStepUI`, `Layout`, `make_empty_state`, `make_sync_button`, `make_search_box`, `make_card_body`, `inline_confirm`, etc.

---

## 6. Performance and Scalability
- **Asynchronous Processing**: Always dispatch tasks to GEE via `ee.batch.Export`.
- **Local Cache**: Use `M_cache.py` to avoid repetitive GCS listings.
- **Tasks**: All tasks must contain the prefix defined in `PERSONAL_TASK_FLAG`.
