"""
Step 11: the final test, run ONCE.

main() refuses to run if results/test_read_once.json exists, then checks every
hash in results/FREEZE.md (and the labels.csv hash recorded at generation)
before any test label is read. Only then does it unlock the test labels
(labels_guard.unlock_test_labels, called here and nowhere else).

The frozen model (lof_v3_4f, scaler fitted on training only) scores the 150
test agents at the cutoff chosen on validation. Nothing is refitted and no
cutoff is chosen on test. Baselines use their frozen settings: random scores
(20 seeds, 15% budget), the volume rule (training P90), the best single feature
from Step 7 (collusion_score, +, 15% budget) and duplicate_activation_rule
(pairs > 0). The union of the model flag and the duplicate rule flag is a
pre-declared secondary analysis (results/selection_notes.md); the primary
result is the model alone. Bootstrap 95% CIs: 1000 agent-level resamples,
seed 42, resamples without both classes redrawn. For flag-only methods (the
union) PR AUC and ROC AUC are computed on the 0/1 flag.

Usage: python final_evaluation.py
Output: ml/runs/<run_id>/ (metrics, figures with captions, error analysis,
        ring candidates, subgroups, acceptance) and results/test_read_once.json
"""

import json
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve  # noqa: E402

from baselines import RANDOM_SEEDS, RULE_FEATURE, RULE_PERCENTILE, duplicate_activation_counts, feature_directions  # noqa: E402
from data_generation import COUNTY_TO_FORMER_PROVINCE  # noqa: E402
from explain import reasons  # noqa: E402
from metrics import ALERT_BUDGET, FRAUD_PATTERNS, budget_flags  # noqa: E402
from scoring import OUTPUT_COLUMNS, detector_from, score_agents  # noqa: E402

ML = Path(__file__).resolve().parent
MARKER = ML / "results" / "test_read_once.json"
ATTEMPT_LOG = ML / "results" / "test_read_attempts.log"
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 42
BEST_SINGLE_FEATURE = "collusion_score"
RING_MIN_SHARED_CUSTOMERS = 3
TIMING_REPEATS = 5
COST_RATIOS = [5, 2, 10]
METRIC_NAMES = ["pr_auc", "roc_auc", "precision", "recall", "f1", "flagged", "alert_rate"]
ROW = re.compile(r"^\| [^|]+ \| `([^`]+)` \| `([0-9a-f]{64})` \|$")

INK, INK_MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
CLASS_COLORS = {"honest": "#2a78d6", "fraud": "#eb6834"}
METHOD_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": INK_MUTED, "ytick.color": INK_MUTED,
    "axes.titlecolor": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
})


def refuse_if_already_run(marker=None):
    marker = Path(marker or MARKER)
    if marker.exists():
        raise SystemExit(f"The test set has already been read once ({marker}). Step 11 does not run again.")


def verify_freeze(freeze_path=ML / "results" / "FREEZE.md", ml_dir=ML):
    """[(path, expected, actual)] for every hashed file; labels.csv is checked against the generation run."""
    from freeze import DATA_RUN
    from run_utils import file_sha256

    rows = [m.groups() for line in Path(freeze_path).read_text(encoding="utf-8").splitlines() if (m := ROW.match(line))]
    generated = json.loads((ml_dir / "runs" / DATA_RUN / "run_info.json").read_text())["data_files"]
    rows.append(("data/synthetic/labels.csv", generated["labels.csv"]))
    return [(path, digest, file_sha256(ml_dir / path) if (ml_dir / path).exists() else "missing") for path, digest in rows]


def point_metrics(y, scores, flags):
    y, flags = np.asarray(y, dtype=bool), np.asarray(flags, dtype=bool)
    tp, fp = int((flags & y).sum()), int((flags & ~y).sum())
    fn, tn = int((~flags & y).sum()), int((~flags & ~y).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"pr_auc": average_precision_score(y, scores), "roc_auc": roc_auc_score(y, scores),
            "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "flagged": int(flags.sum()), "alert_rate": float(flags.mean()), "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def method_metrics(y, method, idx=None):
    """method: (scores, flags) or a list of them (averaged, for the random baseline)."""
    runs = method if isinstance(method, list) else [method]
    take = (lambda a: np.asarray(a)[idx]) if idx is not None else np.asarray
    results = [point_metrics(take(y), take(s), take(f)) for s, f in runs]
    return {k: float(np.mean([r[k] for r in results])) for k in results[0]}


def bootstrap_indices(y, resamples=None, seed=BOOTSTRAP_SEED):
    resamples = resamples or BOOTSTRAP_RESAMPLES
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=bool)
    out = []
    while len(out) < resamples:
        idx = rng.integers(0, len(y), len(y))
        if 0 < y[idx].sum() < len(idx):
            out.append(idx)
    return out


def metrics_with_ci(y, methods, indices):
    rows = []
    for name, method in methods.items():
        point = method_metrics(y, method)
        boot = pd.DataFrame([method_metrics(y, method, idx) for idx in indices])
        row = {"method": name, **point}
        for m in METRIC_NAMES:
            row[f"{m}_ci_low"], row[f"{m}_ci_high"] = np.percentile(boot[m], [2.5, 97.5])
        rows.append(row)
    return pd.DataFrame(rows)


def by_pattern(profiles, y, flags):
    profiles, y, flags = np.asarray(profiles), np.asarray(y, dtype=bool), np.asarray(flags, dtype=bool)
    row = {}
    for p in FRAUD_PATTERNS:
        mask = profiles == p
        row[f"recall_{p}"], row[f"agents_{p}"] = float(flags[mask].mean()) if mask.any() else float("nan"), int(mask.sum())
    row["honest_flag_rate"] = float(flags[~y].mean())
    return row


def build_methods(train, test, bundle, duplicate_counts):
    detector = detector_from(bundle)
    cutoff = float(bundle["operating_point"]["threshold"])
    model_scores = detector.score(test)
    cap = float(train[RULE_FEATURE].quantile(RULE_PERCENTILE))
    direction = feature_directions(train).loc[BEST_SINGLE_FEATURE, "direction"]
    single = direction * test[BEST_SINGLE_FEATURE].values
    dup = test["agent_id"].map(duplicate_counts).fillna(0).values.astype(float)
    model_flags, dup_flags = model_scores >= cutoff, dup > 0
    union = model_flags | dup_flags
    primary = {
        f"{bundle['model_version']} (cutoff {cutoff:.3f})": (model_scores, model_flags),
        f"random scores (mean of {len(RANDOM_SEEDS)} seeds, {ALERT_BUDGET:.0%} budget)": [
            (r, budget_flags(r)) for r in (np.random.default_rng(s).random(len(test)) for s in RANDOM_SEEDS)],
        f"rule: {RULE_FEATURE} > training P{int(RULE_PERCENTILE * 100)} ({cap:g})": (test[RULE_FEATURE].values, test[RULE_FEATURE].values > cap),
        f"best single feature: {BEST_SINGLE_FEATURE} (+, {ALERT_BUDGET:.0%} budget)": (single, budget_flags(single)),
        "duplicate_activation_rule (pairs > 0)": (dup, dup_flags),
    }
    secondary = {"SECONDARY: union of model flag and duplicate rule flag": (union.astype(float), union)}
    return primary, secondary, model_scores, cutoff


def single_feature_test_pr_auc(train, test, columns):
    directions = feature_directions(train)
    return {f: average_precision_score(test["is_fraud"], directions.loc[f, "direction"] * test[f].values) for f in columns}


def cost_sensitivity(y, model_scores, profiles, validation_points):
    rows = []
    for _, point in validation_points.iterrows():
        flags = model_scores >= point["cutoff"]
        m = point_metrics(y, model_scores, flags)
        row = {"rule (chosen on validation)": point["rule"], "cutoff": point["cutoff"], **{k: m[k] for k in
               ["flagged", "alert_rate", "precision", "recall", "f1", "tp", "fp", "fn", "tn"]}}
        for r in COST_RATIOS:
            row[f"cost_per_agent_{r}to1"] = (r * m["fn"] + m["fp"]) / len(y)
        rows.append({**row, **by_pattern(profiles, y, flags)})
    return pd.DataFrame(rows)


def explain_row(row, cutoff, reference):
    unusual = [f for f in reference if abs(row[f] - reference[f]["median"]) / max(reference[f]["iqr"], 1e-3) >= 1]
    where = f"score {row['score']:.3f} {'>=' if row['flag'] else '<'} cutoff {cutoff:.3f}"
    return f"{where}; features at least 1 IQR from typical: {', '.join(unusual) if unusual else 'none'}"


def error_analysis(test, output, bundle, cutoff):
    columns = list(bundle["feature_columns"])
    df = test.merge(output[["agent_id", "score", "flag", "reason"]], on="agent_id")
    errors = df[(df["is_fraud"] & ~df["flag"]) | (~df["is_fraud"] & df["flag"])].copy()
    errors["error"] = np.where(errors["is_fraud"], "missed fraud", "false alarm")
    if len(errors):
        missed = errors["error"] == "missed fraud"
        if missed.any():
            errors.loc[missed, "reason"] = reasons(bundle["reference_stats"], columns, errors[missed])
        errors["explanation"] = [explain_row(r, cutoff, bundle["reference_stats"]) for _, r in errors.iterrows()]
    keep = ["error", "agent_id", "profile", "ring_id", *columns, "score", "reason", "explanation"]
    return errors.reindex(columns=keep).sort_values(["error", "profile", "score"], ascending=[True, True, False])


def ring_candidates(all_features, activations, bundle, min_shared=RING_MIN_SHARED_CUSTOMERS):
    """Flag every agent with the frozen model, then join flagged agents sharing >= min_shared customers."""
    scores = detector_from(bundle).score(all_features)
    flagged = set(all_features.loc[scores >= float(bundle["operating_point"]["threshold"]), "agent_id"])
    customers = activations[activations["agent_id"].isin(flagged)].groupby("agent_id")["customer_id"].agg(set)
    agents = sorted(customers.index)
    parent = {a: a for a in agents}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, a in enumerate(agents):
        for b in agents[i + 1:]:
            if len(customers[a] & customers[b]) >= min_shared:
                parent[find(a)] = find(b)
    groups = pd.Series({a: find(a) for a in agents})
    sizes = groups.value_counts()
    groups = groups[groups.map(sizes) >= 2]
    ids = {root: f"cand_{i + 1:02d}" for i, root in enumerate(sorted(groups.unique()))}
    table = pd.DataFrame({"candidate_id": groups.map(ids), "agent_id": groups.index})
    table["candidate_size"] = table["candidate_id"].map(table["candidate_id"].value_counts())
    return table.sort_values(["candidate_id", "agent_id"]).reset_index(drop=True), flagged


def ring_comparison(candidates, flagged, labels, split):
    """After scoring: true rings against flagged members and candidates."""
    rings = labels[labels["ring_id"] != ""].merge(split, on="agent_id")
    rings["flagged"] = rings["agent_id"].isin(flagged)
    rings = rings.merge(candidates[["agent_id", "candidate_id"]], on="agent_id", how="left")
    summary = rings.groupby("ring_id").agg(
        pattern=("profile", "first"), members=("agent_id", "size"), flagged_members=("flagged", "sum"),
        test_members=("split", lambda s: int((s == "test").sum())),
        test_flagged=("flagged", lambda f: int(f[rings.loc[f.index, "split"] == "test"].sum())),
        candidates=("candidate_id", lambda c: ";".join(sorted(set(c.dropna())))),
    ).reset_index()
    summary["at_least_one_flagged"] = summary["flagged_members"] >= 1
    summary["at_least_half_flagged"] = summary["flagged_members"] >= summary["members"] / 2
    purity = candidates.merge(labels[["agent_id", "ring_id", "is_fraud"]], on="agent_id").groupby("candidate_id").agg(
        size=("agent_id", "size"), true_rings=("ring_id", lambda r: ";".join(sorted(set(r) - {""}))),
        non_ring_members=("ring_id", lambda r: int((r == "").sum())), honest_members=("is_fraud", lambda f: int((~f).sum())))
    return summary, purity.reset_index()


def subgroups(test, flags, column):
    df = test.assign(flag=flags)
    return df.groupby(column).apply(lambda g: pd.Series({
        "agents": len(g), "fraud": int(g["is_fraud"].sum()), "flagged": int(g["flag"].sum()),
        "true_positives": int((g["flag"] & g["is_fraud"]).sum()), "false_alarms": int((g["flag"] & ~g["is_fraud"]).sum()),
        "recall": (g["flag"] & g["is_fraud"]).sum() / g["is_fraud"].sum() if g["is_fraud"].any() else float("nan")}),
        include_groups=False).reset_index()


def median_seconds(fn, repeats=TIMING_REPEATS):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def save_figure(fig, path, caption):
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    Path(path).with_suffix(".caption.txt").write_text(caption + "\n", encoding="utf-8")


def figures(run_dir, y, primary, pattern_table, model_name, cutoff, model_scores, confusion, n_fraud):
    curves = [(name, method) for name, method in primary.items() if not isinstance(method, list)]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for color, (name, (scores, _)) in zip(METHOD_COLORS, [curves[0], curves[3], curves[1], curves[2]]):
        precision, recall, _ = precision_recall_curve(y, scores)
        ax.step(recall, precision, where="post", color=color, linewidth=2,
                label=f"{name.split(' (')[0]} (PR AUC {average_precision_score(y, scores):.3f})")
    ax.axhline(np.mean(y), color=INK_MUTED, linestyle="--", linewidth=1, label=f"random (fraud rate {np.mean(y):.3f})")
    ax.set(xlabel="Recall (share of fraud agents flagged)", ylabel="Precision (share of flags that are fraud)",
           xlim=(0, 1.02), ylim=(0, 1.05), title="Precision-recall curve on the test set")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    save_figure(fig, run_dir / "fig11_precision_recall.png",
                f"Figure: precision-recall curves on the 150 test agents ({n_fraud} fraud) for the frozen model "
                f"{model_name} and the frozen baselines. The dashed line is a random score. Higher and further right is better.")

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for color, (name, (scores, _)) in zip(METHOD_COLORS, [curves[0], curves[3], curves[1], curves[2]]):
        fpr, tpr, _ = roc_curve(y, scores)
        ax.plot(fpr, tpr, color=color, linewidth=2, label=f"{name.split(' (')[0]} (ROC AUC {roc_auc_score(y, scores):.3f})")
    ax.plot([0, 1], [0, 1], color=INK_MUTED, linestyle="--", linewidth=1, label="random (0.5)")
    ax.set(xlabel="False positive rate (share of honest agents flagged)", ylabel="True positive rate (recall)",
           title="ROC curve on the test set")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    save_figure(fig, run_dir / "fig12_roc.png",
                f"Figure: ROC curves on the 150 test agents for {model_name} and the frozen baselines. The dashed diagonal is a random score.")

    fig, ax = plt.subplots(figsize=(6.5, 4))
    bins = np.linspace(min(model_scores.min(), cutoff) * 0.95, model_scores.max() * 1.02, 30)
    ax.hist([model_scores[~y], model_scores[y]], bins=bins, stacked=True, color=[CLASS_COLORS["honest"], CLASS_COLORS["fraud"]],
            edgecolor=SURFACE, linewidth=1, label=[f"honest ({int((~y).sum())})", f"fraud ({int(y.sum())})"])
    ax.axvline(cutoff, color=INK, linewidth=1.5, linestyle="--")
    ax.text(cutoff, ax.get_ylim()[1] * 0.95, f"  cutoff {cutoff:.3f}", color=INK, fontsize=8, va="top")
    ax.set(xlabel=f"{model_name} anomaly score (higher = more anomalous)", ylabel="Test agents",
           title="Score distribution on the test set")
    ax.legend(frameon=False)
    save_figure(fig, run_dir / "fig13_score_distribution.png",
                f"Figure: anomaly scores of the 150 test agents by true class. Bars are stacked (honest below, fraud above). Agents at or right of the dashed line "
                f"(cutoff {cutoff:.3f}, chosen on validation) are flagged.")

    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    matrix = np.array([[confusion["tn"], confusion["fp"]], [confusion["fn"], confusion["tp"]]])
    ax.imshow(matrix, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("blues", [SURFACE, "#2a78d6"]))
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=14,
                    color=SURFACE if matrix[i, j] > matrix.max() / 2 else INK)
    ax.set_xticks([0, 1], ["not flagged", "flagged"])
    ax.set_yticks([0, 1], ["honest", "fraud"])
    ax.set(xlabel="Model decision", ylabel="True class", title="Confusion matrix (test)")
    ax.grid(False)
    save_figure(fig, run_dir / "fig14_confusion_matrix.png",
                f"Figure: confusion matrix of {model_name} at cutoff {cutoff:.3f} on the 150 test agents.")

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    width = 0.38
    x = np.arange(len(FRAUD_PATTERNS))
    for k, (label, color) in enumerate([(model_name, METHOD_COLORS[0]), ("SECONDARY: union with duplicate rule", METHOD_COLORS[1])]):
        values = [pattern_table.loc[label, f"recall_{p}"] for p in FRAUD_PATTERNS]
        bars = ax.bar(x + (k - 0.5) * width, values, width=width - 0.04, color=color, label=label)
        for bar, v in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=7, color=INK)
    counts = [int(pattern_table.loc[model_name, f"agents_{p}"]) for p in FRAUD_PATTERNS]
    ax.set_xticks(x, [f"{p}\n({n} agents)" for p, n in zip(FRAUD_PATTERNS, counts)])
    ax.set(ylabel="Recall (share of the pattern's agents flagged)", ylim=(0, 1.32), title="Recall by fraud pattern on the test set")
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.legend(frameon=False, fontsize=7, loc="upper center", ncol=2)
    save_figure(fig, run_dir / "fig15_recall_by_pattern.png",
                f"Figure: recall by fraud pattern on the test set for {model_name} (primary result) and, as a pre-declared secondary "
                "analysis, the union with duplicate_activation_rule. Each pattern has 3 to 6 test agents, so each bar is very uncertain.")


def evaluate_test(parts, all_features, activations, agents, bundle, validation_points, run_dir, frozen_checks=None):
    """Everything after the test labels are loaded. Returns a summary dict."""
    run_dir = Path(run_dir)
    train, val, test = parts["train"], parts["validation"], parts["test"]
    y, profiles = test["is_fraud"].values.astype(bool), test["profile"].values
    duplicate_counts = duplicate_activation_counts(activations)
    primary, secondary, model_scores, cutoff = build_methods(train, test, bundle, duplicate_counts)
    model_name = bundle["model_version"]
    indices = bootstrap_indices(y)

    metrics = metrics_with_ci(y, {**primary, **secondary}, indices)
    metrics["role"] = ["primary"] + ["baseline"] * (len(primary) - 1) + ["secondary (pre-declared)"] * len(secondary)
    metrics.to_csv(run_dir / "test_metrics.csv", index=False)

    flags_by_method = {name: (m[1] if not isinstance(m, list) else None) for name, m in {**primary, **secondary}.items()}
    pattern_rows = [{"method": name, **by_pattern(profiles, y, f)} for name, f in flags_by_method.items() if f is not None]
    pattern_table = pd.DataFrame(pattern_rows).set_index("method")
    pattern_table = pattern_table.rename(index={list(primary)[0]: model_name,
                                                list(secondary)[0]: "SECONDARY: union with duplicate rule"})
    pattern_table.to_csv(run_dir / "recall_by_pattern.csv")

    model_flags = primary[list(primary)[0]][1]
    confusion = point_metrics(y, model_scores, model_flags)
    pd.DataFrame([[confusion["tn"], confusion["fp"]], [confusion["fn"], confusion["tp"]]],
                 index=["true honest", "true fraud"], columns=["not flagged", "flagged"]).to_csv(run_dir / "confusion_matrix.csv")
    costs = cost_sensitivity(y, model_scores, profiles, validation_points)
    costs.to_csv(run_dir / "cost_sensitivity.csv", index=False)

    output = score_agents(bundle, test)
    output.to_csv(run_dir / "test_scores.csv", index=False)
    errors = error_analysis(test, output, bundle, cutoff)
    errors.to_csv(run_dir / "error_analysis.csv", index=False)

    candidates, flagged_all = ring_candidates(all_features, activations, bundle)
    candidates.to_csv(run_dir / "ring_candidates.csv", index=False)
    labels_all = pd.concat([p[["agent_id", "is_fraud", "profile", "ring_id"]] for p in parts.values()])
    split = pd.concat([p[["agent_id"]].assign(split=name) for name, p in parts.items()])
    rings, purity = ring_comparison(candidates, flagged_all, labels_all, split)
    rings.to_csv(run_dir / "ring_comparison.csv", index=False)
    purity.to_csv(run_dir / "ring_candidate_purity.csv", index=False)

    test_regions = test.merge(agents[["agent_id", "region"]], on="agent_id")
    test_regions["former_region"] = test_regions["region"].map(COUNTY_TO_FORMER_PROVINCE)
    by_region = subgroups(test_regions, model_flags, "former_region")
    by_profile = subgroups(test, model_flags, "profile")
    by_region.to_csv(run_dir / "subgroups_former_region.csv", index=False)
    by_profile.to_csv(run_dir / "subgroups_pattern.csv", index=False)

    detector = detector_from(bundle)
    timing = {
        "test_agents": len(test),
        "score_ms_per_agent": 1000 * median_seconds(lambda: detector.score(test)) / len(test),
        "score_and_explain_ms_per_agent": 1000 * median_seconds(lambda: score_agents(bundle, test)) / len(test),
        "all_agents": len(all_features),
        "score_all_agents_seconds": median_seconds(lambda: detector.score(all_features)),
    }
    timing["score_all_agents_ms_per_agent"] = 1000 * timing["score_all_agents_seconds"] / len(all_features)
    (run_dir / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")

    single_test = single_feature_test_pr_auc(train, test, list(feature_directions(train).index))
    model_row = metrics.iloc[0]
    fraud_rate = float(y.mean())
    frozen_checks = frozen_checks or {}
    best_single_test = max(single_test.values())
    schema_ok = all(c in output.columns for c in OUTPUT_COLUMNS) and not output[OUTPUT_COLUMNS].isna().any().any() \
        and not (output[OUTPUT_COLUMNS].astype(str).apply(lambda s: s.str.strip() == "")).any().any()
    acceptance = [
        ("Q1", "validation", "mean validation PR AUC (seeds 1-5) > best single-feature validation PR AUC",
         frozen_checks.get("Q1_value"), frozen_checks.get("Q1_pass")),
        ("Q2", "test", f"test PR AUC > best single-feature test PR AUC (max over the 5 features, training directions: {best_single_test:.3f}; "
         f"{BEST_SINGLE_FEATURE} alone {single_test[BEST_SINGLE_FEATURE]:.3f})", model_row["pr_auc"], model_row["pr_auc"] > best_single_test),
        ("Q3", "test", f"test PR AUC >= 3 x test fraud rate ({3 * fraud_rate:.3f}) and CI low > fraud rate ({fraud_rate:.3f})",
         f"{model_row['pr_auc']:.3f} (CI {model_row['pr_auc_ci_low']:.3f} to {model_row['pr_auc_ci_high']:.3f})",
         model_row["pr_auc"] >= 3 * fraud_rate and model_row["pr_auc_ci_low"] > fraud_rate),
        ("Q4", "validation", "train ROC AUC - validation ROC AUC <= 0.10", frozen_checks.get("Q4_value"), frozen_checks.get("Q4_pass")),
        ("Q5", "test", "test recall at the cutoff >= 0.60", model_row["recall"], model_row["recall"] >= 0.60),
        ("Q6", "test", "test alert rate at the cutoff <= 25%", model_row["alert_rate"], model_row["alert_rate"] <= 0.25),
        ("S1", "test timing", "scoring <= 10 ms per agent and <= 5 s for the 1000-agent table",
         f"{timing['score_ms_per_agent']:.3f} ms per test agent; all {len(all_features)} agents in {timing['score_all_agents_seconds']:.3f} s",
         timing["score_ms_per_agent"] <= 10 and timing["score_all_agents_seconds"] <= 5),
        ("S2", "frozen system checks", "model replaceable; threshold read from the bundle", frozen_checks.get("S2_value"), frozen_checks.get("S2_pass")),
        ("S3", "test output", "every test output row has all 9 fields, non-empty", f"{len(output)} rows", schema_ok),
        ("S4", "frozen system checks", "scoring 10000 agents <= 60 s; features + scoring <= 600 s", frozen_checks.get("S4_value"), frozen_checks.get("S4_pass")),
    ]
    acceptance = pd.DataFrame([{"criterion": c, "measured_on": on, "condition": cond, "value": v,
                                "result": "PASS" if ok else ("FAIL" if ok is not None else "NOT AVAILABLE")}
                               for c, on, cond, v, ok in acceptance])
    acceptance.to_csv(run_dir / "acceptance_test.csv", index=False)
    pd.Series(single_test, name="test_pr_auc").to_csv(run_dir / "single_feature_test_pr_auc.csv")

    figures(run_dir, y, primary, pattern_table, model_name, cutoff, model_scores, confusion, int(y.sum()))
    train_gap = roc_auc_score(train["is_fraud"], detector.training_scores(train)) - model_row["roc_auc"]
    summary = {"model_version": model_name, "cutoff": cutoff, "test_agents": len(test), "test_fraud": int(y.sum()),
               "fraud_rate": fraud_rate, "train_minus_test_roc_auc": float(train_gap),
               "rings_with_a_flagged_member": int(rings["at_least_one_flagged"].sum()),
               "rings_at_least_half_flagged": int(rings["at_least_half_flagged"].sum()), "rings": len(rings),
               "ring_candidates": int(candidates["candidate_id"].nunique()), "errors": len(errors),
               "acceptance": acceptance.set_index("criterion")["result"].to_dict()}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def frozen_check_values(selection_run, system_checks_run):
    val = pd.read_csv(ML / "runs" / selection_run / "acceptance_validation.csv").set_index("criterion")
    checks = json.loads((ML / "runs" / system_checks_run / "system_checks.json").read_text())
    scaling = pd.read_csv(ML / "runs" / system_checks_run / "scaling.csv").iloc[-1]
    return {"Q1_value": val.loc["Q1", "value"], "Q1_pass": val.loc["Q1", "result"] == "PASS",
            "Q4_value": val.loc["Q4", "value"], "Q4_pass": val.loc["Q4", "result"] == "PASS",
            "S2_value": f"swap to {checks['S2']['swapped_model_version']}, threshold {checks['S2']['threshold_from_bundle']} from the bundle",
            "S2_pass": bool(checks["S2"]["pass"]),
            "S4_value": f"10000 agents: scoring {scaling['scoring_seconds']:.3f} s, end to end {scaling['end_to_end_seconds']:.1f} s",
            "S4_pass": bool(checks["S4"]["pass"])}


def main():
    import labels_guard
    from freeze import EXPLAIN_RUN, SELECTION_RUN, SYSTEM_CHECKS_RUN
    from run_utils import start_run

    refuse_if_already_run()
    hashes = verify_freeze()
    mismatched = [(p, e, a) for p, e, a in hashes if e != a]
    for path, expected, actual in hashes:
        print(f"{'OK      ' if expected == actual else 'MISMATCH'} {path}")
    if mismatched:
        raise SystemExit(f"STOP: {len(mismatched)} hash(es) differ from FREEZE.md; no test label was read.")

    data_dir = ML / "data" / "synthetic"
    bundle_path = ML / "runs" / EXPLAIN_RUN / "scoring_bundle.joblib"
    run_dir = start_run("final_evaluation", BOOTSTRAP_SEED, {
        "model_bundle": str(bundle_path), "selection_run": SELECTION_RUN, "explain_run": EXPLAIN_RUN,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES, "bootstrap_seed": BOOTSTRAP_SEED,
        "best_single_feature": BEST_SINGLE_FEATURE, "ring_min_shared_customers": RING_MIN_SHARED_CUSTOMERS,
        "secondary_analysis": "union of model and duplicate rule flags (pre-declared)"},
        [data_dir / f for f in ["feature_vectors.csv", "split.csv", "labels.csv", "activation_records_clean.csv", "agents.csv"]]
        + [bundle_path])
    with open(ATTEMPT_LOG, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat(timespec='seconds')} unlocking test labels for run {run_dir.name}\n")

    labels_guard.unlock_test_labels()
    parts = labels_guard.load_labelled(data_dir, ["train", "validation", "test"])
    bundle = joblib.load(bundle_path)
    summary = evaluate_test(
        parts, pd.read_csv(data_dir / "feature_vectors.csv"), pd.read_csv(data_dir / "activation_records_clean.csv"),
        pd.read_csv(data_dir / "agents.csv"), bundle,
        pd.read_csv(ML / "runs" / SELECTION_RUN / "operating_points.csv"), run_dir,
        frozen_check_values(SELECTION_RUN, SYSTEM_CHECKS_RUN))

    MARKER.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(timespec="seconds"), "run_id": run_dir.name,
        "hashes": {path: actual for path, _, actual in hashes}, "summary": summary}, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    print(f"Run folder {run_dir}\nTest labels were read once; {MARKER} now blocks a second run.")


if __name__ == "__main__":
    main()
