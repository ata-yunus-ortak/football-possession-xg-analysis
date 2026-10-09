"""Rebuild and validate all analysis artifacts from local source CSVs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "futbol_xg"))
import pandas as pd
from analysis_core import merge_sources, possession_dilimle, reconcile_xg, audit_event_order
from oyun_durumu_hesapla import rebuild
from analiz_possession_xg import generate as possession_figures
from analiz_oyun_durumu import generate as state_figures
from overview import generate as overview_figures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "futbol_xg" / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--durations", type=Path, help="Optional user-provided match end times")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--synthetic", action="store_true", help="Label invented demo data explicitly")
    args = parser.parse_args()
    if args.bootstrap < 0:
        parser.error("--bootstrap must be non-negative")
    inputs = [args.data_dir / "fbref_team_match.csv", args.data_dir / "understat_team_match.csv"]
    if not all(p.exists() for p in inputs):
        parser.error("Local input CSVs missing. See DATA_SOURCES.md; no network requests are made by this command.")
    inputs += sorted((args.data_dir / "ham_sutlar").glob("*.csv"))
    if args.durations:
        inputs.append(args.durations)
    fbref, fixtures = pd.read_csv(inputs[0]), pd.read_csv(inputs[1])
    merged, report = merge_sources(fbref, fixtures)
    events, exposure, matches, missing, summary = rebuild(args.data_dir, args.durations)
    totals = exposure.groupby(["league", "season", "game_id", "team"]).minutes.sum()
    expected = matches.set_index(["league", "season", "game_id"]).end_minute
    for key, minutes in totals.items():
        if abs(minutes - expected.loc[key[:3]]) > 1e-8:
            raise ValueError(f"Exposure does not sum to match duration: {key}")
    within = possession_dilimle(merged)
    complete = within.dropna(subset=["xg", "sut"])
    xg_audit = reconcile_xg(events, fixtures)
    discrepancies = xg_audit.loc[xg_audit.xg_difference.abs() > 0.001]
    ordering_audit = audit_event_order(events, fixtures)
    report.update({
        "dataset_type": "synthetic_demonstration" if args.synthetic else "provider_snapshot",
        "shot_events": len(events), "attacking_shots": int(events.is_attacking_shot.sum()),
        "own_goals": int((events.result == "Own Goal").sum()),
        "verified_score_matches": int(matches.score_verified.sum()), "fixtures_without_shots": missing,
        "excluded_score_matches": matches.loc[~matches.score_verified, ["league", "season", "game_id", "replayed_score", "fixture_score", "excluded_events"]].to_dict("records"),
        "estimated_duration_matches": int(((matches.duration_source == "estimated") & matches.score_verified).sum()),
        "same_minute_order": "Stable source order retained; true order within an integer minute is not verified.",
        "event_order_diagnostics": {
            "scope": "Score-verified fixtures only; numeric shot-ID order is an unverified sensitivity, not a chronology correction.",
            "fixtures_with_numeric_ids": int(ordering_audit.numeric_id_order_available.sum()),
            "minute_decreases_in_numeric_id_order": int(ordering_audit.minute_decreases.sum()),
            "fixtures_with_minute_decreases": int(ordering_audit.minute_decreases.gt(0).sum()),
            "scoring_minute_decreases": int(ordering_audit.scoring_minute_decreases.sum()),
            "alternative_state_labels": int(ordering_audit.alternative_state_labels.sum()),
            "fixtures_with_alternative_states": int(ordering_audit.alternative_state_labels.gt(0).sum()),
            "interpretation": "No period or precise event clock is available. Minute ties and possible halftime clock overlap leave intermediate score states and exposure uncertain. Final scores do not verify chronology.",
        },
        "possession_range": "25-75 inclusive", "range_observations": len(within),
        "excluded_range_observations": len(merged) - len(within),
        "complete_shot_quality_observations": len(complete),
        "excluded_incomplete_shot_quality_observations": len(within) - len(complete),
        "combined_xg_per_shot": float(complete.xg.sum() / complete.sut.sum()),
        "bootstrap_repetitions": args.bootstrap, "bootstrap_seed": 2026,
        "xg_reconciliation": {
            "scope": "Score-verified fixtures only; attacking-shot xG sum versus fixture-summary xG.",
            "absolute_tolerance": 0.001,
            "team_match_rows": len(xg_audit),
            "missing_fixture_xg_rows": int(xg_audit.fixture_xg.isna().sum()),
            "team_match_discrepancies": len(discrepancies),
            "fixtures_with_discrepancies": len(discrepancies[["league", "season", "game_id"]].drop_duplicates()),
            "summed_event_xg": float(xg_audit.event_xg.sum()),
            "summed_fixture_xg": float(xg_audit.fixture_xg.sum()),
            "maximum_absolute_difference": float(xg_audit.xg_difference.abs().max()),
            "interpretation": "Aggregate definitions may differ. Discrepancies do not trigger event edits or additional exclusions; final-score verification is not xG concordance.",
        },
        "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    subtitle = "SYNTHETIC DEMONSTRATION" if args.synthetic else "2025-26 snapshot"
    possession_results = possession_figures(merged, args.output_dir, args.bootstrap, subtitle)
    state_results = state_figures(summary, args.output_dir, subtitle)
    overview_figures(possession_results, state_results, args.output_dir, subtitle)
    matches.to_csv(args.output_dir / "match_validation.csv", index=False)
    # Keep source-like values local; publish only derived differences and flags.
    xg_audit.to_csv(args.data_dir / "xg_reconciliation_detail.csv", index=False)
    xg_audit[["league", "season", "game_id", "team", "xg_difference", "within_tolerance"]].to_csv(
        args.output_dir / "xg_reconciliation.csv", index=False)
    ordering_audit.to_csv(args.output_dir / "event_order_diagnostics.csv", index=False)
    (args.output_dir / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Validated {report['verified_score_matches']:,} match scores; {len(events):,} included events ({report['own_goals']} own goals).")
    print(f"Excluded {len(report['excluded_score_matches'])} score-inconsistent matches; {len(missing)} fixtures lack events.")
    print(f"xG reconciliation: {len(discrepancies):,} team-match totals differ by more than 0.001; see xg_reconciliation.csv.")
    print(f"Possession data: {len(report['possession_leagues'])} leagues; results saved to {args.output_dir}")


if __name__ == "__main__":
    main()
