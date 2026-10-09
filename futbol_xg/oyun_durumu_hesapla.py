"""Rebuild score-state labels from local CSVs, without network access."""
import argparse
import pandas as pd
from analysis_core import reconstruct_game_states, summarize_states
from ortak import DATA_DIR

def rebuild(data_dir=DATA_DIR, durations=None):
    paths = sorted((data_dir / "ham_sutlar").glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No shot CSVs in {data_dir / 'ham_sutlar'}; see DATA_SOURCES.md")
    shots = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    fixtures = pd.read_csv(data_dir / "understat_team_match.csv")
    ends = pd.read_csv(durations) if durations else None
    events, exposure, matches, missing = reconstruct_game_states(shots, fixtures, ends, exclude_score_mismatches=True)
    summary = summarize_states(events, exposure)
    events.to_csv(data_dir / "sut_game_state.csv", index=False)
    exposure.to_csv(data_dir / "match_state_exposure.csv", index=False)
    summary.to_csv(data_dir / "takim_durum_ozet.csv", index=False)
    return events, exposure, matches, missing, summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--durations", help="Optional user-provided match-duration CSV")
    args = parser.parse_args()
    events, _, matches, missing, _ = rebuild(durations=args.durations)
    print(f"Rebuilt {len(events):,} events in {len(matches):,} matches; {len(missing)} fixtures without events.")

if __name__ == "__main__":
    main()
