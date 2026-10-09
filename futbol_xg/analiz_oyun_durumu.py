"""Exploratory score-state plots with estimated time exposure labelled."""
import pandas as pd
from analysis_core import STATES, STATE_LABELS
from ortak import DATA_DIR, CIKTI_DIR, LIG_ADLARI
from plot_utils import panel_2x3_olustur, paneli_kaydet, draw_state_bars, common_limits

def aggregate(frame):
    g = frame.groupby("durum")[["toplam_xg", "toplam_sut", "toplam_gol", "toplam_dakika"]].sum().reindex(STATES)
    g["label"] = [STATE_LABELS[state] for state in g.index]
    g["n"] = g.toplam_sut
    return g

def generate(frame, output_dir=CIKTI_DIR, subtitle="2025-26 snapshot"):
    specs = [
        ("durum_sut_kalitesi.png", "Shot quality by score state", "Summed shot xG / attacking shots", "toplam_xg", "toplam_sut", 1),
        ("durum_xg_90.png", "xG production by score state", "xG / 90 estimated minutes", "toplam_xg", "toplam_dakika", 90),
        ("durum_donusum.png", "Finishing conversion by score state", "Non-own-goal goals / summed shot xG", "toplam_gol", "toplam_xg", 1),
    ]
    estimated = bool(frame.estimated_duration.any())
    for filename, title, xlabel, numerator, denominator, scale in specs:
        if denominator == "toplam_dakika" and not estimated:
            xlabel = "xG / 90 provided minutes"
        fig, axes = panel_2x3_olustur(f"{title} | {subtitle}")
        tables = []
        for ax, (league, name) in zip(axes, list(LIG_ADLARI.items()) + [(None, f"Combined: {frame.league.nunique()} leagues")]):
            subset = frame if league is None else frame.loc[frame.league == league]
            if subset.empty:
                ax.set_title(name)
                ax.text(0.5, 0.5, "No data in this snapshot", ha="center", transform=ax.transAxes)
                ax.set_yticks([])
                continue
            stats = aggregate(subset)
            stats["value"] = stats[numerator].div(stats[denominator].where(stats[denominator] > 0)) * scale
            draw_state_bars(ax, stats, name, xlabel)
            tables.append(stats)
        common_limits(axes, tables)
        note = "Exploratory minute-based state labels; chronology is ambiguous. Own goals excluded. n = attacking shots."
        if denominator == "toplam_dakika":
            note = "EXPOSURE ESTIMATED: max(90, last event minute + 1). Rates and minute-based state labels are approximate." if estimated else "Match durations provided; minute-based state chronology remains ambiguous."
        fig.text(0.5, 0.015, note, ha="center", fontsize=8)
        paneli_kaydet(fig, output_dir / filename)
    result = []
    for league in list(LIG_ADLARI) + [None]:
        subset = frame if league is None else frame.loc[frame.league == league]
        if subset.empty:
            continue
        g = aggregate(subset).reset_index()
        g["league"] = league or "Combined"
        g["xg_per_shot"] = g.toplam_xg / g.toplam_sut.where(g.toplam_sut > 0)
        g["xg_90"] = g.toplam_xg / g.toplam_dakika.where(g.toplam_dakika > 0) * 90
        g["conversion"] = g.toplam_gol / g.toplam_xg.where(g.toplam_xg > 0)
        g["estimated_duration"] = bool(subset.estimated_duration.any())
        result.append(g)
    result = pd.concat(result, ignore_index=True)
    result.to_csv(output_dir / "game_state_summary.csv", index=False)
    return result

def main():
    generate(pd.read_csv(DATA_DIR / "takim_durum_ozet.csv"))
    print(f"Saved state figures and summaries to {CIKTI_DIR}")

if __name__ == "__main__":
    main()
