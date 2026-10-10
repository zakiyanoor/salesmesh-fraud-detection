"""
Checks on a generated SyntheticDataset, written to the generation run folder
(data_checks.json) and reused by tests. Labels are read here for checking the
generator only; nothing in this file feeds a feature or a model.
"""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from data_generation import COUNTIES, COUNTY_TO_FORMER_PROVINCE

SMALL_COUNTY_AGENTS = 5


def primary_by_agent(activations, column):
    """Most frequent value of column per agent; ties broken alphabetically."""
    counts = activations.groupby(["agent_id", column]).size().rename("n").reset_index()
    counts = counts.sort_values(["agent_id", "n", column], ascending=[True, False, True])
    return counts.drop_duplicates("agent_id").set_index("agent_id")[column]


def collusion_scores(activations):
    """Same formula as feature_engineering.compute_collusion_score, vectorised."""
    pairs = activations[["agent_id", "customer_id"]].drop_duplicates()
    owners = pairs.groupby("customer_id")["agent_id"].nunique()
    pairs = pairs.assign(shared=pairs["customer_id"].map(owners) > 1)
    return pairs.groupby("agent_id")["shared"].mean()


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
