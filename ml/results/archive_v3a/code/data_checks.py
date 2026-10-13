"""
Checks on a generated SyntheticDataset, written to the generation run folder
(data_checks.json) and reused by tests. Labels are read here for checking the
generator only; nothing in this file feeds a feature or a model.
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from data_generation import COUNTIES, COUNTY_TO_FORMER_PROVINCE
from feature_engineering import collusion_scores, identifier_similarity  # noqa: F401

SMALL_COUNTY_AGENTS = 5


def primary_by_agent(activations, column):
    """Most frequent value of column per agent; ties broken alphabetically."""
    counts = activations.groupby(["agent_id", column]).size().rename("n").reset_index()
    counts = counts.sort_values(["agent_id", "n", column], ascending=[True, False, True])
    return counts.drop_duplicates("agent_id").set_index("agent_id")[column]


def agent_table(dataset):
    table = dataset.agents.merge(dataset.labels, on="agent_id").set_index("agent_id")
    table["former_region"] = table["region"].map(COUNTY_TO_FORMER_PROVINCE)
    table["primary_category"] = primary_by_agent(dataset.activations, "category")
    table["primary_client"] = primary_by_agent(dataset.activations, "client_id")
    table["n_clients"] = dataset.activations.groupby("agent_id")["client_id"].nunique()
    table["n_categories"] = dataset.activations.groupby("agent_id")["category"].nunique()
    table["collusion"] = collusion_scores(dataset.activations)
    table["group"] = np.select(
        [~table["is_fraud"], table["profile"] == "ring", table["profile"] == "weak_ring"],
        ["legitimate", "strong_ring", "weak_ring"], "other_fraud")
    return table


def chi_square_p(table, column):
    return float(chi2_contingency(pd.crosstab(table[column], table["is_fraud"]))[1])


def run_checks(dataset):
    table = agent_table(dataset)
    acts = dataset.activations
    per_county = table["region"].value_counts().reindex(COUNTIES, fill_value=0)

    repeats = acts.groupby(["agent_id", "customer_id", "client_id"]).size()
    customer_clients = acts.groupby(["agent_id", "customer_id"])["client_id"].nunique()

    def group_stats(series):
        return {"agents": int(series.size), "min": round(float(series.min()), 3),
                "median": round(float(series.median()), 3), "max": round(float(series.max()), 3),
                "nonzero": int((series > 0).sum())}

    by_category = table.groupby("primary_category")["is_fraud"].agg(agents="size", fraud="sum")
    return {
        "agents": int(len(table)), "fraud_agents": int(table["is_fraud"].sum()),
        "fraud_rate": round(float(table["is_fraud"].mean()), 4), "records": int(len(acts)),
        "agents_by_pattern": table["profile"].value_counts().sort_index().to_dict(),
        "fraud_by_pattern": table.loc[table["is_fraud"], "profile"].value_counts().sort_index().to_dict(),
        "agents_per_county": {"min": int(per_county.min()), "median": float(per_county.median()),
                              "max": int(per_county.max()),
                              f"counties_under_{SMALL_COUNTY_AGENTS}": int((per_county < SMALL_COUNTY_AGENTS).sum()),
                              "smallest": per_county.sort_values().head(8).to_dict(),
                              "largest": per_county.sort_values(ascending=False).head(6).to_dict()},
        "agents_per_former_region": table["former_region"].value_counts().sort_index().to_dict(),
        "agents_per_primary_category": by_category["agents"].astype(int).sort_values(ascending=False).to_dict(),
        "fraud_by_primary_category": by_category["fraud"].astype(int).sort_values(ascending=False).to_dict(),
        "clients_per_agent": table["n_clients"].value_counts().sort_index().to_dict(),
        "categories_per_agent": table["n_categories"].value_counts().sort_index().to_dict(),
        "chi_square_p_fraud_vs": {
            "county": round(chi_square_p(table, "region"), 3),
            "former_region": round(chi_square_p(table, "former_region"), 3),
            "primary_category": round(chi_square_p(table, "primary_category"), 3),
            "primary_client": round(chi_square_p(table, "primary_client"), 3),
        },
        "collusion_score": {g: group_stats(table.loc[table["group"] == g, "collusion"])
                            for g in ["legitimate", "strong_ring", "weak_ring", "other_fraud"]},
        "same_customer_same_client_repeats": {
            g: int((repeats[repeats.index.get_level_values("agent_id").isin(table.index[table["group"] == g])] - 1).sum())
            for g in ["legitimate", "strong_ring", "weak_ring", "other_fraud"]},
        "same_customer_different_clients_pairs": int((customer_clients > 1).sum()),
    }


AUDIT_GROUPS = ["legit", "ring", "weak_ring", "sequential", "duplicate", "weak"]
AUDIT_DESCRIPTORS = {
    "volume": "Submissions in window",
    "max_per_day": "Max submissions in one day",
    "mean_per_active_day": "Mean submissions per active day",
    "hours_used": "Distinct hours used",
    "night_share": "Share of submissions 00:00-04:59",
    "hour_entropy": "Hour-of-day entropy (0-1)",
    "weekend_share": "Share of submissions on Sat/Sun",
    "customers_per_client": "Distinct customers per client",
    "repeat_share": "Share repeating an earlier customer+client",
    "clients_per_agent": "Clients per agent",
    "registration_age_days": "Registration age (days)",
    "completed_share": "Share of completed activations",
    "collusion_score": "Collusion score",
    "customer_similarity": "Customer similarity (identifiers)",
}


def raw_descriptors(dataset):
    from data_generation import ANALYSIS_START

    acts = dataset.activations.assign(timestamp=pd.to_datetime(dataset.activations["timestamp"]))
    hours = acts["timestamp"].dt.hour
    by_agent = acts.groupby("agent_id")
    per_day = acts.groupby(["agent_id", acts["timestamp"].dt.date]).size()
    entropy = hours.groupby(acts["agent_id"]).apply(
        lambda h: float(-(h.value_counts(normalize=True) * np.log2(h.value_counts(normalize=True))).sum() / np.log2(24)))
    registration = pd.to_datetime(dataset.agents.set_index("agent_id")["registration_timestamp"])
    table = pd.DataFrame({
        "volume": by_agent.size(),
        "max_per_day": per_day.groupby(level=0).max(),
        "mean_per_active_day": per_day.groupby(level=0).mean(),
        "hours_used": hours.groupby(acts["agent_id"]).nunique(),
        "night_share": hours.lt(5).groupby(acts["agent_id"]).mean(),
        "hour_entropy": entropy,
        "weekend_share": acts["timestamp"].dt.dayofweek.ge(5).groupby(acts["agent_id"]).mean(),
        "customers_per_client": by_agent["customer_id"].nunique() / by_agent["client_id"].nunique(),
        "repeat_share": acts.duplicated(["agent_id", "customer_id", "client_id"]).groupby(acts["agent_id"]).mean(),
        "clients_per_agent": by_agent["client_id"].nunique(),
        "registration_age_days": (ANALYSIS_START - registration).dt.days,
        "completed_share": acts["activation_status"].eq("completed").groupby(acts["agent_id"]).mean(),
        "collusion_score": collusion_scores(acts),
        "customer_similarity": by_agent["customer_id"].apply(identifier_similarity),
    })
    labels = dataset.labels.set_index("agent_id")
    table["group"] = np.where(labels["is_fraud"].reindex(table.index), labels["profile"].reindex(table.index), "legit")
    return table


def overlap_audit(dataset):
    """min/median/max per group; a fraud group has zero overlap when its range is disjoint from legit's."""
    table = raw_descriptors(dataset)
    rows = []
    for column in AUDIT_DESCRIPTORS:
        legit = table.loc[table["group"] == "legit", column]
        for group in AUDIT_GROUPS:
            values = table.loc[table["group"] == group, column]
            outside = ((values < legit.min()) | (values > legit.max())).mean() if group != "legit" else 0.0
            rows.append({
                "descriptor": column, "group": group, "agents": int(values.size),
                "min": round(float(values.min()), 4), "median": round(float(values.median()), 4),
                "max": round(float(values.max()), 4),
                "share_outside_legit_range": round(float(outside), 3),
                "zero_overlap": bool(group != "legit" and (values.min() > legit.max() or values.max() < legit.min())),
            })
    return pd.DataFrame(rows), table


def repetition_score(customer_ids):
    """Generator check: 1 - distinct / total customer ids."""
    return 0.0 if len(customer_ids) == 0 else 1 - customer_ids.nunique() / len(customer_ids)


def sequential_score(customer_ids):
    """Generator check: share of consecutive pairs among sorted distinct numeric ids that differ by 1."""
    numbers = sorted({int(str(c)[4:]) for c in customer_ids.unique()})
    if len(numbers) < 2:
        return 0.0
    return sum(1 for a, b in zip(numbers, numbers[1:]) if b - a == 1) / (len(numbers) - 1)
