# 📘 Estrela-Guia: Padrões de Desenvolvimento MapBiomas Fire

Este documento sistematiza os padrões de arquitetura, interface e performance estabelecidos durante a refatoração do Pipeline MapBiomas Fire (Peru). O objetivo é garantir que todos os novos módulos (M3 a M7) herdem o mesmo DNA de estabilidade e design.

---

## 1. 🏗️ Arquitetura de "Código Partido" (Code Splitting)

Todos os módulos devem ser divididos em dois arquivos para facilitar a manutenção e evitar conflitos no Jupyter.

*   **`M#_logic.py`**: Contém apenas funções puras de Earth Engine, GDAL ou manipulação de arquivos. Não deve conter `ipywidgets`.
*   **`M#_ui.py`**: Contém a classe que herda de `PipelineStepUI`. Gerencia o layout, botões e reatividade.

---

## 2. 🎨 Padrões de Interface (UI/UX)

### Matriz de Seleção (Pattern M1/M2)
Usado quando o processamento pode ser feito por bandas individuais através de múltiplos períodos.
*   **Larguras Padrão**: Data (`100px`), Tipo (`60px`), Botão [S] (`40px`), Células (`80px`).
*   **Padrão de Linha Dupla (M1)**: Cada período exibe duas linhas — **GCS** (shards) e **ASSET** (GEE). Facilita a auditoria de sincronização entre nuvens.
*   **Padrão de Triagem Ativa (M2)**: A interface é filtrada dinamicamente. **Só exibe os meses que possuem chunks no GCS**, mas que ainda não tiveram seus COGs gerados. Isso limpa a visão do analista e foca no processamento pendente.

*   **Botão [S] (Smart Toggle)**: Deve inverter o estado da linha. Se algo estiver marcado -> Desmarcar tudo. Se nada marcado -> Marcar tudo que for `MISS`.
*   **Células de Status**:
    *   `OK` (**Verde**): Dado existe e está pronto.
    *   `RUN` (**Azul**): Processamento em curso no backend (GEE).
    *   `MISS` (**Cinza/Vermelho**): Dado ausente ou ação necessária.

### Mockup ASCII: M1 (Despacho Multi-Nuvem)
O M1 foca em **Auditoria**, mostrando sempre o estado no GCS e no GEE simultaneamente.

```text
Data       Tipo   [S]    blue     green     red      nir      ...
--------------------------------------------------------------------
2026-03    GCS    [S]    MISS     MISS     MISS     MISS
           ASSET  [S]     OK       OK       OK       OK
--------------------------------------------------------------------
2026-02    GCS    [S]     OK       OK       OK       OK
           ASSET  [S]     OK       OK       OK       OK
--------------------------------------------------------------------

                                [ Logs ]
[10:30] M1: [2/14] Despachando 2026-03_blue (gcs)
```

### Mockup ASCII: M2 (Montagem de Mosaicos)
O M2 foca em **Ação**, mostrando apenas o que está pendente de processamento.

```text
Data       Tipo   [S]    blue     green     red      nir      ...
--------------------------------------------------------------------
2026-04    COG    [S]   MISS    MISS     OK       OK  
--------------------------------------------------------------------

                                [ Logs ]
[11:00] M2: [1/7] Processando [blue] | ⏳ ETA: ~0:15:00
```

### Mockup ASCII: M3 (Toolkit Gateway)
Foco em simplicidade e conexão com o Earth Engine Code Editor.

```text
[ 🔗 GEE JS TOOLKIT ]
URL: https://code.earthengine.google.com/?scriptPath=...

Assets de Polígonos Disponíveis:
• projects/mapbiomas/assets/SAMPLES/v1_peru_2### Mockup ASCII: M4 (Entrenador)
Foco em parametrização técnica, metadados automáticos e anotações do usuário.

```text
[ 🧠 M4 - CONFIGURACIÓN DE ENTRENAMIENTO ]
Versión Sugerida: [ v3_peru_rns1s2_10k ] (Auto-ID)
Amostras: [ v2_peru_2024 ]  Bandas: [X] r  [ ] g  [ ] b  [X] n  [X] s1  [X] s2
Hyperparams: LR: 0.001 | Layers: [64, 32, 16] | Iters: 10,000

---
[ 🤖 Meta-descrição Automática ]
"Dataset: 12.500 pixels (Fogo/Não-Fogo). Arquitetura: DNN 3-layer.
Bandas espectrais: Red, NIR, SWIR1, SWIR2."

[ ✍️ Anotações do Analista (Long-form) ]
[                                                              ]
[                                                              ]
---

[ 🚀 EXTRAER PIXELS & ENTRENAR ]

Progress: [██████░░░░] 60% | Loss: 0.452 | Acc: 0.912
```

### Mockup ASCII: M4.2 (Biblioteca de Modelos)
Foco em governança, comparação visual e análise espectral.

```text
[ 📚 M4.2 - BIBLIOTECA Y MÉTRICAS ]
---------------------------------------------------------------
|  [ MODEL v3 ]        |  [ ASSINATURA ESPECTRAL (v3) ]
|  Status: Ativo       |  Val
|  Acc: 0.94           |   ^      /--[ Fogo (StdDev) ]
|  Loss: 0.21          |   |     /  /---[ Solo (StdDev) ]
|  [ USAR ESTE ]       |   +----|--|----|----|---> (Bandas)
---------------------------------------------------------------
```

### Mockup ASCII: M5 (Clasificador - Gestión y Producción)
Fase 1: Atribuição de modelos às regiões. Fase 2: Matriz de produção por modelo em gavetas.
**Output Final**: `ee.ImageCollection` contendo todas as permutações de [Modelo X x Região x Data ].

```text
[ 🚀 M5 - CLASIFICADOR ]

1. MAPA DE ATRIBUCIÓN (Região x Modelo)
Região          Modelo Selecionado
---------------------------------------
Amazonia-L     [ v3_peru_rns1s2_10k ]
Andes-C        [ v3_peru_rns1s2_10k ]
Costa-N        [ v2_exp_r_5k        ]
---------------------------------------

2. MATRIZ DE EXECUÇÃO (Produção em Lote)
[ ▼ ] Gaveta: Modelo v3_peru_rns1s2_10k
      Data       Amazonia-L     Andes-C     Costa-N
      ---------------------------------------------
      2024-05    [ ] MISS       [X] OK      [ ] RUN
      2024-04    [X] OK         [X] OK      [X] OK
      ---------------------------------------------

celula isolada [ ▶ DISPARAR CLASIFICACIÓN SELECIONADA ]

3. PAINEL DE CONSOLIDACIÓN (Histórico de Versões no ImageCollection)
Data       Amazonia-L       Andes-C     Costa-N
---------------------------------------------------
2024-05     [v1, v2]         [v1, v2]    [v2]
2024-04     [v1, v3]         [v1]        [v2]
---------------------------------------------------
```

### Mockup ASCII: M6 (Publicador y Filtros de Decisão)
> [!NOTE]
> **Em fase de planejamento**. Foco em filtrar a `ImageCollection` do M5 para o merge final.

```text
[ 🏁 M6 - FILTROS Y PUBLICADOR ]

1. CONFIGURAÇÃO DE MÁSCARAS (Defaults)
[X] Open/Close: [ 2 x 2 ] (Pixels)
[X] Classes de Exclusão: [ 33, 24, 27 ] (Agua, Urbano, Afloramento)

2. COMPOSIÇÃO DO MERGE (Região x Versão/Modelo)
Região         Versão Seç.    Filtros Espaciais
-------------------------------------------------
Amazonia-L     [ v3 ]         [X] Open [X] Close
Andes-C        [ v1 ]         [X] Open [ ] Close
Costa-N        [ v3 ]         [X] Open [X] Close
-------------------------------------------------

[ 💾 CONSOLIDAR ATRIBUTO DOY (Day of Year) ]
```

### Gerenciamento do Modo de Edição (`EDIT_MODE`)
A variável global `EDIT_MODE` (definida no M0) dita o comportamento de destrutividade:
*   `False` (Padrão): Checkboxes `OK` ficam desabilitados. O botão de "Eliminar Seleção" (Lixeira) fica oculto.
*   `True`: Checkboxes `OK` são liberados para seleção. O botão vermelho de remoção aparece na toolbar.

---

## 3. ⚡ Performance e Estabilidade

### Limpeza "Degrau a Degrau" (Step-by-Step)
Para otimizar o espaço em disco (especialmente no Peru a 10m):
*   **NUNCA** acumule arquivos temporários de várias bandas desnecessariamente.
*   **Regra de Ouro**: Exclua chunks, COGs e metadados locais IMEDIATAMENTE após a etapa que não dependerá mais deles. 
    *   *Exemplo*: Na montagem de mosaicos, os chunks podem ser removidos assim que o COG final for validado e iniciado o upload.

### Cronometria Inteligente
Rotinas de lote devem informar:
*   **Progresso**: No formato `[N/T]` (Ex: `[3/20]`).
*   **ETA**: Cálculo baseado na média de tempo a partir do segundo item concluído.

---

---

## 4. 📅 Roadmap de Futuros Módulos (M3-M8)
> [!IMPORTANT]
> Os módulos M6, M7 e M8 estão em **fase de definição estratégica**. O design abaixo é preliminar e sujeito a alterações conforme o avanço dos testes no M5.

### [M3] — Sample Manager (Dashboard GEE)
*   **Interface**: Dashboard integrado no Earth Engine com gavetas simultâneas (Instruções, Importação, Amostras, Exportação). Inclui painel de estatísticas em tempo real e ferramentas de desenho dedicadas (Fogo / Não Fogo).
*   **Missão**: Construir o banco de dados de treinamento através da coleta interativa e balanceada de polígonos. Exporta tabelas de assinaturas espectrais tanto para GEE Asset quanto para GCS.
*   **Padrão de Nomenclatura**: Sufixos automáticos `YYYY` (Anual) ou `YYYY_MM` (Mensal) com rastreamento de versão (`v000X`).
*   **Rutas Base**: GEE -> `VERSION_01/LIBRARY_SAMPLES` | GCS -> `monitor/library_samples`.

### [M4] — Model Trainer
*   **Interface**: Painel de Logs + Widget de Gráfico de Perda (Loss).
*   **Missão**: Treinar a Rede DNN e salvar o binário (`.h5` ou similar) junto com o metadado do dataset utilizado.
*   **Ação**: Inputs para hiperparâmetros e campo livre de anotações técnicas.

### [M5] — Classifier (The Core Collection)
*   **Interface**: Matriz de Atribuição + Matriz de Produção por Modelo (Gavetas).
*   **Missão**: Aplicar modelos treinados sobre os mosaicos do M2.
*   **Output**: Consolida todas as exportações em uma **`ee.ImageCollection`** única de versões regionais/temporais.

### [M6] — Decision Filter & National Merge
*   **Interface**: Triagem de versões da `ImageCollection` do M5.
*   **Missão**: Filtrar a melhor versão para cada região/data e aplicar pós-processamento.
*   **Filtros Candidatos**:
    *   **Espaciais**: `Open(2x2)` e `Close(2x2)` (ajustáveis).
    *   **Máscaras de Classe**: Filtragem sobre Água (33), Urbano (24) e Afloramentos Rochosos (27).
*   **Finalidade**: Gerar o dado consolidado nacional com banda de **DOY (Day of Year)**.

### [M7 e M8] — Subprodutos e Publisher
*   **M7 (Insights)**: Cálculo de estatísticas de área queimada baseadas nos ativos consolidados.
*   **M8 (Operations)**: Publicação e integração com o Workspace oficial MapBiomas.
