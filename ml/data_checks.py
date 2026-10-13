"""
Checks on a generated SyntheticDataset, written to the generation run folder
(data_checks.json) and reused by tests: integrity rules R1-R6, referential
integrity, value ranges, identity uniqueness and the independence table.
Labels are read here for checking the generator only; nothing in this file
feeds a feature or a model.
"""

import re

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.metrics import roc_auc_score

from data_generation import (
    ANALYSIS_START, CLIENT_CATEGORY, COUNTIES, COUNTY_TO_FORMER_PROVINCE, NATIONAL_ID_DIGITS, PHONE_DIGITS,
    PHONE_PREFIX, pending_window_start,
)
from feature_engineering import collusion_scores, identifier_similarity  # noqa: F401

SMALL_COUNTY_AGENTS = 5
INDEPENDENCE_AUC_RANGE = (0.35, 0.65)
PAIR = ["customer_id", "client_id"]


def by_class(counts, is_fraud):
    """Splits a per-agent count Series into honest and fraud totals."""
    fraud = np.array([bool(is_fraud.get(a, False)) for a in counts.index], dtype=bool)
    return {"honest": int(counts[~fraud].sum()), "fraud": int(counts[fraud].sum())}


def r1_shared_pairs(acts, is_fraud):
    """(customer, client) pairs used by 2+ agents: 'honest' if any user is honest, else 'fraud'."""
    users = acts[PAIR + ["agent_id"]].drop_duplicates()
    users = users.assign(fraud=users["agent_id"].map(is_fraud).astype(bool))
    per_pair = users.groupby(PAIR).agg(agents=("agent_id", "size"), all_fraud=("fraud", "all"))
    shared = per_pair[per_pair["agents"] >= 2]
    return {"honest": int((~shared["all_fraud"]).sum()), "fraud": int(shared["all_fraud"].sum())}


def r2_violations(acts):
    """Per agent: repeats of its own (customer, client) pair that do not follow a failed or pending attempt."""
    ordered = acts.sort_values(["timestamp", "record_id"], kind="mergesort")
    previous = ordered.groupby(["agent_id"] + PAIR)["activation_status"].shift()
    return previous.eq("completed").groupby(ordered["agent_id"]).sum()


def r6_violations(acts):
    old_pending = acts["activation_status"].eq("pending") & (pd.to_datetime(acts["timestamp"]) < pending_window_start())
    return old_pending.groupby(acts["agent_id"]).sum()


def r5_violations(acts, agents, agent_categories):
    """Per agent: activations before registration, or without a certification in force at that time."""
    ts = pd.to_datetime(acts["timestamp"])
    registration = acts["agent_id"].map(pd.to_datetime(agents.set_index("agent_id")["registration_timestamp"]))
    certified = agent_categories[agent_categories["certification_status"] == "certified"]
    cert_at = pd.MultiIndex.from_frame(acts[["agent_id", "category"]]).map(
        pd.to_datetime(certified.set_index(["agent_id", "category"])["certified_at"]).to_dict().get)
    cert_at = pd.to_datetime(pd.Series(cert_at, index=acts.index))
    bad = (ts < registration) | cert_at.isna() | (ts < cert_at)
    return bad.groupby(acts["agent_id"]).sum()


def referential_integrity(dataset):
    agents = set(dataset.agents["agent_id"])
    acts, cats = dataset.activations, dataset.agent_categories
    expired = cats[cats["certification_status"] == "expired"]
    active_in_expired = acts.merge(expired[["agent_id", "category"]], on=["agent_id", "category"])
    return {
        "unknown_agent_id": {name: int((~frame["agent_id"].isin(agents)).sum()) for name, frame in [
            ("activation_records", acts), ("agent_identity", dataset.identity),
            ("agent_categories", cats), ("labels", dataset.labels)]},
        "agents_missing_identity_row": len(agents - set(dataset.identity["agent_id"])),
        "duplicate_identity_rows": int(dataset.identity["agent_id"].duplicated().sum()),
        "unknown_client_id": int((~acts["client_id"].isin(dataset.clients["client_id"])).sum()),
        "category_not_client_category": int((acts["category"] != acts["client_id"].map(CLIENT_CATEGORY)).sum()),
        "clients_category_mismatch": int((dataset.clients["category"] != dataset.clients["client_id"].map(CLIENT_CATEGORY)).sum()),
        "duplicate_agent_category_rows": int(cats.duplicated(["agent_id", "category"]).sum()),
        "activations_in_expired_category": int(len(active_in_expired)),
        "certified_after_first_activity_or_before_registration": int(certification_order_errors(dataset)),
    }


def certification_order_errors(dataset):
    cats = dataset.agent_categories.assign(certified_at=pd.to_datetime(dataset.agent_categories["certified_at"]))
    registration = cats["agent_id"].map(pd.to_datetime(dataset.agents.set_index("agent_id")["registration_timestamp"]))
    first = dataset.activations.assign(timestamp=pd.to_datetime(dataset.activations["timestamp"])).groupby(
        ["agent_id", "category"])["timestamp"].min()
    first_at = pd.MultiIndex.from_frame(cats[["agent_id", "category"]]).map(first.to_dict().get)
    first_at = pd.to_datetime(pd.Series(first_at, index=cats.index))
    return int(((cats["certified_at"] < registration) | (first_at.notna() & (cats["certified_at"] > first_at))).sum())


def rule_checks(dataset):
    acts = dataset.activations
    is_fraud = dataset.labels.set_index("agent_id")["is_fraud"].astype(bool).to_dict()
    honest = acts[~acts["agent_id"].map(is_fraud).astype(bool)]
    honest_customers = honest.groupby("customer_id")["agent_id"].nunique()
    honest_pairs = honest.groupby(PAIR)["agent_id"].nunique()
    expired = dataset.agent_categories["certification_status"].eq("expired")
    return {
        "R1_pairs_used_by_another_agent": r1_shared_pairs(acts, is_fraud),
        "R2_repeat_after_completed": by_class(r2_violations(acts), is_fraud),
        "R3_honest_customers_shared_by_2plus_honest_agents": int((honest_customers >= 2).sum()),
        "R3_honest_pairs_shared_by_2plus_honest_agents": int((honest_pairs >= 2).sum()),
        "R5_activation_without_certification_or_before_registration": by_class(
            r5_violations(acts, dataset.agents, dataset.agent_categories), is_fraud),
        "R5_agents_with_expired_category": int(dataset.agent_categories.loc[expired, "agent_id"].nunique()),
        "R6_pending_before_last_72h": by_class(r6_violations(acts), is_fraud),
    }


def range_checks(dataset):
    acts = dataset.activations
    completed = acts["activation_status"].eq("completed")
    rate = acts["client_id"].map(dataset.clients.set_index("client_id")["commission_per_activation_kes"])
    return {
        "quality_score_outside_0_100": int((~acts["quality_score"].between(0, 100)).sum()),
        "commission_nonzero_when_not_completed": int((acts.loc[~completed, "commission_kes"] != 0).sum()),
        "commission_not_client_rate_when_completed": int((acts.loc[completed, "commission_kes"] != rate[completed]).sum()),
        "client_rate_outside_40_400": int((~dataset.clients["commission_per_activation_kes"].between(40, 400)).sum()),
        "account_status_values": dataset.agents["account_status"].value_counts().to_dict(),
    }


def identity_checks(identity):
    phone = rf"^{re.escape(PHONE_PREFIX)}\d{{{PHONE_DIGITS}}}$"
    return {
        "rows": int(len(identity)),
        "duplicate_full_name": int(identity["full_name"].duplicated().sum()),
        "duplicate_phone_number": int(identity["phone_number"].duplicated().sum()),
        "duplicate_national_id_number": int(identity["national_id_number"].duplicated().sum()),
        "malformed_full_name": int((~identity["full_name"].str.fullmatch(r"[A-Z][a-z]+ [A-Z][a-z]+")).sum()),
        "malformed_phone_number": int((~identity["phone_number"].str.fullmatch(phone)).sum()),
        "malformed_national_id_number": int(
            (~identity["national_id_number"].astype(str).str.fullmatch(rf"[1-9]\d{{{NATIONAL_ID_DIGITS - 1}}}")).sum()),
    }


def context_by_agent(dataset):
    acts = dataset.activations
    by_agent = acts.groupby("agent_id")
    agents = dataset.agents.set_index("agent_id")
    return pd.DataFrame({
        "account_status_suspended": agents["account_status"].eq("suspended").astype(int),
        "n_categories": dataset.agent_categories.groupby("agent_id").size(),
        "registration_age_days": (ANALYSIS_START - pd.to_datetime(agents["registration_timestamp"])).dt.days,
        "mean_quality_score": by_agent["quality_score"].mean(),
        "completed_share": acts["activation_status"].eq("completed").groupby(acts["agent_id"]).mean(),
        "commission_total_kes": by_agent["commission_kes"].sum(),
        "commission_mean_per_record_kes": by_agent["commission_kes"].mean(),
    }).fillna(0)


def independence_table(dataset):
    """Single-field AUC against is_fraud (data audit only; never a model input)."""
    table = context_by_agent(dataset)
    y = dataset.labels.set_index("agent_id")["is_fraud"].astype(bool).reindex(table.index)
    rows = {}
    for column in table:
        auc = float(roc_auc_score(y, table[column]))
        rows[column] = {"auc": round(auc, 3), "strength": round(max(auc, 1 - auc), 3),
                        "within_0.35_0.65": bool(INDEPENDENCE_AUC_RANGE[0] <= auc <= INDEPENDENCE_AUC_RANGE[1])}
    return rows


def behaviour_summary(dataset):
    acts = dataset.activations.merge(dataset.labels[["agent_id", "is_fraud", "profile"]], on="agent_id")
    acts = acts.sort_values(["timestamp", "record_id"], kind="mergesort")
    lab = dataset.labels.set_index("agent_id")
    coll = collusion_scores(dataset.activations).reindex(lab.index).fillna(0)
    honest = acts[~acts["is_fraud"]]
    acts["repeat_customer"] = acts.duplicated(["agent_id", "customer_id"])
    acts["repeat_pair"] = acts.duplicated(["agent_id"] + PAIR)
    users = acts[PAIR + ["agent_id", "is_fraud"]].drop_duplicates(PAIR + ["agent_id"])
    per_pair = users.groupby(PAIR).agg(agents=("agent_id", "size"), fraud_agents=("is_fraud", "sum"))
    per_agent = acts.groupby("agent_id").size()
    rpa = per_agent.groupby(lab["profile"]).agg(["mean", "min", "max"]).round(1)

    def spread(series):
        return [round(float(x), 3) for x in series.agg(["min", "median", "max"])]

    return {
        "fraud_by_pattern": lab.loc[lab["is_fraud"], "profile"].value_counts().sort_index().to_dict(),
        "honest_collusion_max": round(float(coll[~lab["is_fraud"]].max()), 3),
        "honest_collusion_nonzero": int((coll[~lab["is_fraud"]] > 0).sum()),
        "strong_ring_collusion_min_median_max": spread(coll[lab["profile"] == "ring"]),
        "weak_ring_collusion_min_median_max": spread(coll[lab["profile"] == "weak_ring"]),
        "repeat_customer_share_by_profile": acts.groupby("profile")["repeat_customer"].mean().round(4).to_dict(),
        "repeat_pair_share_by_profile": acts.groupby("profile")["repeat_pair"].mean().round(4).to_dict(),
        "records_per_agent_by_profile": {p: r.to_dict() for p, r in rpa.iterrows()},
        "customers_shared_by_2plus_honest_agents": int((honest.groupby("customer_id")["agent_id"].nunique() >= 2).sum()),
        "pairs_shared_by_2plus_honest_agents": int((honest.groupby(PAIR)["agent_id"].nunique() >= 2).sum()),
        "pairs_shared_by_2plus_fraud_agents": int((per_pair["fraud_agents"] >= 2).sum()),
        "pairs_shared_by_honest_and_fraud": int(((per_pair["fraud_agents"] >= 1) & (per_pair["agents"] > per_pair["fraud_agents"])).sum()),
    }


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
        "referential_integrity": referential_integrity(dataset),
        "rules": rule_checks(dataset),
        "ranges": range_checks(dataset),
        "identity": identity_checks(dataset.identity),
        "independence_auc": independence_table(dataset),
        "behaviour": behaviour_summary(dataset),
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
