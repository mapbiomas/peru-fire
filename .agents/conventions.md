# Convenções e Diretrizes (Peru Fire Monitor)

Este documento define regras de desenvolvimento para Agentes IA e desenvolvedores que operam no repositório.

## 🎨 UI/UX e Frontend (Jupyter Widgets)
1. **Design "Premium"**: As interfaces devem impressionar. Use `widgets.HTML` com CSS inline para injetar gradientes, sombras (`box-shadow`), bordas arredondadas (`border-radius`) e tipografia moderna. Exemplo: `<div style='background:linear-gradient(90deg, #b00a0a, #ff4b2b); color:white; padding:15px...'>`.
2. **Separação UI / Lógica**: Toda funcionalidade de tela fica em arquivos `*_ui.py` (ou em classes `*UI`). Lógica pesada fica em arquivos `*_logic.py` (ou fora do escopo principal da UI).
3. **M_ui_components.py**: Utilize sempre as classes base como `PipelineStepUI` e botões pré-estilizados (`make_status_cell`, etc.) para manter consistência visual (ex: ícones FontAwesome, botões coloridos danger/success/info).

## ☁️ Interação com Google Cloud Storage (GCS)
1. **Windows vs Colab**: Este pipeline precisa rodar em Windows (Ambiente de Desenvolvimento) e em Colab/Linux.
2. **Evite `gsutil` Wildcards no Windows**: No M2, evite `gsutil ls "gs://bucket/**"`. No PowerShell, wildcards dão erro. Prefira listar diretórios diretos com `-r` ou usar a biblioteca `gcsfs` programaticamente.
3. **Leitura Raster (`rasterio`)**: No Colab, usar caminhos `/vsigs/`. No Windows, se houver falha no `/vsigs/`, deve haver um fallback explícito para fazer o download temporário do arquivo e lê-lo localmente.

## 🐍 Python e Bibliotecas
1. **TensorFlow**: O projeto utiliza código legado migrado. Utilize **apenas** a API de compatibilidade v1:
   ```python
   import tensorflow.compat.v1 as tf
   tf.compat.v1.disable_v2_behavior()
   ```
   **CRÍTICO**: O import do TensorFlow deve ter *lazy load* (dentro das funções de treinamento) ou instanciado com cuidado, para não causar travamento de Kernel no Windows ao inicializar o Notebook.
2. **GDAL**: É um requisito estrito para o M2. Assuma que binários como `gdalbuildvrt` estão disponíveis no PATH via Conda ou OSGeo4W. Use subcomandos nativos de SO para GDAL, mas garanta que o kernel retenha `stdout`/`stderr` do processo para monitoramento síncrono.
3. **Logging**: Evite prints vazios. Utilize um mecanismo de log com emojis ou `widgets.Output()` dedicado (Dashboard de Monitoramento) para informar passos ("info", "error", "warning", "success").
