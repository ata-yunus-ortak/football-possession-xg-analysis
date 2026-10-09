"""Descriptive possession analysis with match-cluster bootstrap intervals."""
import pandas as pd
from analysis_core import merge_sources, possession_statistics
from ortak import DATA_DIR, CIKTI_DIR, LIG_ADLARI
from plot_utils import panel_2x3_olustur, paneli_kaydet, draw_points, common_limits
METRICS = {
 "shot_quality": ("possession_sut_kalitesi.png", "Shot quality", "Fixture-summary xG / FBref shots"),
 "finishing": ("possession_bitiris_verimliligi.png", "Finishing residual", "Goals minus fixture xG / team-match"),
 "volume": ("possession_xg_hacmi.png", "Chance volume", "Fixture-summary xG / team-match"),
}

def veriyi_birlestir(data_dir=DATA_DIR):
    return merge_sources(pd.read_csv(data_dir / "fbref_team_match.csv"), pd.read_csv(data_dir / "understat_team_match.csv"))[0]

def generate(frame, output_dir=CIKTI_DIR, repetitions=1000, subtitle="2025-26 snapshot"):
    leagues = [league for league in LIG_ADLARI if league in set(frame.league)]
    output_dir.mkdir(parents=True, exist_ok=True)
    all_stats = []
    for metric, (filename, name, xlabel) in METRICS.items():
        fig, axes = panel_2x3_olustur(f"Possession and {name.lower()} | {subtitle}")
        panels = list(LIG_ADLARI.items()) + [(None, f"Combined: {len(leagues)} available leagues")]
        tables = []
        for ax, (league, title) in zip(axes, panels):
            subset = frame if league is None else frame.loc[frame.league == league]
            stats = possession_statistics(subset, metric, repetitions=repetitions)
            draw_points(ax, stats, title, xlabel)
            tables.append(stats)
            if not stats.empty:
                all_stats.append(stats.assign(league=league or "Combined", metric=metric))
        common_limits(axes, tables, signed=metric == "finishing")
        fig.text(0.5, 0.015, "95% within-bin match-cluster bootstrap intervals; n = complete team-match observations. Range: 25-75% (inclusive).", ha="center", fontsize=8)
        paneli_kaydet(fig, output_dir / filename)
    result = pd.concat(all_stats, ignore_index=True)
    result.to_csv(output_dir / "possession_summary.csv", index=False)
    return result

def main():
    generate(veriyi_birlestir())
    print(f"Saved possession figures and summaries to {CIKTI_DIR}")

if __name__ == "__main__":
    main()
