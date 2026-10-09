# Data sources and local reproduction

## Case-study snapshot

The input files were copied from an existing personal football-analysis workspace on **8 October 2026**. This is the preparation date, not a verified original acquisition date. Dated fixture tables span August 2025–May 2026. Source-file SHA-256 hashes are saved in `results/validation_report.json`.

- **FBref**: possession and shot-count match logs, read through the existing source-collection utilities and cached HTML parsing.
- **Understat**: team-match xG/score summaries and shot events, previously collected through `soccerdata`.

The supplied files did not contain a redistribution licence or a complete acquisition manifest. Raw tables therefore remain local and are excluded by `.gitignore` and the upload-package builder. Published results are analysis outputs, not a licence to redistribute the underlying data. Provider access/usage policies should be checked directly when acquiring a new snapshot.

The synthetic example and regression fixtures are invented specifically to exercise this implementation; they are not scraped match records.

## Minimum input layout

```text
LOCAL_DATA/
  fbref_team_match.csv
  understat_team_match.csv
  ham_sutlar/
    one_or_more_shot_files.csv
```

FBref columns: `league,season,team,opponent,venue,GF,possession,sut`. Existing extra columns (date, GA, on-target shots) are allowed. `sut` means shot count. Missing shots are kept visible, but cannot contribute to a shot-quality ratio.

Understat columns: `league,season,game_id,team,opponent,venue,gol,xg`. `gol` is the final score for that team. Each fixture has one Home and one Away row. League/season/team/opponent/venue must be unique; mappings in `ortak.py` reconcile source names.

Event columns: `league,season,game_id,shot_id,team,minute,xg,result`. Results currently accepted: Goal, Own Goal, Missed Shot, Blocked Shot, Saved Shot and Shot On Post. For this snapshot an own-goal event's `team` denotes the team conceding the goal. The opponent is credited, and replayed final scores are checked against fixture summaries. A different provider convention needs an explicit adapter.

## Known coverage issues

- Serie A is missing from the FBref possession table. The combined possession plot contains four leagues.
- 103 FBref records lack shot counts; 100 lie inside the selected possession range.
- Fixture `29840` (Ligue 1) has no event data and missing match xG. Its score-state exposure is not invented.
- Fixture `29482` (La Liga) contains repeated event payloads with different shot IDs; event replay gives 2–2 while the fixture summary gives 1–1. All 46 events are quarantined from score-state metrics. Aggregate possession analysis uses independent team-match inputs and has a different coverage scope.
- Summed shot xG and fixture-summary xG differ above 0.001 in 1,400 score-verified team-match rows across 1,135 fixtures. These are separate provider quantities; their aggregation relationship is unverified. Public fixture identifiers, derived differences and tolerance flags are in `results/xg_reconciliation.csv`. Detailed values remain beside the ignored local inputs in `xg_reconciliation_detail.csv`.
- Period information, precise event timestamps and the original event clock string are unavailable. Integer minutes leave within-minute ordering and possible halftime clock overlap ambiguous. Numeric-ID sensitivity diagnostics do not verify ID chronology; score-state labels remain exploratory.
- Real match end times are unavailable. All real-case exposure rates currently use estimated end times.

## Optional collection utilities

`requirements-data.txt` lists separate optional dependencies. Live collectors depend on upstream schemas, provider availability and an external local cache; their outputs must pass the offline checks before interpretation. They are not invoked by `run_analysis.py`, tests or CI. No attempt to bypass provider restrictions is part of the supported reproduction workflow.

## GitHub upload

The local checkout retains inputs for the owner to rerun the analysis. Upload the curated ZIP or Git's non-ignored files; uploading the entire local directory through a file picker could include ignored raw data and the virtual environment. The archive builder includes only the explicit publication directories/files and verifies exclusion of raw inputs, binaries and credentials.
