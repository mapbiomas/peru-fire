# Prompt para gerar fluxograma M5 (Mermaid.js)

Copie o bloco abaixo para o ChatGPT (ou IA similar):

---

```
Gere um fluxograma em Mermaid que represente o módulo M5 (Classificação Regional) do pipeline MapBiomas Fire Monitor. O fluxo completo é:

## Visão Geral
M5 recebe jobs de uma fila local (JSON), processa classificação de queimadas usando modelo DNN treinado no M4, faz upload dos resultados para GCS e depois publica no Google Earth Engine.

## Fluxo Detalhado

### 1. Interface do Usuário (M5_classifier_ui.py)
- Usuário seleciona: 1 modelo treinado (da biblioteca GCS), múltiplas regiões geográficas, múltiplos períodos (ano ou ano_mês)
- Clique em "Añadir Lote" gera combinações cartesianas (modelo × região × período) como jobs na fila
- Cada job tem: id, modelo, região, período, status (PENDING/RUNNING/COMPLETED/FAILED), enabled, upload_gee, progress
- Aba Pendentes: lista jobs com checkbox enable/disable, filtros (modelo/região/ano), botão delete
- Aba Concluídas: lista jobs agrupados por modelo, checkbox upload_gee, botão delete (com exclusão GCS)

### 2. Motor de Processamento (M5_classifier.py)
Função principal: run_m5_queue(send=['classification', 'upload'])
- FASE 1 — CLASSIFICAÇÃO:
  - Carrega fila, filtra jobs PENDING e enabled
  - Para cada job:
    - Muda status para RUNNING, salva fila
    - _process_job(job):
      a) Lê metadata.json do modelo no GCS (extrai bands_config, num_input, layers)
      b) Obtém grid de células cim-world do GEE que intersectam a região
      c) Reconstrói modelo Keras Sequential com os pesos do .npz salvos no M4
      d) Para cada célula do grid:
         - Se já existe classificado em GCS → pula (checkpoint)
         - _classify_cell(): baixa bandas COG, empilha arrays, aplica modelo DNN → raster classificado
         - Upload do raster para GCS
      e) Marca job como COMPLETED
- FASE 2 — UPLOAD GEE:
  - Para cada job COMPLETED com upload_gee=True:
    - Lista tiles classificados em GCS
    - Download de todos, faz merge (rasterio.merge) em mosaico regional
    - Upload mosaico para GCS
    - Cria ImageCollection no GEE (se não existir)
    - Dispara task Export.image.toAsset() com scale=10, maxPixels=1e13

### 3. Fluxo de Dados
GCS:
  library_models/{model_id}/metadata.json
  library_models/{model_id}/weights.npz
  library_classifications/{model_id}/{period}/classified_tiles/{region}/{cell_id}.tif
  library_classifications/{model_id}/{period}/regional_mosaics/{region}.tif

GEE:
  cim-world-1-250000 (grid de células)
  FAO/GAUL/2015/level0 (filtro Peru)
  LIBRARY_CLASSIFICATIONS/REGIONAL/{model_id} (ImageCollection destino)

### 4. Decisões importantes no fluxo
- Se o mosaico regional já existe em GCS, o job é ignorado (não entra na fila)
- Se o tile já existe em GCS durante processamento, pula (checkpoint)
- Erro em qualquer job → marca FAILED e interrompe a fase
- Upload ao GEE é opcional (controlado por checkbox upload_gee)

Crie o fluxograma em Mermaid usando graph TD com subgraphs para organizar: "Interface do Usuário", "Fila de Jobs", "Fase 1: Classificação", "Fase 2: Upload GEE", "Armazenamento GCS". Use notas laterais para destacar os checkpoints e decisões.
```

---

Depois de gerar, cole o código Mermaid em https://mermaid.live para visualizar e exportar como PNG/SVG.
