# Arquitetura do Peru Fire Monitor (version_01)

Este documento descreve a arquitetura do projeto MapBiomas Fire Monitor (Peru), focado em extração, montagem, amostragem e treinamento de modelos de detecção de fogo usando Sentinel-2/Landsat.

## 🏗 Estrutura de Módulos (M0 a M7)

O pipeline é estritamente modular, focado em execução via Jupyter Notebooks utilizando `ipywidgets` para UI.

### 🔧 M0: Configuração Base (`M0_auth_config.py`)
- Centraliza as credenciais (Earth Engine, GCS).
- Gerencia a taxonomia de caminhos na nuvem (estruturas `sudamerica/peru/monitor/version_01/...`).
- Exporta constantes globais (`CONFIG`, `GLOBAL_OPTS`).

### 📥 M1: Extração de Dados (`M1_export_logic.py` / `M1_export_ui.py`)
- Comunica com o Google Earth Engine (GEE).
- Exporta chunks (fragmentos espaciais) de imagens COG e CSV/Parquet para o Google Cloud Storage (GCS).
- Separa lógica pesada (GEE Tasks) da UI (Jupyter Widgets).

### 🧩 M2: Montagem de Mosaicos (`M2_mosaic_logic.py` / `M2_mosaic_ui.py`)
- Lê recursivamente os shards COG exportados pelo M1 usando `gsutil` ou `gcsfs`.
- Usa **GDAL** local (`gdalbuildvrt`, `gdal_translate`) para unir fragmentos espacialmente.
- O processamento é **síncrono/bloqueante**, com saída enviada diretamente para o console do Jupyter (stdout).

### 🧪 M3: Curadoria de Amostras (`M3_toolkit_logic.py` / `M3_sample_ui.py`)
- Visualização de bandas e índices (NDVI, NBR, Falsas Cores).
- Coleta vetorial via Leaflet/Geemap ou ferramentas personalizadas para criação de dados de treino.

### 🧠 M4: Treinamento de Modelo (`M4_model_trainer.py`)
- Extrai píxeis a partir dos pontos (M3) lendo os Mosaicos COG (M2).
- Treinamento utilizando **TensorFlow 1.x Compatibilidade** (`tf.compat.v1.disable_v2_behavior()`).
- O TensorFlow **deve ter "lazy load"** (importado dentro dos métodos ou após a construção da UI) para evitar travamento da renderização de Widgets no Windows.
- Salva Modelo (pesos npz), Metadados (JSON) e Métricas (JSON) no GCS.
- Gera Dashboard premium com Matriz de Confusão e Evolução da Acurácia.

### 🚧 M5, M6, M7: Em Desenvolvimento
- Previstos para Classificação, Pós-processamento e Publicação de Coleções Finais.

## 🗂 Estrutura de Diretórios
```
peru-fire/
└── mapbiomas_fire_monitor/
    └── version_01/
        ├── notebooks/
        │   └── mapbiomas_fire_sentinel_peru.ipynb (Ponto de entrada)
        ├── src/
        │   └── core/ (Todos os módulos lógicos e de UI)
        └── scratch/ (Scripts temporários, testes, depuração)
```
