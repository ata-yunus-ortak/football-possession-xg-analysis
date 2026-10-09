"""Compact case-study figures derived from the published aggregate tables."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis_core import BIN_LABELS, STATES


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#cbd5e1")
    ax.grid(axis="x", color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#334155", labelsize=10)


def generate(possession, states, output_dir, subtitle="2025-26 snapshot"):
    """Use existing estimates; do not resample or recalculate the case study."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": "DejaVu Sans", "text.color": "#0f172a"}):
        fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
        for ax, metric, title, xlabel in (
            (axes[0], "volume", "Chance volume", "Mean fixture-summary xG per team-match"),
            (axes[1], "shot_quality", "Shot quality", "Fixture-summary xG / FBref shots"),
        ):
            table = possession.loc[(possession.league == "Combined") & (possession.metric == metric)]
            table = table.set_index("Possession_Bin").reindex(BIN_LABELS)
            y = np.arange(len(table))
            ax.hlines(y, table.ci_low, table.ci_high, color="#0e7490", linewidth=2)
            ax.scatter(table.value, y, s=42, color="#0e7490", zorder=3)
            ax.set_title(title, loc="left", fontsize=15, fontweight="bold", pad=14)
            ax.set_xlabel(xlabel, fontsize=11, labelpad=10)
            ax.set_yticks(y, BIN_LABELS)
            ax.set_xlim(left=0)
            _style(ax)
        axes[0].invert_yaxis()
        axes[0].set_ylabel("Possession", fontsize=11)
        fig.suptitle(f"Possession, chance volume and shot quality | {subtitle}",
                     fontsize=17, fontweight="bold", y=0.98)
        fig.text(0.5, 0.025,
                 "Combined available leagues | 95% within-bin match-cluster bootstrap intervals\n"
                 "Understat xG + FBref shot counts; paired-complete rows for shot quality. Descriptive, unadjusted estimates.",
                 ha="center", fontsize=9, color="#475569")
        fig.tight_layout(rect=(0, 0.085, 1, 0.92))
        fig.savefig(output_dir / "overview_possession.png", dpi=160, facecolor="white")
        plt.close(fig)

        combined = states.loc[states.league == "Combined"].set_index("durum").reindex(STATES)
        fig, ax = plt.subplots(figsize=(10, 4.6))
        y = np.arange(len(combined))
        ax.barh(y, combined.xg_per_shot, height=0.58, color="#0e7490")
        ax.set_yticks(y, combined.label)
        ax.invert_yaxis()
        ax.set_xlim(0, max(0.01, combined.xg_per_shot.max() * 1.48))
        ax.set_xlabel("Summed shot-level xG / attacking shots", fontsize=11, labelpad=10)
        ax.set_title(f"Exploratory shot quality by score state | {subtitle}",
                     loc="left", fontsize=16, fontweight="bold", pad=18)
        _style(ax)
        for i, row in enumerate(combined.itertuples()):
            if pd.notna(row.xg_per_shot):
                ax.text(row.xg_per_shot + ax.get_xlim()[1] * 0.025, i,
                        f"{row.xg_per_shot:.4f}  ({int(row.toplam_sut):,} shots)",
                        va="center", fontsize=10, color="#334155")
        fig.text(0.5, 0.025,
                 "Minute-based pre-shot labels; true chronology is ambiguous at ties and around halftime. Own goals excluded.\n"
                 "Pooled, unadjusted comparison; final-score agreement does not verify each event's score state.",
                 ha="center", fontsize=9, color="#475569")
        fig.tight_layout(rect=(0, 0.115, 1, 1))
        fig.savefig(output_dir / "overview_score_state.png", dpi=160, facecolor="white")
        plt.close(fig)
