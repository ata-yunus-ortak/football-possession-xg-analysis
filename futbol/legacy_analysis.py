"""Earlier possession/goals exploration. Input fixtures lack match identifiers."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = {"Premier League": "epl_possession_data_full.csv", "La Liga": "la_liga_possession_data_full.csv",
         "Bundesliga": "bundesliga_possession_data_full.csv", "Serie A": "serie_a_possession_data_full.csv", "Ligue 1": "ligue_1_possession_data_full.csv"}


def main(home_away=False, single=None):
    pieces = []
    for league, name in FILES.items():
        path = ROOT / name
        if path.exists():
            pieces.append(pd.read_csv(path).assign(league=league))
    if not pieces:
        raise FileNotFoundError("Earlier exploratory CSVs are local-only; see DATA_SOURCES.md")
    data = pd.concat(pieces, ignore_index=True)
    data = data[data.Possession.between(25, 75)].copy()
    edges = list(range(25, 75, 5)) + [75.000001]
    labels = [f"{i}-{i + 4}%" for i in range(25, 70, 5)] + ["70-75%"]
    data["bin"] = pd.cut(data.Possession, edges, labels=labels, right=False)
    panels = [(single, single)] if single else list((k, k) for k in FILES) + [(None, "Combined exploratory snapshot")]
    fig, axes = plt.subplots(1, 1, figsize=(9, 6)) if single else plt.subplots(2, 3, figsize=(16, 9))
    axes = [axes] if single else list(axes.flatten())
    maximum = 0
    for ax, (league, title) in zip(axes, panels):
        subset = data if league is None else data[data.league == league]
        if subset.empty:
            ax.set_title(f"{title}: no data")
            continue
        groups = ["Home", "Away"] if home_away else [None]
        for index, venue in enumerate(groups):
            d = subset if venue is None else subset[subset.Location == venue]
            stats = d.groupby("bin", observed=False).Goals.agg(["mean", "count"]).reindex(labels)
            positions = list(range(len(labels)))
            offset = (-0.18 if index == 0 else 0.18) if home_away else 0
            ax.barh([p + offset for p in positions], stats['mean'], height=0.32 if home_away else 0.6,
                    label=venue, color=("#246b84" if index == 0 else "#d8875e"))
            maximum = max(maximum, stats['mean'].max())
        ax.set_yticks(range(len(labels)), labels)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel("Goals / team observation")
        if home_away:
            ax.legend()
    for ax in axes:
        ax.set_xlim(0, maximum * 1.2)
    fig.suptitle("Earlier possession/goals exploration | unverified fixture scope", fontweight="bold")
    fig.text(0.5, 0.015, "No match IDs or dates in these inputs. Bundesliga/Ligue 1 snapshots may include play-offs; not used in the main xG analysis.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    out = ROOT / "results" / "legacy"
    out.mkdir(parents=True, exist_ok=True)
    name = "home_away.png" if home_away else "ligue_1.png" if single else "possession_goals.png"
    fig.savefig(out / name, dpi=140)
    plt.close(fig)
    print(f"Saved {out / name}")
