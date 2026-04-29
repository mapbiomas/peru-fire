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
| **M1: Export** | **Leve** | **IN:** Colecciones GEE<br>**OUT:** Chunks GCS | `[sensor]_fire_[país]_[año][mes]` | `s2_fire_peru_2408` |
| **M2: Mosaic** | **Medio** | **IN:** Chunks GCS<br>**OUT:** Mosaicos COG (GCS) | Semilla M1 + sufijo banda | `s2_fire_peru_2408_nir_cog.tif` |
| **M3: Samples (Gateway)** | **Leve** | **IN:** Mosaicos (M2)<br>**OUT:** Polígonos (GCS/Asset) | `[col]_[sat_ref]_[reg]`| `samples_sentinel2_r01` |
| **M4: Train** | **Medio** | **IN:** Muestras M3 + Mosaicos M2<br>**OUT:** DNN (GCS) | `[ver]_[sensor]_[reg]` | `v1_1_sentinel2_r01` |
| **M5: Classify**| **Pesado**| **IN:** Modelo M4 + Mosaicos M2<br>**OUT:** Raster (GCS) | `klass_[país]_[reg]_[mod]_[yymm]`| `klass_peru_r01_v1_2408` |
| **M6: Filters** | **Leve** | **IN:** DOY M5 + LULC<br>**OUT:** Raster Filtrado (GCS)| `filt_[país]_[reg]_[mod]_[yymm]`| `filt_peru_r01_v1_2408` |
| **M7: Versioner**| **Leve** | **IN:** Candidatos M6<br>**OUT:** Asset PRE-OFICIAL | `[colección]_v[X]` | `peru_fire_col1_v1` |

### 📂 Arquitectura de Datos e Relacionamento (M1-M7)

O monitor opera um fluxo circular de sincronização entre três ambientes:

| Ambiente | Componentes Principais | Papel no Ciclo |
| :--- | :--- | :--- |
| **🌍 Google Earth Engine** | ImageCollections (Mosaicos) / Assets | Fonte de Brutos e Destino Final |
| **☁️ Google Cloud Storage** | Chunks / COGs / Models / Samples | Persistência e Área de Trabalho Central |
| **⚡ Cache Local (Temp)** | VRT Stack / Tiles / NumPy Arrays | Processamento I/O de Alta Velocidade |

#### 🧭 Mapa de Persistência (Onde encontrar os dados)

| Etapa | Extensão | Path Principal no Cloud Storage (GCS) | 
| :--- | :--- | :--- |
| **M1: Export** | `.tif` | `library_images/{sensor}/monthly/chunks/{yyyy}/{mm}/` |
| **M2: Mosaic** | `.tif` | `library_images/{sensor}/monthly/cog/{yyyy}/{mm}/` |
| **M3: Samples** | `.shp` | `library_samples/{anual,monthly}/{ano}/` |
| **M4: Train** | `.pb / .json` | `models/{version}/{region}/` |
| **M5: Classify** | `.tif` | `library_images/{sensor}/monthly/classifications/raw_versions/v{v}/` |
| **M7: Public** | Asset IC | `projects/mapbiomas-public/assets/{country}/fire/monitor/` |

#### 🏷️ Regras de Nomenclatura Padrão
*   **Fragmentos (M1):** `{sensor}_fire_{pais}_{yy}{mm}_{banda}.tif`
*   **Mosaico COG (M2):** `{sensor}_fire_{pais}_{yy}{mm}_{banda}_cog.tif`
*   **Classificação (M5):** `class_{sensor}_{pais}_{modelo}_{yymm}_v{v}.tif`

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
set_country(COUNTRY)
set_global_opts(sensor='sentinel2', periodicity='monthly')
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
