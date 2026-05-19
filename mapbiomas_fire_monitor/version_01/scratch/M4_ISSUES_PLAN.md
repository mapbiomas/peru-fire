# Plano de Ação — Issues M4

Repo: `mapbiomas/peru-fire`

---

## Fase 1 — CRASHES (6 issues)

**Propósito:** Impedir que o usuário encontre telas de erro ao interagir com o M4.

### 1. `band_chk_map` desempacotamento errado (CRASH)

**Arquivo:** `M4_ui.py:90` (tb `M4_model_trainer_backup.py:1247`)

```python
# ATUAL — desempacota 3, mas chave tem 4 elementos
for (s, m, b), chk in self.band_chk_map.items():
```

```python
# CORRETO
for (s, m, p, b), chk in self.band_chk_map.items():
```

**Impacto:** `_load_config_into_widgets()` → `ValueError` ao tentar retreinar.

---

### 2. Checkboxes de intent nunca criados (CRASH)

**Arquivo:** `M4_ui.py`

`self.cb_retrain`, `self.cb_reextract`, `self.cb_borrar_retrain` são referenciados em:
- `_load_config_into_widgets()` — `.value`, `.observe()`, `.unobserve()`
- `start_training()` — `.value = False`
- `_on_intent_cb_change()` — iteração

Mas **nunca são instanciados** — nem em `__init__`, nem em `display()`.

**Reparo:** Ou criar os widgets no `__init__`:
```python
self.cb_retrain = widgets.Checkbox(...)
self.cb_reextract = widgets.Checkbox(...)
self.cb_borrar_retrain = widgets.Checkbox(...)
```
Ou, se são código morto, remover todas as referências.

**Impacto:** `AttributeError` em qualquer retrain.

---

### 3. `_refresh_models_list()` nunca definido (CRASH)

**Arquivo:** `M4_ui.py` — chamado em 5 lugares (linhas 268, 273, 277, 605, e via `M4_analytics.py`)

**Reparo:** O método que deveria ser chamado é `_refresh_canvas_hub()`. Renomear as chamadas.

**Impacto:** Crash ao clicar em qualquer estrela de rating (Nota Humana).

---

### 4. `update_model_metadata()` sem prefixo do bucket (CRASH)

**Arquivo:** `M4_algorithms_dnn.py:454`

```python
# ATUAL — fs.open sem bucket prefix
path = f"{base_path}/metadata.json"
with fs.open(path, 'r') as f:
```

```python
# CORRETO
path = f"{CONFIG['bucket']}/{base_path}/metadata.json"
with fs.open(path, 'r') as f:
```

**Impacto:** `update_model_metadata()` escreve no bucket errado. Rating de usuário nunca persiste.

---

### 5. Fallback `available_combos` com chave 2-tupla (CRASH)

**Arquivo:** `M4_ui.py:518`

```python
# ATUAL — fallback usa 2-tupla (sensor, mosaic)
('sentinel2', 'minnbr'): set([...])
# Mas iteração espera 3-tupla (s, m, p)
for (s, m, p) in sorted(available_combos.keys()):
```

**Reparo:** Adicionar period `'monthly'` às chaves do fallback:
```python
('sentinel2', 'minnbr', 'monthly'): set([...])
```

**Impacto:** `ValueError` se cache do COG estiver vazio.

---

### 6. Bucket hardcoded no path parsing (CRASH)

**Arquivo:** `M4_analytics.py:241`, `M4_ui.py:653`

```python
# ATUAL
clean_path = m_path.replace('gs://', '').replace('mapbiomas-fire/', '').lstrip('/')
```

```python
# CORRETO
clean_path = m_path.replace('gs://', '').replace(f"{CONFIG['bucket']}/", '').lstrip('/')
```

**Impacto:** Se `CONFIG['bucket']` mudar, analytics não carrega.

---

## Fase 2 — LÓGICA (6 issues)

**Propósito:** Corrigir comportamento incorreto que pode passar despercebido.

### 7. `load()` usa `gsutil` enquanto `save()` usa gcsfs

**Arquivo:** `M4_algorithms_dnn.py:194`

**Reparo:** Substituir `subprocess.run(['gsutil', 'cp', ...])` por `fs.get()` para consistência com `save()` (que usa `fs.put()`).

**Impacto:** Quebra se `gsutil` não estiver instalado (ex: Colab sem Google Cloud SDK).

---

### 8. Chaves erradas no backup trainer

**Arquivo:** `M4_model_trainer_backup.py:1236`

```python
# ATUAL — chaves não existem no metadata
self.w_iters.value = str(hp.get('iters', 5000))
self.w_batch.value = str(hp.get('batch', 1000))
```

```python
# CORRETO
self.w_iters.value = str(hp.get('n_iters', 5000))
self.w_batch.value = str(hp.get('batch_size', 1000))
```

**Impacto:** Retrain sempre usa 5000 iterações e batch 1000, ignorando valores originais.

---

### 9. Thread safety no CacheManager

**Arquivo:** `M_cache.py`

`get_state()`, `add_asset()`, `remove_asset()` acessam `CacheManager._state` sem o lock que só é usado em `load()`, `clear()`, `save()`.

**Reparo:** Envolver todos os acessos a `_state` com o `_lock`.

**Impacto:** Race condition em builds concorrentes do cache.

---

### 10. Sincronização GCS vs Local inconsistente

**Arquivo:** `M_cache.py:398-429`

Se `fs.open(gcs_path, 'w')` falha, o arquivo local já foi escrito. Se o local falha mas GCS não, o oposto.

**Reparo:** Escrever local primeiro, depois GCS. Se GCS falhar, reverter o local.

---

### 11. `_save_m4_metadata()` filtra dados

**Arquivo:** `M4_hub_manager.py:24`

```python
safe = {k: v for k, v in data.items() if k in ('meta', 'metadata')}
```

**Reparo:** Salvar o dict completo.

**Impacto:** Perda de dados entre versões do hub manager.

---

### 12. Bare `except: pass` engole erros

**Arquivo:** `M4_ui.py:664,668`

**Reparo:** Logar o erro em vez de engolir:
```python
except Exception as e:
    print(f"[WARN] Erro ao carregar metadados: {e}")
```

**Impacto:** GCS offline → modelos somem sem aviso.

---

## Fase 3 — ROBUSTEZ (8 issues)

**Propósito:** Qualidade de código, debugabilidade, prevenção de bugs futuros.

| # | Arquivo | Reparo |
|---|---------|--------|
| **13** | `M4_ui.py:611+841` | Remover primeira definição duplicada de `_on_canvas_batch_action` |
| **14** | `M4_ui.py:605` | Corrigir `_refresh_ui()` para chamar `_refresh_canvas_hub()` ou remover |
| **15** | `M4_ui.py:1071` | Envolver `int()`/`float()` em try/except com mensagem para o usuário |
| **16** | `M0_auth_config.py:67-73` | Adicionar `'FIRE_POTENTIAL_FILTER': False` ao `GLOBAL_OPTS` |
| **17** | Geral (20+ locais) | Trocar bare `except:` por `except Exception:` |
| **18** | `M4_analytics.py:264` | Aceitar `ui` como parâmetro opcional em vez de `__main__` |
| **19** | `M4_data_extractor.py:169` | Remover linhas de log duplicadas |
| **20** | `M4_analytics.py:389` | `threading.Thread(daemon=True)` → `threading.Timer` não-daemon |

---

## Arquivos Afetados

| Arquivo | Issues |
|---------|--------|
| `M4_ui.py` | 1, 2, 3, 5, 6, 12, 13, 14, 15 |
| `M4_analytics.py` | 6, 18, 20 |
| `M4_algorithms_dnn.py` | 4, 7 |
| `M4_model_trainer_backup.py` | 1, 8 |
| `M_cache.py` | 9, 10 |
| `M4_hub_manager.py` | 11 |
| `M0_auth_config.py` | 16 |
| `M4_data_extractor.py` | 19 |
