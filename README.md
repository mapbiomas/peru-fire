# MapBiomas Fire - Peru (peru-fire)

This repository serves as the main entry point (root directory) for scripts and projects dedicated to mapping burned areas in Peru as part of the collaborative [MapBiomas Fire](https://brasil.mapbiomas.org/es/metodo-mapbiomas-fogo/) network.

The repository brings together independent but interconnected modules designed to support the end-to-end management of data, workflows, and algorithms used for burned-area mapping.

## Repository Modules

### 1. [MapBiomas Fire Monitor (`mapbiomas_fire_monitor/`)](./mapbiomas_fire_monitor/README.md)

An interactive application and data pipeline (M1, M2, etc.) responsible for orchestrating, exporting, downloading, and validating the satellite imagery and mosaics used as inputs for the classification workflow.

### 2. [Fire Landsat 30m (`fire_landsat_30m/`)](./fire_landsat_30m/README.md)

Workflows, notebooks, and methodological configurations for burned-area classification using 30-meter Landsat imagery. This module contains the procedures and parameters used for `collection_01` across the ecoregions of Peru.

## Institutional Support and Contact

Developed with technological and methodological support from the **Instituto de Pesquisa Ambiental da Amazônia (IPAM)**.

For technical questions, collaboration opportunities, or issue reporting, please contact:

* **Vera Arruda** — [vera.arruda@ipam.org.br](mailto:vera.arruda@ipam.org.br)
* **Wallace Silva** — [wallace.silva@ipam.org.br](mailto:wallace.silva@ipam.org.br)
