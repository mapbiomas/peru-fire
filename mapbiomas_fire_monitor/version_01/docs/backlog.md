# Backlog — MapBiomas Fire Monitor

Ideias registradas para depois; nenhuma delas está implementada.

## 1. Sensor VIIRS

- **Status:** não implementado (nenhuma referência no pipeline).
- **Produto a definir:** `VNP09GA` (diário, 500 m / 1 km), `VNP09H1` (8 dias, 500 m)
  ou outro produto VIIRS compatível com as 6 bandas espectrais + NBR.
- **Onde implementar:**
  - `M1_export_logic.py`: novo branch de coleção e `process_viirs` (máscara de QA,
    seleção/renomeação de bandas, `nbr` e `dayOfYear`).
  - `M0_auth_config.py`: `get_sensor_scale`, `get_sensor_start_year` (NPP: 2012)
    e `known_sensors` em `get_model_scale`.
  - `M_mosaics.py`: incluir `viirs` nos métodos suportados (opcional).
  - `M_blocklist.py`: preencher `BLOCKLIST_SOURCES['viirs']` quando existir lista.
- **Decisões pendentes:** produto, bandas, QA, escala e semântica da blocklist
  (granulo/tile vs. índice temporal).

## 2. Períodos temporais adicionais

- **Desejos:** semestral (6 meses), trimestral (3 meses), bimestral (2 meses) e
  bianual (2 anos).
- **Situação atual:** `monthly` e `yearly` estão fixos em:
  - `M0_auth_config.py` (validação, paths GCS/GEE, `mosaic_name`);
  - `M1_export_ui.py` (grade de anos/meses e datas de export);
  - `M2_mosaic_logic.py` / `M2_mosaic_ui.py` (montagem e grid);
  - `M_cache.py` (varredura de assets/chunks);
  - `M4_data_extractor.py`, `M5_inference.py`, `M6_publisher.py` (paths e metadados).
- **Proposta:** registry `PERIODS` em M0 com duração, rótulo, pasta e função
  `period_key(year, month, period)` / `period_dates(...)`; migrar os branches
  `if period == 'monthly'` para essas funções.
- **Decisões pendentes:** nomenclatura (`2026_S1`, `2026_Q1`, `2026_B1`,
  `2024_2025`), pastas (`SEMIANNUAL`, `QUARTERLY`, `BIMONTHLY`, `BIENNIAL`) e
  compatibilidade com os dados monthly/yearly existentes.
