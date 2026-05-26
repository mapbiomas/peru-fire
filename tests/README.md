# Tests — MapBiomas Fire Monitor

Testes e benchmarks independentes do pipeline principal.

## Estrutura

```
tests/
├── README.md
└── benchmarks/
    ├── vsigs_benchmark.py      # Backend: funcoes de medicao de performance
    └── vsigs_benchmark.ipynb   # Notebook: executa os benchmarks com UI
```

## benchmarks/vsigs_benchmark

Compara duas estrategias de leitura de COGs do GCS:

| Teste | Estrategia | O que mede |
|-------|-----------|-----------|
| A | Download → rasterio | Tempo de download + leitura + RAM cache |
| B | `/vsigs/` → rasterio | Tempo de leitura streaming + RAM |
| C | Download → GDAL VRT → COG | Simula merge M2 atual (NUM_THREADS=2) |
| D | `/vsigs/` → GDAL VRT → COG | Simula merge M2 otimizado (NUM_THREADS=ALL_CPUS) |

### Como rodar

```bash
cd tests/benchmarks
jupyter notebook vsigs_benchmark.ipynb
```

### Requisitos

- Ambiente conda `environment.yml` da raiz do projeto
- Credenciais GCS configuradas (`gcloud auth application-default login`)
- (opcional) `psutil` para medicao precisa de RAM
- (opcional) `matplotlib` para grafico de barras

### Resultado esperado

| Métrica | Download | /vsigs/ | Ganho |
|---------|----------|---------|-------|
| Tempo leitura 1 COG | ~10s | ~2s | 5x |
| Tempo merge 3 bandas | ~52s | ~16s | 3x |
| RAM cache disco | +GBs | 0 | infinito |

## Links

- [[ADR-007 - Otimizacao IO M2 M6 com paralelismo e streaming]]
- [[2026-05-25 — Plano de otimização M2 e M6]]
