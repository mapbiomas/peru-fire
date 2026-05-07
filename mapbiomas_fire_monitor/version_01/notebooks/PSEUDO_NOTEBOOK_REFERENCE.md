# 📓 MapBiomas Fire Monitor — Pipeline (M0-M7)

## 📘 Documentación y Guía del Usuario
Expanda esta sección para entender la arquitectura del dato, requisitos de ambiente y flujo de trabajo.

#### 📌 Introducción y Contexto de Uso

Este pipeline de código constituye el núcleo de procesamiento automatizado para el **Monitoramiento de Cicatrices de Fuego de MapBiomas**. Su objetivo principal es extraer, procesar, clasificar y publicar datos satelitales a nivel regional o nacional con alta trazabilidad.

*   📥 **Entradas Globales (Inputs):** Colecciones de imágenes brutas desde Google Earth Engine (Sentinel-2, Landsat), polígonos vectoriales para entrenamiento (muestras / *samples*), y mapas auxiliares de cobertura de suelo (LULC).
*   📤 **Salidas Globales (Outputs):** Chunks y mosaicos optimizados (COGs) en Google Cloud Storage (GCS), pesos de modelos de redes neuronales (DNN), matrices de clasificación, e ImageCollections versionadas pre-oficiales en GEE.
*   🔄 **Alternativas de Ejecución:** La arquitectura modular permite **ejecución mixta**.
    *   **Ejecución Local (Sugerida para M1, M2 e M5):** Máxima estabilidad al descargar y ensamblar mosaicos con GDAL a través de I/O de disco sostenido.
    *   **Google Colab (Sugerida para M3 y M4):** Acceso inmediato a recursos de RAM/GPU, facilitando recolección de muestras ágil y entrenamiento de redes.

> **Nota:** Tanto el disco del PC local como el almacenamiento temporal de Colab actúan como **espacio efímero**. La persistencia ocurre siempre en el **Google Cloud Storage (GCS) Bucket**.

#### 🚦 Ciclo de Vida del Dato y Reglas de Nomenclatura

| Etapa | Peso | Inputs → Outputs | Regla de Nomenclatura | Ejemplo |
| :--- | :--- | :--- | :--- | :--- |
| **M1: Export** | **Leve** | **IN:** Colecciones GEE<br>**OUT:** Chunks GCS | `image_{country}_fire_{sensor}_{mosaic}_{band}_{temporal_id}_{suffix}` | `image_peru_fire_sentinel2_minnbr_buffer_blue_2025_08_00000-00000` |
| **M2: Mosaic** | **Medio** | **IN:** Chunks GCS<br>**OUT:** Mosaicos COG (GCS) | `image_{country}_fire_{sensor}_{mosaic}_{band}_{temporal_id}_cog` | `image_peru_fire_sentinel2_minnbr_buffer_blue_2025_08_cog` |
| **M3: Samples** | **Leve** | **IN:** Mosaicos (M2)<br>**OUT:** Polígonos (GCS/Asset) | `sample_{id}_{country}_{region}_{temporal_id}`| `sample_0001_peru_r10_amazon_2025_07` |
| **M4: Train** | **Medio** | **IN:** Muestras M3 + Mosaicos M2<br>**OUT:** DNN (GCS) | `training_{id}_{region}_{sensor}` | `training_0001_peru_r10_sentinel2` |
| **M5: Classify**| **Pesado**| **IN:** Modelo M4 + Mosaicos M2<br>**OUT:** Raster (GCS) | `region_{reg}_training_{id}_{sensor}_{temp_id}`| `region_r10_training_0001_sentinel2_2025_08` |
| **M6: Filters** | **Leve** | **IN:** M5 + LULC<br>**OUT:** Raster Filtrado (GCS)| `candidate_{id}_{sensor}_{temp_id}`| `candidate_c1_sentinel2_2025_08` |
| **M7: Versioner**| **Leve** | **IN:** Candidatos M6<br>**OUT:** Asset OFICIAL | `burned_day_of_year_{sensor}_{temp_id}` | `burned_day_of_year_sentinel2_2025_08` |

### 📂 Arquitectura de Datos e Relacionamento (M1-M7)

O monitor opera um fluxo circular de sincronização entre três ambientes:

| Ambiente | Componentes Principais | Papel no Ciclo |
| :--- | :--- | :--- |
| **🌍 Google Earth Engine** | ImageCollections (Mosaicos) / Assets | Fonte de Brutos e Destino Final |
| **☁️ Google Cloud Storage** | Chunks / COGs / Models / Samples | Persistência e Área de Trabalho Central |
| **⚡ Cache Local (Temp)** | VRT Stack / Tiles / NumPy Arrays | Processamento I/O de Alta Velocidade |

#### 🧭 Mapa de Persistência (Onde encontrar os dados)

| Etapa | Extensão | Path Principal no Cloud Storage (GCS) | 
| :--- | :--- | :--- | :--- |
| **M1: Export** | `.tif` | `library_images/{sensor}/{period}/{mosaic}/{temporal_id}/chunks/` |
| **M2: Mosaic** | `.tif` | `library_images/{sensor}/{period}/{mosaic}/{temporal_id}/` |
| **M3: Samples** | `.csv` | `library_samples/` |
| **M4: Train** | `.pb / .json` | `library_images/{sensor}/models/training_{training_id}_{shortname}_{sensor}/` |
| **M5: Classify** | `.tif` | `library_images/{sensor}/{period}/burned_day_of_year_regional/` |
| **M6: Filters** | `.tif` | `library_images/{sensor}/{period}/burned_day_of_year_candidates/` |
| **M7: Public** | Asset IC | `library_images/{sensor}/{period}/burned_day_of_year_official/` |

#### 🏷️ Regras de Nomenclatura Padrão
*   **Imagens (M1/M2):** `image_{country}_fire_{sensor}_{mosaic}_{band}_{temporal_id}`
*   **Amostras (M3):** `sample_{id}_{country}_{region}_{temporal_id}`
*   **Classificação (M5):** `region_{region}_training_{training_id}_{sensor}_{temporal_id}`

---
#### 🔄 Retroalimentación y Tolerancia a Fallos

*   **Restantes:** El botón "Seleccionar Restantes" marcará solo los ítems **pendientes** en GCS.
*   **Sobrescritura:** Remarcar manualmente un ítem con bandera de éxito (verde) indica la intención de reemplazar el archivo.
*   **Modo Edición (`EDIT_MODE`):** Si es activado en `M0`, la UI expone botones de "Eliminar" en GCS.

## ⚙️ [M0] — Configuración de Ambiente (Escolha uma Rota)

### > Opción A: Inicialización Google Colab
**💡 Nota para Colab:** Las siguientes celdas preparan el entorno virtual en la nube.

```python
# M0.1a — Preparación del entorno Colab (Clonar repo)
import os
if not os.path.exists("fire_monitor"):
    !git clone https://github.com/mapbiomas/peru-fire.git fire_monitor
%cd fire_monitor/mapbiomas_fire_monitor/version_01/src/core
```

```python
# ⬇️ Instalar GDAL Binaries e dependências Python
!apt-get update -qq && apt-get install -y -qq gdal-bin python3-gdal
!pip install -q earthengine-api gcsfs rasterio scipy tqdm
```

### > Opción B: Inicialización Local
**🛠️ Requisitos Local (GDAL / Conda)**
Si recibes un error de `Faltam dependências vitais`, el monitor buscará automáticamente el GDAL en tu instalación de Conda.

```python
# M0.1b — Configuración local de rutas (Opcional, M0.2 ya lo hace)
import sys, os
REPO_ROOT = os.path.abspath("..")
SRC_PATH  = os.path.join(REPO_ROOT, "src", "core")
if SRC_PATH not in sys.path: sys.path.insert(0, SRC_PATH)
```

### > Inicialización Común (M0.2)
**💡 Célula "Invencível":** Esta célula autodetecta se estás en Local ou Colab y configura as rutas.

```python
# M0.2 — Inicialização do Monitor
import sys, os

def auto_path_setup():
    """Localiza a pasta src/core em diferentes ambientes"""
    possible_paths = [
        os.path.abspath("."),             
        os.path.abspath("../src/core"),   
        "/content/fire_monitor/mapbiomas_fire_monitor/version_01/src/core", 
    ]
    for p in possible_paths:
        if os.path.exists(os.path.join(p, "M0_auth_config.py")):
            if p not in sys.path: sys.path.insert(0, p)
            return p
    return None

found_path = auto_path_setup()
COUNTRY = "peru"

from M0_auth_config import set_country, authenticate, set_global_opts
set_global_opts(sensor='sentinel2', periodicity='monthly', personal_task_flag='MONITOR', clean_cache=False)
authenticate() 
```

---

## 🚀 Fluxo de Processamento (Sequencial)

### [M1] — Despacho de Exportación (GEE → Bucket)
```python
from M1_export_ui import run_ui, start_export
ui_exporter = run_ui(years=[2025,2026])
start_export(ui_exporter)
```

### [M2] — Ensamblaje Nacional (COG)
```python
from M2_mosaic_ui import run_ui, start_assemble
ui_assembler = run_ui(years=[2025,2026])
start_assemble(ui_assembler)
```

### [M3] — Coleta de Amostras (GEE Toolkit Gateway)
```python
from M3_sample_ui import show_toolkit_links
show_toolkit_links()
```

### [M4] — Entrenamiento DNN
```python
from M4_model_trainer import run_ui, start_training
ui_trainer = run_ui()
start_training(ui_trainer)
```

### [M5] — Clasificación Regional
```python
from M5_classifier import run_ui, start_classification
ui_classifier = run_classifier(PRESET_MODELS)
start_classification(ui_classifier)
```

### [M6] — Aplicación de Filtros
```python
from M6_publisher import run_ui, start_filtering
ui_filters = run_filters(PRESET_FILTERS)
start_filtering(ui_filters)
```

### [M7] — Versão Final (Curaduría)
```python
from M7_curator import run_ui, start_curation
ui_curator = run_curator(PRESET_VOTES)
start_curation(ui_curator)
```
