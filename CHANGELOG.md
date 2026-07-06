# CHANGELOG

All notable changes to the Peru Fire Monitor pipeline.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — dev

### Added

### Fixed

### Changed

## [1.1.0] — 2026-07-05

### Fixed
- M5: masked pixels (clouds, out-of-bounds) no longer classified as fire. Uses `dayOfYear > 0` (Int16) as valid pixel reference instead of broken `src_nodata` chain.
- M5: `SymbolicTensor` error in `predict_on_batch`. Forced eager mode via `tf.config.run_functions_eagerly(True)` + `np.asarray()` wrapper.
- M5_classifier.py `_log()` now highlights `[ERROR]` in red and `[WARN]` in orange via THEME colors.

### Changed
- **Sync button unified across all modules**: M1/M2/M4/M5/M6 now show `"Sincronizar Dados"` (Lang.SYNC_DATA) with refresh icon and green (`success`) color.
- M5 sync now calls `CacheManager.build_full_cache()` and repopulates model checkboxes — no kernel restart needed to see newly trained models.
- M4/M5 user-facing strings internationalized in 5 languages (EN/ES/PT/FR/ID). Removed 7 hardcoded UI strings.
- M4 header, sample pane label, training progress bar, compatibility errors now use `Lang.XXX`.

### Added
- CHANGELOG.md
- Version table in notebook intro

## [1.0.0] — main (2026-06-23)

Initial tagged release. Pipeline M0-M8 Sentinel-2, campaign `MONITOR_01`, LANDSAT 30m legacy pipeline.
Result of ADRs 001–009. See [adr/](../adr/) for full decision history.
