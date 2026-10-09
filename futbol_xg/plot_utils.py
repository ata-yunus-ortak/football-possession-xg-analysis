"""English plots with shared scales and descriptive uncertainty intervals."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from analysis_core import possession_dilimle

def panel_2x3_olustur(title):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle(title, fontsize=15, fontweight="bold")
    return fig, axes.flatten()

def paneli_kaydet(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(path, dpi=140)
    plt.close(fig)

def draw_points(ax, stats, title, xlabel):
    ax.set_title(title, fontsize=11, fontweight="bold")
    if stats.empty:
        ax.text(0.5, 0.5, "No data in this snapshot", ha="center", transform=ax.transAxes)
        ax.set_yticks([])
        return
    y = np.arange(len(stats))
    ax.scatter(stats.value, y, color="#246b84", s=28, zorder=3)
    valid = stats.ci_low.notna() & stats.ci_high.notna()
    ax.hlines(y[valid], stats.loc[valid, "ci_low"], stats.loc[valid, "ci_high"], color="#246b84", linewidth=1.5)
    ax.set_yticks(y, stats.Possession_Bin)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(axis="x", alpha=0.2)
    for i, row in enumerate(stats.itertuples()):
        ax.text(0.98, i, f"n={row.n}", transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8,
                bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"})

def draw_state_bars(ax, stats, title, xlabel):
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.barh(stats.label, stats.value, color=["#246b84", "#4a9b78", "#d8875e"])
    ax.invert_yaxis()
    ax.set_xlabel(xlabel, fontsize=9)
    ax.grid(axis="x", alpha=0.2)
    for i, row in enumerate(stats.itertuples()):
        ax.text(0.98, i, f"{row.value:.3f} | {int(row.n):,} shots", transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=8, bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none"})

def common_limits(axes, tables, signed=False):
    values = []
    for table in tables:
        for col in ("value", "ci_low", "ci_high"):
            if col in table:
                values.extend(table[col].dropna().tolist())
    maximum, minimum = max(values, default=1.0), min(values, default=0.0)
    lo = min(0.0, minimum * 1.2) if signed else 0.0
    hi = max(0.01, maximum * 1.2)
    for ax in axes:
        ax.set_xlim(lo, hi)
        if signed:
            ax.axvline(0, color="gray", linewidth=0.8)
