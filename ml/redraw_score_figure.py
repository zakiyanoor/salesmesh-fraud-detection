"""
Presentation only: redraws the Step 11 score distribution from the saved run
files, with the x axis clipped and an overflow bin. Nothing is recomputed and
labels.csv is not read: each test agent's class comes from the saved outputs
(fraud = flagged and not a false alarm, or a missed fraud agent, both listed in
error_analysis.csv). Writes fig13b_score_distribution_clipped.png and its
caption next to the original, which is kept.

Usage: python redraw_score_figure.py [--run DIR]
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from final_evaluation import CLASS_COLORS, INK, SURFACE, save_figure  # noqa: E402

ML = Path(__file__).resolve().parent
X_MAX = 5.0


def classes_from_saved_files(run_dir):
    scores = pd.read_csv(run_dir / "test_scores.csv")
    errors = pd.read_csv(run_dir / "error_analysis.csv")
    false_alarms = set(errors.loc[errors["error"] == "false alarm", "agent_id"])
    missed = set(errors.loc[errors["error"] == "missed fraud", "agent_id"])
    fraud = (scores["flag"] & ~scores["agent_id"].isin(false_alarms)) | scores["agent_id"].isin(missed)
    return scores.assign(fraud=fraud)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Redraw the Step 11 score distribution (presentation only).")
    parser.add_argument("--run", type=Path, default=None)
    args = parser.parse_args(argv)
    run_dir = args.run or ML / "runs" / json.loads((ML / "results" / "test_read_once.json").read_text())["run_id"]

    table = classes_from_saved_files(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    cutoff, model = summary["cutoff"], summary["model_version"]
    if int(table["fraud"].sum()) != summary["test_fraud"]:
        raise SystemExit("saved files do not give the recorded number of fraud agents")
    over = table[table["score"] > X_MAX]
    clipped = table["score"].clip(upper=X_MAX + 0.15)
    bins = np.append(np.round(np.arange(9, 10 * X_MAX + 1) / 10, 1), X_MAX + 0.3)
    honest, fraud = clipped[~table["fraud"]], clipped[table["fraud"]]

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.set_axisbelow(True)
    ax.hist([honest, fraud], bins=bins, stacked=True, color=[CLASS_COLORS["honest"], CLASS_COLORS["fraud"]],
            edgecolor=SURFACE, linewidth=0.8, label=[f"honest ({len(honest)})", f"fraud ({len(fraud)})"])
    ax.axvline(cutoff, color=INK, linewidth=1.5, linestyle="--")
    ax.text(cutoff, ax.get_ylim()[1] * 0.95, f"  cutoff {cutoff:.3f}", color=INK, fontsize=8, va="top")
    ax.set_xticks([1, 2, 3, 4, X_MAX + 0.15], ["1", "2", "3", "4", f">{X_MAX:g}"])
    ax.set(xlim=(0.85, X_MAX + 0.35), xlabel=f"{model} anomaly score (higher = more anomalous)",
           ylabel="Test agents", title="Score distribution on the test set (axis clipped at 5)")
    note = (f"{len(over)} {'fraud ' if over['fraud'].all() else ''}agents score "
            f"{over['score'].min():.1f} to {over['score'].max():.1f}; shown in the >{X_MAX:g} bin")
    ax.text(0.98, 0.70, note, transform=ax.transAxes, ha="right", fontsize=8, color=INK)
    ax.legend(frameon=False)
    save_figure(fig, run_dir / "fig13b_score_distribution_clipped.png",
                f"Figure: anomaly scores of the 150 test agents by true class, stacked (honest below, fraud above), with the "
                f"score axis clipped at {X_MAX:g}. {note}. Agents at or right of the dashed line "
                f"(cutoff {cutoff:.3f}, chosen on validation) are flagged. Presentation only: redrawn from the saved run files, "
                "nothing recomputed.")
    print(f"Saved {run_dir / 'fig13b_score_distribution_clipped.png'}; {note}")


if __name__ == "__main__":
    main()
