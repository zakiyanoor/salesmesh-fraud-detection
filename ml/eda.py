"""
Exploratory data analysis (Step 3) on the cleaned activation records.

Per-agent descriptors here are for understanding the data only; they are not
the model features (Step 4). Labels are read to describe the groups. EDA covers
all agents, including those that Step 5 will put in validation and test; no
later decision may be based on it unless documented.

Usage: python eda.py [--data-dir DIR] [--clean-run DIR]
Output: ml/runs/<run_id>/ with run_info.json, findings.md, raw_sample.md,
        descriptors_by_agent.csv, descriptors_by_group.csv, correlations.csv and fig*.png
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from data_checks import collusion_scores  # noqa: E402
from data_generation import DEFAULT_OUT_DIR  # noqa: E402
from run_utils import RUNS_DIR, start_run  # noqa: E402

SAMPLE_SEED = 0
SAMPLE_ROWS = 8
NIGHT_HOURS = range(0, 5)
GROUP_ORDER = ["legit", "legit_night", "legit_repeat", "legit_busy",
               "ring", "weak_ring", "sequential", "duplicate", "weak"]
CLASS_COLORS = {"legit": "#2a78d6", "fraud": "#eb6834"}
INK, INK_MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
DIVERGING = LinearSegmentedColormap.from_list("blue_gray_orange", ["#2a78d6", "#d9d8d4", "#eb6834"])
DESCRIPTORS = {
    "records": "Records in window",
    "max_records_one_day": "Max records in one day",
    "active_days": "Active days",
    "night_share": "Share of records 00:00-04:59",
    "hour_entropy": "Hour-of-day entropy (0-1)",
    "distinct_customer_ratio": "Distinct customers / records",
    "repeat_same_client_share": "Share repeating a customer+client",
    "shared_customer_share": "Share of customers shared with others",
    "near_duplicates": "Near-duplicate flags (cleaning)",
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": INK_MUTED, "ytick.color": INK_MUTED,
    "axes.titlecolor": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
})


def latest_clean_run():
    runs = sorted(RUNS_DIR.glob("*_clean"))
    return runs[-1] if runs else None


def hour_entropy(hours):
    p = hours.value_counts(normalize=True).values
    return float(-(p * np.log2(p)).sum() / np.log2(24))


def agent_descriptors(acts, flags):
    acts = acts.assign(timestamp=pd.to_datetime(acts["timestamp"]))
    hours = acts["timestamp"].dt.hour
    day = acts["timestamp"].dt.date
    g = acts.groupby("agent_id")
    table = pd.DataFrame({
        "records": g.size(),
        "max_records_one_day": acts.groupby(["agent_id", day]).size().groupby(level=0).max(),
        "active_days": g["timestamp"].apply(lambda t: t.dt.date.nunique()),
        "night_share": hours.isin(NIGHT_HOURS).groupby(acts["agent_id"]).mean(),
        "hour_entropy": hours.groupby(acts["agent_id"]).apply(hour_entropy),
        "distinct_customer_ratio": g["customer_id"].nunique() / g.size(),
        "repeat_same_client_share": acts.duplicated(["agent_id", "customer_id", "client_id"]).groupby(acts["agent_id"]).mean(),
        "shared_customer_share": collusion_scores(acts),
    })
    near = flags[flags["flag"].str.startswith("near_duplicate")].merge(acts[["record_id", "agent_id"]], on="record_id")
    table["near_duplicates"] = near.groupby("agent_id").size()
    return table.fillna({"near_duplicates": 0})


def md_table(df, index=True):
    df = df.reset_index() if index else df
    cells = [[str(v) for v in row] for row in df.astype(object).values]
    header = "| " + " | ".join(map(str, df.columns)) + " |"
    return "\n".join([header, "|" + "---|" * len(df.columns)] + ["| " + " | ".join(r) + " |" for r in cells])


def fig_class_balance(labels, path):
    counts = labels["profile"].value_counts().reindex(GROUP_ORDER)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    colors = [CLASS_COLORS["fraud" if p in labels.loc[labels["is_fraud"], "profile"].values else "legit"] for p in counts.index]
    ax.barh(counts.index[::-1], counts.values[::-1], color=colors[::-1], height=0.6)
    for y, v in enumerate(counts.values[::-1]):
        ax.text(v + 5, y, str(v), va="center", color=INK, fontsize=8)
    ax.set_xlabel("Agents")
    ax.set_title(f"Class balance: {int(labels['is_fraud'].sum())} fraud of {len(labels)} agents "
                 f"({labels['is_fraud'].mean():.1%}), by pattern")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in CLASS_COLORS.values()],
              labels=["Legitimate", "Fraud"], loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_volume_by_hour(acts, labels, path):
    acts = acts.merge(labels, on="agent_id")
    hours = pd.to_datetime(acts["timestamp"]).dt.hour
    fig, axes = plt.subplots(3, 3, figsize=(10, 7), sharex=True, sharey=True)
    for ax, group in zip(axes.flat, GROUP_ORDER):
        mask = acts["profile"] == group
        share = hours[mask].value_counts(normalize=True).reindex(range(24), fill_value=0)
        cls = "fraud" if acts.loc[mask, "is_fraud"].iloc[0] else "legit"
        ax.bar(share.index, share.values, color=CLASS_COLORS[cls], width=0.8)
        ax.set_title(f"{group} ({labels['profile'].eq(group).sum()} agents)")
        ax.set_xticks([0, 6, 12, 18, 23])
    for ax in axes[-1]:
        ax.set_xlabel("Hour of day (Africa/Nairobi)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of records")
    fig.suptitle("Volume by hour of day, per group (blue = legitimate, orange = fraud)", color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_distributions(table, path):
    fig, axes = plt.subplots(3, 3, figsize=(11, 9))
    for ax, (column, title) in zip(axes.flat, DESCRIPTORS.items()):
        data = [table.loc[table["profile"] == g, column].values for g in GROUP_ORDER]
        box = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=True,
                         flierprops={"markersize": 2, "markeredgecolor": INK_MUTED},
                         medianprops={"color": INK, "linewidth": 1.2})
        for patch, g in zip(box["boxes"], GROUP_ORDER):
            cls = "fraud" if g in table.loc[table["is_fraud"], "profile"].values else "legit"
            patch.set_facecolor(CLASS_COLORS[cls])
            patch.set_edgecolor(SURFACE)
        ax.set_title(title)
        ax.set_xticks(range(1, len(GROUP_ORDER) + 1), GROUP_ORDER, rotation=45, ha="right", fontsize=7)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Per-agent descriptors by group (blue = legitimate, orange = fraud)", color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_correlations(corr, path):
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    image = ax.imshow(corr.values, cmap=DIVERGING, vmin=-1, vmax=1)
    labels = [DESCRIPTORS[c] for c in corr.columns]
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(labels)), labels, fontsize=7)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=7, color=INK)
    ax.grid(False)
    fig.colorbar(image, ax=ax, fraction=0.046, label="Spearman correlation")
    ax.set_title("Correlation between per-agent descriptors (all 1000 agents)")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Exploratory analysis of the cleaned activation records.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--clean-run", type=Path, default=None)
    args = parser.parse_args(argv)

    clean_run = args.clean_run or latest_clean_run()
    inputs = [args.data_dir / f for f in ["activation_records.csv", "activation_records_clean.csv",
                                          "agents.csv", "clients.csv", "labels.csv"]]
    raw, acts, agents, clients, labels = (pd.read_csv(p, keep_default_na=False) for p in inputs)
    flags = pd.read_csv(clean_run / "record_flags.csv")
    run_dir = start_run("eda", SAMPLE_SEED, {"sample_rows": SAMPLE_ROWS, "night_hours": [0, 4],
                                             "clean_run": clean_run.name}, inputs + [clean_run / "record_flags.csv"])

    table = agent_descriptors(acts, flags).join(labels.set_index("agent_id")).join(agents.set_index("agent_id"))
    table.reset_index().to_csv(run_dir / "descriptors_by_agent.csv", index=False)

    by_group = table.groupby("profile")[list(DESCRIPTORS)].agg(
        lambda s: f"{s.median():.3g} [{s.quantile(0.25):.3g}-{s.quantile(0.75):.3g}]").reindex(GROUP_ORDER)
    by_group.insert(0, "agents", table["profile"].value_counts().reindex(GROUP_ORDER))
    by_group.to_csv(run_dir / "descriptors_by_group.csv")
    by_class = table.groupby("is_fraud")[list(DESCRIPTORS)].median().round(3).rename(index={False: "legit", True: "fraud"})

    corr = table[list(DESCRIPTORS)].corr(method="spearman").round(3)
    corr.to_csv(run_dir / "correlations.csv")
    upper = corr.where(np.triu(np.ones(corr.shape, dtype=bool), 1)).stack().sort_values(key=abs, ascending=False)
    upper = upper.rename_axis(["descriptor_a", "descriptor_b"])

    sample = raw.sample(SAMPLE_ROWS, random_state=SAMPLE_SEED).sort_values("timestamp")
    agent_sample = agents.sample(5, random_state=SAMPLE_SEED)
    raw_sample = (f"# Raw sample (seed {SAMPLE_SEED})\n\n## activation_records.csv ({len(raw)} rows, raw, before cleaning)\n\n"
                  f"{md_table(sample, index=False)}\n\n## agents.csv ({len(agents)} rows)\n\n{md_table(agent_sample, index=False)}\n\n"
                  f"## clients.csv ({len(clients)} rows, first 5)\n\n{md_table(clients.head(), index=False)}\n")
    (run_dir / "raw_sample.md").write_text(raw_sample, encoding="utf-8")

    figures = {
        "fig01_class_balance.png": "Agents per pattern, coloured by class.",
        "fig02_volume_by_hour.png": "Share of each group's records by hour of day.",
        "fig03_distributions_by_group.png": "Box plots of nine per-agent descriptors by group.",
        "fig04_correlations.png": "Spearman correlations between the descriptors.",
    }
    fig_class_balance(labels, run_dir / "fig01_class_balance.png")
    fig_volume_by_hour(acts, labels, run_dir / "fig02_volume_by_hour.png")
    fig_distributions(table, run_dir / "fig03_distributions_by_group.png")
    fig_correlations(corr, run_dir / "fig04_correlations.png")

    hours = pd.to_datetime(acts["timestamp"]).dt.hour
    fraud_records = acts["agent_id"].map(labels.set_index("agent_id")["is_fraud"])
    night = hours.isin(NIGHT_HOURS).groupby(fraud_records).mean()
    near = table.groupby("profile")["near_duplicates"].agg(agents_flagged=lambda s: int((s > 0).sum()),
                                                            flags="sum").reindex(GROUP_ORDER).astype(int)
    findings = f"""# EDA findings (run `{run_dir.name}`)

Inputs: cleaned activation records ({len(acts)} rows), {len(agents)} agents, {len(clients)} clients, labels, and near-duplicate flags from cleaning run `{clean_run.name}`.
EDA reads labels to describe groups and covers all agents, including those Step 5 will put in validation and test. The feature definitions were fixed in DATA_CARD.md before this EDA; nothing in later steps is chosen from it unless stated.

## Class balance
{int(labels['is_fraud'].sum())} fraud of {len(labels)} agents ({labels['is_fraud'].mean():.1%}). Fraud agents produce {fraud_records.mean():.1%} of records.

{md_table(labels['profile'].value_counts().reindex(GROUP_ORDER).rename('agents').to_frame())}

## Volume by hour
Share of records at 00:00-04:59: legitimate {night.get(False, 0):.1%}, fraud {night.get(True, 0):.1%}. Per group: see fig02.

## Distributions by group (median [IQR])
{md_table(by_group)}

Medians by class:

{md_table(by_class)}

## Near-duplicate flags from cleaning, by group
{md_table(near)}

## Strongest correlations between descriptors (Spearman, all agents)
{md_table(upper.head(6).rename('rho').to_frame())}

## Figures
""" + "\n".join(f"- `{name}`: {desc}" for name, desc in figures.items()) + "\n\nRaw sample table: `raw_sample.md`.\n"
    (run_dir / "findings.md").write_text(findings, encoding="utf-8")
    print(findings)
    print(raw_sample)
    print(f"Run folder {run_dir}")


if __name__ == "__main__":
    main()
