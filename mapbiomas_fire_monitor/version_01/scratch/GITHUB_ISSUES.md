# Issues M5 — Revisão de Código

Repo: `mapbiomas/peru-fire`

---

## Issue 1 — Cache key `cogs_yearly` deveria ser `cogs_annually`

**Arquivo:** `M5_classifier.py:159-161`

```python
period_type = 'monthly' if month else 'yearly'
state = CacheManager.get_state()
known_cogs = set(state.get(f'cogs_{period_type}', []))
```

**Problema:** Quando `month=0` (periodicidade anual), `period_type='yearly'` → busca `state['cogs_yearly']`. Porém o `CacheManager` em `M_cache.py:60-61` inicializa a chave como `'cogs_annually'`:
```python
"cogs_monthly": [],
"cogs_annually": [],
```

**Impacto:** O cache de COGs anuais sempre retorna conjunto vazio. Toda execução do M5 para períodos anuais baixa COGs do GCS via `fs.exists()` em vez de usar o cache local — lentidão desnecessária.

**Reparo:** Trocar `'yearly'` por `'annually'`:
```python
period_type = 'monthly' if month else 'annually'
```

**Labels:** bug, performance

---

## Issue 2 — `_make_cargar` chama `make_job_id` sem campaign (duplicatas)

**Arquivo:** `M5_classifier_ui.py:456-467`

```python
def _make_cargar(m, regs, pers):
    def _h(_):
        self.queue = load_queue()
        for r in regs:
            for p in pers:
                jid = make_job_id(m, r, p)         # sem campaign!
                if any(job['id'] == jid for job in self.queue):
                    skipped += 1
                    continue
                self.queue.append(new_job(m, r, p)) # new_job() usa GLOBAL_OPTS internamente
```

**Problema:** `make_job_id(m, r, p)` gera IDs tipo `"model | region | period"` (sem prefixo de campaign). Já `new_job()` lê `GLOBAL_OPTS['SAMPLING_CAMPAIGN']` e chama `make_job_id()` **com** campaign, gerando IDs tipo `"campaign | model | region | period"`. A checagem de duplicata compara IDs sem campaign contra IDs com campaign → **nunca match** → toda tarea do GCS é readicionada como duplicata em cada clique.

**Reparo:** Extrair `campaign` e passar para ambas as funções:
```python
campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
jid = make_job_id(m, r, p, campaign)
if any(job['id'] == jid for job in self.queue):
    skipped += 1
    continue
self.queue.append(new_job(m, r, p))
```

**Labels:** bug, critical

---

## Issue 3 — Aba Pendentes usa campaign global em vez do campaign do job

**Arquivo:** `M5_classifier_ui.py:540-575`

```python
# linha 540:
campaign = GLOBAL_OPTS.get('SAMPLING_CAMPAIGN', '')
# filtro usa essa campaign...
# linha 575:
t_dir = gcs_full(classified_tiles_dir(model_name, campaign))
```

**Problema:** O diretório de tiles é construído com a **campaign global atual**, não com a campaign de cada job individual. Jobs criados com outra campaign têm tiles contados no diretório errado.

**Impacto:** Barras de progresso e contagem de tiles ficam incorretas quando a campaign selecionada difere da campaign original do job.

**Reparo:** Agrupar jobs por sua própria campaign ou iterar por job ao contar tiles.

**Labels:** bug

---

## Issue 4 — `break` prematuro em `_delete_model_region`

**Arquivo:** `M5_classifier_ui.py:403-412`

```python
campaigns = set(j.get('campaign', '') for j in jobs)
for c in campaigns:
    s_dir = gcs_full(stats_dir(model, c))
    for csv_name in ['stats_tile.csv', 'stats_region.csv']:
        try:
            p = f"{s_dir}/{csv_name}"
            if fs.exists(p):
                fs.rm(p)
        except Exception:
            pass
    break   # <--- BUG
```

**Problema:** O `break` na linha 412 faz o loop `for c in campaigns` executar apenas para o **primeiro** campaign. Se um modelo/região tem jobs em múltiplos campaigns (ex: `monitor_01` e `monitor_02`), os stats do segundo nunca são deletados.

**Reparo:** Remover o `break`.

**Labels:** bug

---

## Issue 5 — `break` em vez de `continue` na falha de grupo

**Arquivo:** `M5_classifier.py:66-77`

```python
for (model_id, period), group in groups.items():
    try:
        _process_period(model_id, period, group, out, progress_callback)
    except Exception as e:
        ...
        for job in group:
            q = load_queue()
            for qj in q:
                if qj['id'] == job['id']:
                    qj['status'] = 'FAILED'
            save_queue(q)
        break   # <--- BUG
```

**Problema:** Quando um grupo `(modelo, periodo)` falha, o `break` encerra **toda** a fase de classificação. Grupos seguintes na fila (mesmo com modelos diferentes) nunca são processados.

**Impacto:** Se o grupo `(model_A, 2025_01)` falha, `(model_A, 2025_02)` e `(model_B, 2025_01)` nunca são tentados.

**Reparo:** Trocar `break` por `continue`.

**Labels:** bug

---

## Issue 6 — Jobs marcados FINISHED mesmo com merge/upload falho

**Arquivo:** `M5_classifier.py:103-118`

```python
mosaic_path = merge_region_tiles(model_id, region, period, fs=fs, campaign=campaign)
if mosaic_path:
    job['progress'] = '50% (mosaic)'
    save_queue(queue)
if job.get('upload_gee'):
    upload_to_gee(model_id, region, period, fs=fs, campaign=campaign)
    job['progress'] = '100% (published)'
else:
    job['progress'] = '100% (mosaic)'
job['status'] = 'FINISHED'
save_queue(queue)
```

**Problema:** Se `merge_region_tiles` retorna `None` (nenhum tile classificado), o progresso `'50% (mosaic)'` é pulado, mas o job ainda é marcado `FINISHED`. Se `upload_gee=True`, `upload_to_gee` é chamada mas internamente retorna `False` se o mosaico não existe — o upload silenciosamente falha, mas o job é marcado como `'100% (published)'`.

**Impacto:** Mosaicos inexistentes são reportados como concluídos com sucesso.

**Reparo:**
```python
mosaic_path = merge_region_tiles(model_id, region, period, fs=fs, campaign=campaign)
if not mosaic_path:
    job['status'] = 'FAILED'
    job['progress'] = 'error: no mosaic generated'
    save_queue(queue)
    continue
job['progress'] = '50% (mosaic)'
...
```

**Labels:** bug

---

## Issue 7 — Queue carregada/salva N vezes no tratamento de erro

**Arquivo:** `M5_classifier.py:71-76`

```python
for job in group:
    q = load_queue()
    for qj in q:
        if qj['id'] == job['id']:
            qj['status'] = 'FAILED'
    save_queue(q)
```

**Problema:** Para N jobs no grupo, o arquivo `m5_queue.json` é lido e escrito N vezes. Deveria carregar uma vez, modificar todos, salvar uma vez.

**Reparo:**
```python
q = load_queue()
for job in group:
    for qj in q:
        if qj['id'] == job['id']:
            qj['status'] = 'FAILED'
save_queue(q)
```

**Labels:** enhancement, performance

---

## Issue 8 — Progress update afeta todos jobs com mesmo (model, period)

**Arquivo:** `M5_classifier.py:231-237`

```python
for qj in q:
    if (qj['model'], qj['period']) == (model_id, period):
        qj['progress'] = f"{processed + i}/{total_cells_group} ({pct:.1%})"
```

**Problema:** Se múltiplas regiões compartilham o mesmo `(model, period)`, **todas** recebem o mesmo valor de progresso, mesmo que o loop externo esteja processando apenas uma região. O progresso da Região A pula quando tiles da Região B estão sendo processados.

**Impacto:** Barras de progresso enganosas para o usuário.

**Reparo:** Match pelo `id` do job em vez de `(model, period)`.

**Labels:** bug

---

## Issue 9 — Código morto: `classify_cell` wrapper não usado

**Arquivo:** `M5_inference.py:169-198`

**Problema:** A função `classify_cell` baixa COGs localmente e depois chama `classify_cell_with_cogs`. Porém `M5_classifier.py` chama `classify_cell_with_cogs` diretamente com COGs pré-baixados. A função wrapper não é chamada por nenhum código M5.

**Impacto:** Código morto que aumenta a superfície de manutenção sem benefício.

**Reparo:** Remover `classify_cell` ou marcá-la como deprecated.

**Labels:** cleanup

---

## Issue 10 — `scale=10` fixo no upload GEE

**Arquivo:** `M5_publisher.py:244-245`

```python
scale=10,
maxPixels=1e13,
```

**Problema:** `scale=10` assume resolução Sentinel-2 (10m). Se o modelo usou Landsat (30m) ou MODIS (250m), a escala está errada.

**Reparo:** Derivar escala do sensor/configuração do modelo.

**Labels:** enhancement

---

## Issue 11 — Typo: `peridiocity_active`

**Arquivo:** `M5_classifier_ui.py:1143`

```python
def run_m5_ui(years=None, peridiocity_active=None):
```

**Problema:** `peridiocity_active` → `periodicity_active` (i extra). Quebra chamadas externas que usam o nome correto.

**Reparo:** Renomear para `periodicity_active`.

**Labels:** bug

---

## Issue 12 — Lock no `m5_queue.json`

**Arquivo:** `M5_queue.py` (todo o arquivo)

**Problema:** Nenhum mecanismo de lock. Se UI e engine de classificação rodam simultaneamente (ex: dois kernels Colab, ou uma célula rodando enquanto outra carrega), podem sobrescrever alterações uma da outra.

**Impacto:** Jobs podem ser perdidos ou entrar em estado inconsistente.

**Reparo:** Implementar file locking com `portalocker` ou usar GCS para o arquivo de queue.

**Labels:** enhancement

---

## Issue 13 — `_safe_update` assume que `f` é Dropdown

**Arquivo:** `M5_classifier_ui.py:1077-1083`

```python
def _safe_update(f, new_ops):
    old = f.value
    f.options = new_ops
    if old in new_ops:
        f.value = old
    else:
        f.value = new_ops[0]
```

**Problema:** A função assume que `f` tem `.options` (Dropdown, Select). Se por engano um Checkbox ou outro widget sem `.options` for passado, quebra em runtime.

**Reparo:** Adicionar type guard:
```python
if not hasattr(f, 'options'):
    return
```

**Labels:** enhancement

---

## Issue 14 — `save_queue(load_queue())` perde status RUNNING

**Arquivo:** `M5_classifier.py:210-211`

```python
job['status'] = 'RUNNING'
save_queue(load_queue())
```

**Problema:** `load_queue()` retorna uma **nova lista** do disco. A modificação `job['status'] = 'RUNNING'` foi feita no objeto em memória da lista `pending` (filtrada da queue anterior), não no objeto recém-carregado. `save_queue` salva a lista recém-carregada (sem a modificação), efetivamente perdendo a atualização de status.

**Impacto:** O job nunca é marcado como `RUNNING` no arquivo queue.json. A UI nunca vê o job como "em execução".

**Reparo:**
```python
q = load_queue()
for qj in q:
    if qj['id'] == job['id']:
        qj['status'] = 'RUNNING'
save_queue(q)
```

**Labels:** bug, critical

---

## Issue 15 — Checkbox widget armazenado em vez de booleano

**Arquivo:** `M5_classifier_ui.py:592-599`

```python
chk = widgets.Checkbox(
    value=self._card_checkboxes.get(model_name, False),  # linha 593
    ...
)
chk.observe(lambda change, m=model_name: self._sync_card_enabled(m, change['new']), names='value')
self._card_checkboxes[model_name] = chk  # linha 599 — guarda o widget!
```

**Problema:** Na primeira execução, `_card_checkboxes.get(model_name, False)` retorna `False` (booleano) → Checkbox criado com `value=False`. Na linha 599, o **widget** é armazenado no dict. Na segunda execução, `_card_checkboxes.get(model_name, False)` retorna o **widget** (não o booleano) → `widgets.Checkbox(value=<widget>)` → `TraitError: expected a boolean, not a Checkbox`.

**Impacto:** `_render_pending()` quebra na segunda chamada. Todas as abas que chamam `_refresh_ui()` → `_render_pending()` falham: carregar tarea do GCS, deletar modelo, limpar fila.

**Reparo:** Extrair `.value` do widget se necessário:
```python
chk_cache = self._card_checkboxes.get(model_name, False)
value = chk_cache.value if isinstance(chk_cache, widgets.Checkbox) else chk_cache
```

**Labels:** bug, critical

---

## Issue 16 — Falta `.items()` na iteração do dict `groups`

**Arquivo:** `M5_classifier.py:62`

```python
for (model_id, period), group in groups:
```

**Problema:** `groups` é um `defaultdict(list)`. Iterar diretamente sobre um dict (`for x in dict_var:`) produz apenas **chaves**, não pares `(chave, valor)`. Cada chave é uma tupla de 2 elementos `(modelo, periodo)`. O desempacotamento `(model_id, period), group` espera um par (chave, valor), mas recebe apenas a chave de 2 elementos → `ValueError: too many values to unpack (expected 2)`.

**Impacto:** `run_m5_queue` quebra na fase de classificação antes de processar qualquer tile.

**Reparo:** `for (model_id, period), group in groups.items():`

**Labels:** bug, critical
