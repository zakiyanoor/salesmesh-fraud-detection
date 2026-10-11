"""
Learning curve (Step 9B), validation only.

Fits a configuration on TRAIN_FRACTIONS of the training agents (stratified by
pattern, REPEATS repeats each, repeat r uses seed r for both the subsample and
the model) and scores all validation agents. Test labels are never loaded.

Usage: python learning_curve.py [--selection-run DIR] [--model M --features F --params JSON] [--label NAME]
Default configuration: the chosen one in the latest selection run (operating_point.json).
Output: ml/runs/<run_id>/ with learning_curve.csv, learning_curve_summary.csv, learning_curve.png
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402

from data_generation import DEFAULT_OUT_DIR  # noqa: E402
from detectors import FITTERS  # noqa: E402
from labels_guard import load_labelled  # noqa: E402
from run_utils import RUNS_DIR  # noqa: E402
from split import strata  # noqa: E402
from train_models import FEATURE_SETS  # noqa: E402

TRAIN_FRACTIONS = [0.10, 0.25, 0.50, 0.75, 1.00]
REPEATS = [1, 2, 3, 4, 5]
INK, INK_MUTED, GRID, SURFACE, SERIES = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6"


def subsample(train, fraction, seed):
    if fraction >= 1.0:
        return train
    keep, _ = train_test_split(train, train_size=fraction, stratify=strata(train), random_state=seed)
    return keep


def learning_curve(train, val, model, columns, params):
    rows = []
    for fraction in TRAIN_FRACTIONS:
        for repeat in REPEATS:
            part = subsample(train, fraction, repeat)
            detector = FITTERS[model](part, columns, repeat, **params)
            scores = detector.score(val)
            rows.append({"fraction": fraction, "repeat": repeat, "train_agents": len(part),
                         "train_fraud": int(part["is_fraud"].sum()),
                         "pr_auc": average_precision_score(val["is_fraud"], scores),
                         "roc_auc": roc_auc_score(val["is_fraud"], scores)})
    return pd.DataFrame(rows)


def plot(summary, random_pr, title, path):
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
                         "axes.grid": True, "grid.color": GRID, "axes.spines.top": False, "axes.spines.right": False,
                         "xtick.color": INK_MUTED, "ytick.color": INK_MUTED, "font.size": 9})
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    x = summary["train_agents_mean"]
    for ax, metric, label in [(axes[0], "pr_auc", "Validation PR AUC"), (axes[1], "roc_auc", "Validation ROC AUC")]:
        ax.fill_between(x, summary[f"{metric}_min"], summary[f"{metric}_max"], color=SERIES, alpha=0.18, linewidth=0)
        ax.plot(x, summary[f"{metric}_mean"], color=SERIES, linewidth=2, marker="o", markersize=5)
        if metric == "pr_auc":
            ax.axhline(random_pr, color=INK_MUTED, linewidth=1, linestyle="--")
            ax.text(x.iloc[-1], random_pr + 0.01, f"random {random_pr:.3f}", ha="right", color=INK_MUTED, fontsize=8)
        ax.set_xlabel("Training agents used (10%, 25%, 50%, 75%, 100%)")
        ax.set_ylabel(label)
        ax.set_title(f"{label}: mean, band = min-max of 5 repeats", color=INK, fontsize=9)
    fig.suptitle(title, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def latest_selection_run():
    return sorted(RUNS_DIR.glob("*_selection_s*"))[-1]


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Step 9B learning curve on validation.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--selection-run", type=Path, default=None)
    parser.add_argument("--model")
    parser.add_argument("--features")
    parser.add_argument("--params")
    parser.add_argument("--label", default="chosen by the Step 9 rule")
    args = parser.parse_args(argv)

    if args.model:
        model, feature_set, params = args.model, args.features, json.loads(args.params)
    else:
        config = json.loads(((args.selection_run or latest_selection_run()) / "operating_point.json").read_text())
        model, params = config["model"], config["params"]
        feature_set = f"{len(config['feature_columns'])} features"
    columns = FEATURE_SETS[feature_set]

    parts = load_labelled(args.data_dir, ["train", "validation"])
    train, val = parts["train"], parts["validation"]
    inputs = [args.data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv"]]
    run_dir = start_run("learning_curve", None, {"model": model, "features": feature_set, "params": params,
                                                 "label": args.label, "fractions": TRAIN_FRACTIONS,
                                                 "repeats": REPEATS, "evaluated_on": "validation"}, inputs)
    table = learning_curve(train, val, model, columns, params)
    table.to_csv(run_dir / "learning_curve.csv", index=False)
    summary = table.groupby("fraction").agg(
        train_agents_mean=("train_agents", "mean"), train_fraud_mean=("train_fraud", "mean"),
        pr_auc_mean=("pr_auc", "mean"), pr_auc_std=("pr_auc", "std"), pr_auc_min=("pr_auc", "min"), pr_auc_max=("pr_auc", "max"),
        roc_auc_mean=("roc_auc", "mean"), roc_auc_std=("roc_auc", "std"), roc_auc_min=("roc_auc", "min"), roc_auc_max=("roc_auc", "max"),
    ).reset_index()
    summary.to_csv(run_dir / "learning_curve_summary.csv", index=False)
    title = f"Learning curve: {model}, {feature_set}, {params} ({args.label})"
    plot(summary, float(val["is_fraud"].mean()), title, run_dir / "learning_curve.png")
    print(title)
    print(summary.round(3).to_string(index=False))
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
