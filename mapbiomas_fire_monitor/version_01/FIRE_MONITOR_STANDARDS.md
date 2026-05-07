# 📘 Estrela-Guia: Padrões de Desenvolvimento MapBiomas Fire

Este documento sistematiza os padrões de arquitetura, interface e performance estabelecidos durante a refatoração do Pipeline MapBiomas Fire (Peru). O objetivo é garantir que todos os novos módulos (M3 a M7) herdem o mesmo DNA de estabilidade e design.

---

## 1. 🏗️ Arquitetura de "Código Partido" (Code Splitting)

Todos os módulos devem ser divididos em dois arquivos para facilitar a manutenção e evitar conflitos no Jupyter:

*   **`M#_logic.py`**: Contém apenas funções puras de Earth Engine, GDAL ou manipulação de arquivos. Não deve conter `ipywidgets`.
*   **`M#_ui.py`**: Contém a classe que herda de `PipelineStepUI`. Gerencia o layout, botões e reatividade.

---

## 2. 📁 Estrutura de Dados e Nomenclatura

### 2.1 Google Cloud Storage (GCS)
Toda a base de dados bruta (shards) e processada (COGs) deve seguir a hierarquia:
`gs://{bucket}/sudamerica/peru/monitor/version_01/library_images/{sensor}/{periodicity}/{mosaic}/{temporal_id}/`

Onde:
- `{sensor}`: sentinel2, landsat, etc.
- `{periodicity}`: monthly, yearly.
- `{mosaic}`: minnbr, minnbr_buffer, etc.
- `{temporal_id}`: YYYY_MM (mensal) ou YYYY (anual).

### 2.2 Google Earth Engine (GEE)
Os Assets devem seguir o padrão:
`image_{country}_fire_{sensor}_{mosaic}_{band}_{temporal_id}`

As coleções (ImageCollections) são organizadas por banda:
`projects/{project}/assets/FIRE/MONITOR/VERSION_01/LIBRARY_IMAGES/{SENSOR}/{PERIOD}/{MOSAIC}/{band}`

---

## 3. ⚙️ Configuração Inicial (M0)
A inicialização do projeto deve ser feita através do `set_global_opts`. O parâmetro de buffer foi removido (agora ele é um tipo de mosaico) e adicionamos a flag de tarefas:

```python
set_global_opts(
    sensor='sentinel2', 
    periodicity='monthly', 
    personal_task_flag='MONITOR',
    clean_cache=True
)
```

---

## 4. 🎨 Padrões de Interface (UI/UX)

### Matriz de Seleção e Abas (Tabs)
Para simplificar a interface, módulos como M1 e M2 devem utilizar **Abas** para alternar entre:
*   **Sensores**: [Sentinel-2] [Landsat] [HLS]
*   **Periodicidade**: [Mensal] [Anual]

### M4: Treinamento Flexível
O M4 deve permitir a seleção de bandas de diferentes mosaicos e sensores, quebrando o paradigma de "gaveta única" e oferecendo uma matriz de seleção de bandas rica.

---

## 5. 🚀 Performance e Escalabilidade
- **Processamento Assíncrono**: Sempre despachar tarefas para o GEE via `ee.batch.Export`.
- **Cache Local**: Utilizar o `M_cache.py` para evitar listagens repetitivas no GCS.
- **Tasks**: Todas as tarefas devem conter o prefixo definido na `PERSONAL_TASK_FLAG`.
