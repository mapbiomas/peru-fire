# Prompt para gerar fluxograma M4 (Mermaid.js)

Copie o bloco abaixo para o ChatGPT (ou IA similar):

---

```
Gere um fluxograma em Mermaid que represente o módulo M4 (Treinamento DNN) do pipeline MapBiomas Fire Monitor.

## Fluxo Detalhado

### 1. Configuração do Experimento (M4_ui.py)
- Usuário seleciona campanha de amostragem, sample collections e bandas por sensor/mosaico
- Define hiperparâmetros: Layers, LR, Batch, Iterações
- Training ID (auto-sequencial), Shortname (auto-geração), Comentário
- Clique "Treinar" → dispara extração + treino

### 2. Extração Multisensor (M4_data_extractor.py)
- Verifica cache local de COGs (sincroniza do GCS se vazio)
- Para cada sample collection × período: lê CSV, valida bandas COG, pula se faltar, baixa COGs, rasterio.mask, empilha X e y

### 3. Treinamento DNN (M4_algorithms_dnn.py)
- Split 80/20, normalização só no treino (evita data leakage)
- Grafo TF1: FC[7]→Dropout→FC[14]→Dropout→FC[7]→Dropout→Sigmoid
- Loop com mini-batch, avalia a cada N/20 iters, extrai embeddings ao vivo
- Acumula snapshots para Time Machine

### 4. Persistência GCS
- weights.npz, metadata.json, metrics.json (com diagnostic_snapshot PCA)
- projector/ (TSV), history/ (snapshots), samples/ (CSV), extracted_pixels/ (npy)

### 5. Analytics & Canvas (M4_analytics.py + M4_ui.py)
- Card do modelo, KPIs (Acc, Prec, Rec, F1, Nota IA)
- Dashboard 2x3: CM, History, PCA2D, Prob, PR-Curve
- Espaço Latente Interativo: PCA 3D + t-SNE 3D (Plotly)
- Canvas: grid comparativo com slider Time Machine
- Ações: Retreinar, Re-extrair, Deletar

### 6. Decisões
- Se TF sem AVX → avisa usar Colab
- Se cache vazio → fallback fixo de bandas
- Nota IA automática 1-5 por regras (F1 > 0.90 = 5)

Crie o fluxograma em Mermaid com graph TD e 5 subgraphs: "Configuração", "Extração", "Treinamento", "Persistência GCS", "Auditoria". Use notas para fallbacks.
```

---

Após gerar, cole o código Mermaid em https://mermaid.live para visualizar.
