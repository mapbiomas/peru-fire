# 📓 MapBiomas Fire Monitor — Pipeline (M0-M7)

## 📘 Documentación y Guía del Usuario
Expanda esta sección para entender la arquitectura del dato, requisitos de ambiente y flujo de trabajo.

### 📌 Introducción y Contexto de Uso
Este pipeline constituye el núcleo de procesamiento automatizado para el Monitoramiento de Cicatrices de Fuego.

### 🛠️ Requisitos de Ambiente (GDAL)
Para las etapas de mosaico (M2) y clasificación (M5), el monitor utiliza la herramienta **GDAL** para operaciones de I/O de alto rendimiento.
- **Google Colab:** Se instala automáticamente vía `!apt-get`.
- **Local (Windows):** Requiere **Miniconda** + `conda install -c conda-forge gdal`.

### 🚦 Ciclo de Vida del Dato y Reglas de Nomenclatura
Detalla el flujo secuencial de procesamiento (M1 a M7) y los estándares de nombrado.

### 📂 Arquitectura de Datos y Relacionamiento (M1-M7)
El monitor opera un fluxo circular de sincronización:
- **🌍 GEE Assets:** Fonte de brutos e destino final (ImageCollections).
- **☁️ GCS Bucket:** Persistência central (`library_images/`, `rawsamples/`, `models/`).
- **⚡ Cache Local:** Processamento efêmero (**Local: HD** | **Colab: /content**) para I/O de alta velocidade.

| Etapa | Extensão | Path Principal no Cloud Storage (GCS) |
| :--- | :--- | :--- |
| **M1: Export** | `.tif` | `library_images/{sensor}/monthly/chunks/{yyyy}/{mm}/` |
| **M2: Mosaic** | `.tif` | `library_images/{sensor}/monthly/cog/{yyyy}/{mm}/` |
| **M3.X: Samples** | `.shp` | `rawsamples/{anual,monthly}/{ano}/` |
| **M5: Classify**| `.tif` | `library_images/{sensor}/monthly/classifications/v{v}/` |

---

## [M0] — Configuración y Autenticación

### > Opción A: Inicialización Google Colab
**💡 Nota para Colab:** Las siguientes celdas preparan el entorno virtual en la nube.

```python
# M0.1a — Preparación del entorno Colab (Clonar repo)
import os
if not os.path.exists("fire_monitor"):
    !git clone https://github.com/usuario/fire_monitor.git
%cd fire_monitor/peru-fire/mapbiomas_fire_monitor/version_01/src/core
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
**💡 Célula "Invencível":** Esta célula autodetecta se estás en Local ou Colab e configura as rutas.

```python
# M0.2 — Inicialização do Monitor
import sys, os

def auto_path_setup():
    """Localiza a pasta src/core em diferentes ambientes"""
    possible_paths = [
        os.path.abspath("."),             # Já está na pasta?
        os.path.abspath("../src/core"),   # Estrutura local padrão
        "/content/fire_monitor/peru-fire/mapbiomas_fire_monitor/version_01/src/core", # Colab
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
authenticate() # Detecção automática de login Colab/Local
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
