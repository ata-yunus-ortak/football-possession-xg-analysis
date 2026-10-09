# Offline analysis modules

Start with the [project README](../README.md).

- `analysis_core.py`: source matching, statistical summaries and score replay.
- `oyun_durumu_hesapla.py`: rebuild local score-state tables; always offline.
- `analiz_possession_xg.py` / `analiz_oyun_durumu.py`: individual plot entry points.
- `overview.py`: compact portfolio charts derived from the same aggregate estimates.
- `ortak.py`: side-effect-free paths and team-name mappings.
- `veri_cek.py`, `fbref_cache_parse.py`, `serie_a_tamamla.py`: optional historical collection utilities; live collection was not validated during preparation.

Use `python run_analysis.py` from the repository root for the full validated workflow. Provider inputs under `data/` are ignored by Git.
