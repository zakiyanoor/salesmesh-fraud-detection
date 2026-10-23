"""
Threat intelligence views (issue #18): read only, from the latest successful
detection run and the loaded activation records. No label is used.

"Flagged" means flagged by the model (flag_source ML or Both), the primary
flag; the duplicate rule is reported beside it as "rule flagged".
"""

from collections import Counter

import pandas as pd
from sqlalchemy import text

from src.db import DetectionRun
from src.risk import RISK_BANDS, risk_band

FLAG_SOURCES = ("ML", "Rule", "Both", "None")
MODEL_FLAGGED = ("ML", "Both")
TOP_REGIONS = 10
MIN_REGION_AGENTS = 5
TOP_CLUSTERS = 50
TOP_CUSTOMERS = 50
# The Step 11 ring-candidate rule (ml/final_evaluation.py, RING_MIN_SHARED_CUSTOMERS), unchanged (issue #26).
RING_MIN_SHARED_CUSTOMERS = 3
RING_RULE = ("Agents the model flagged (flag_source ML or Both) are linked when two of them share at least "
             f"{RING_MIN_SHARED_CUSTOMERS} customers, for any client; linked agents are joined into groups, "
             "and every group of 2 or more is a ring candidate. No label is used.")


def latest_run(db_session):
    return (db_session.query(DetectionRun).filter(DetectionRun.status == "succeeded")
            .order_by(DetectionRun.finished_at.desc()).first())


def run_info(run):
    return {"run_id": run.run_id, "model_version": run.model_version, "threshold": round(run.threshold, 6),
            "finished_at": run.finished_at.isoformat()}


def read(db_session, sql, **params):
    return pd.read_sql(text(sql), db_session.connection(), params=params)


def scores(db_session, run):
    frame = read(db_session, "SELECT s.agent_id, s.flag_source, s.flagged, s.rule_flagged, s.anomaly_score, "
                             "s.threshold, s.top_features, a.region FROM agent_scores s "
                             "JOIN agents a ON a.agent_id = s.agent_id WHERE s.run_id = :run", run=run.run_id)
    frame["model_flagged"] = frame["flag_source"].isin(MODEL_FLAGGED)
    frame["risk_band"] = [risk_band(f, s, t) for f, s, t in zip(frame["flag_source"], frame["anomaly_score"],
                                                                 frame["threshold"])]
    return frame


def records(db_session, run):
    frame = read(db_session, "SELECT r.agent_id, r.timestamp, r.client_id, r.category, r.commission_kes "
                             "FROM activation_records r")
    flag = scores(db_session, run).set_index("agent_id")
    frame["model_flagged"] = frame["agent_id"].map(flag["model_flagged"]).fillna(False).astype(bool)
    frame["any_flag"] = frame["agent_id"].map(flag["flag_source"] != "None").fillna(False).astype(bool)
    return frame


def summary(db_session, run):
    s, r = scores(db_session, run), records(db_session, run)
    total_commission = int(r["commission_kes"].fillna(0).sum())
    flagged_commission = int(r.loc[r["model_flagged"], "commission_kes"].fillna(0).sum())
    any_commission = int(r.loc[r["any_flag"], "commission_kes"].fillna(0).sum())
    flagged = s[s["model_flagged"]]
    first = Counter(t.split(";")[0] for t in flagged["top_features"].dropna() if t)
    anywhere = Counter(f for t in flagged["top_features"].dropna() for f in t.split(";") if f)
    return {
        "run": run_info(run),
        "agents_scored": len(s),
        "flag_sources": {k: int((s["flag_source"] == k).sum()) for k in FLAG_SOURCES},
        "flagged": int(s["model_flagged"].sum()),
        "flagged_rate": round(float(s["model_flagged"].mean()), 6) if len(s) else 0.0,
        "rule_flagged": int(s["rule_flagged"].sum()),
        "risk_bands": {b: int((s["risk_band"] == b).sum()) for b in RISK_BANDS},
        "commission_kes": {
            "total": total_commission,
            "flagged_agents": flagged_commission,
            "flagged_share": round(flagged_commission / total_commission, 6) if total_commission else 0.0,
            "any_flag_agents": any_commission,
            "any_flag_share": round(any_commission / total_commission, 6) if total_commission else 0.0,
        },
        "top_features": {
            "as_top_feature": [{"feature": f, "agents": n} for f, n in first.most_common()],
            "in_top_three": [{"feature": f, "agents": n} for f, n in anywhere.most_common()],
        },
    }


def by_region(db_session, run):
    s = scores(db_session, run)
    table = s.groupby("region").agg(agents=("agent_id", "size"), flagged=("model_flagged", "sum"),
                                    rule_flagged=("rule_flagged", "sum")).reset_index()
    table["flagged_rate"] = (table["flagged"] / table["agents"]).round(6)
    rows = [{"region": r.region, "agents": int(r.agents), "flagged": int(r.flagged),
             "rule_flagged": int(r.rule_flagged), "flagged_rate": float(r.flagged_rate)} for r in table.itertuples()]
    top = sorted((r for r in rows if r["agents"] >= MIN_REGION_AGENTS),
                 key=lambda r: (-r["flagged_rate"], -r["flagged"], r["region"]))[:TOP_REGIONS]
    return {"run": run_info(run), "regions": sorted(rows, key=lambda r: r["region"]),
            "top_by_flagged_rate": top, "min_agents_for_top": MIN_REGION_AGENTS}


def by_column(db_session, run, column):
    r = records(db_session, run)
    table = r.groupby(column).agg(activations=("agent_id", "size"), flagged_activations=("model_flagged", "sum"),
                                  flagged_agents=("agent_id", lambda a: a[r.loc[a.index, "model_flagged"]].nunique()))
    total_flagged = int(r["model_flagged"].sum())
    rows = []
    for key, row in table.sort_index().iterrows():
        rows.append({column: key, "activations": int(row.activations),
                     "flagged_activations": int(row.flagged_activations),
                     "flagged_agents": int(row.flagged_agents),
                     "flagged_share_of_activations": round(row.flagged_activations / row.activations, 6),
                     "share_of_all_flagged_activations": round(row.flagged_activations / total_flagged, 6)
                     if total_flagged else 0.0})
    return rows


def by_client(db_session, run):
    rows = by_column(db_session, run, "client_id")
    clients = read(db_session, "SELECT client_id, name, category FROM clients").set_index("client_id")
    for row in rows:
        if row["client_id"] in clients.index:
            row["name"], row["category"] = clients.at[row["client_id"], "name"], clients.at[row["client_id"], "category"]
    return {"run": run_info(run), "clients": rows}


def by_category(db_session, run):
    return {"run": run_info(run), "categories": by_column(db_session, run, "category")}


def timeline(db_session, run):
    r = records(db_session, run)
    day = pd.to_datetime(r["timestamp"]).dt.normalize()
    counts = r.assign(day=day).groupby(["day", "model_flagged"]).size().unstack(fill_value=0)
    days = pd.date_range(day.min(), day.max(), freq="D")
    counts = counts.reindex(days, fill_value=0).reindex(columns=[True, False], fill_value=0)
    return {"run": run_info(run), "first_day": days[0].date().isoformat(), "last_day": days[-1].date().isoformat(),
            "days": [{"date": d.date().isoformat(), "flagged_agents": int(c[True]), "other_agents": int(c[False])}
                     for d, c in counts.iterrows()]}


def components(edges):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        parent[find(a)] = find(b)
    groups = {}
    for node in list(parent):
        groups.setdefault(find(node), set()).add(node)
    return list(groups.values())


def customer_sharing(db_session, run):
    evidence = read(db_session, "SELECT agent_id, other_agent_id, customer_id, client_id FROM duplicate_evidence "
                                "WHERE run_id = :run AND reason = 'shared customer'", run=run.run_id)
    flagged = set(scores(db_session, run).query("model_flagged")["agent_id"])
    customers = []
    for customer, group in evidence.groupby("customer_id"):
        agents = sorted(set(group["agent_id"]) | set(group["other_agent_id"]))
        customers.append({"customer_id": customer, "agent_count": len(agents), "agent_ids": agents,
                          "client_ids": sorted(set(group["client_id"]))})
    customers.sort(key=lambda c: (-c["agent_count"], c["customer_id"]))
    clusters = []
    for members in components(zip(evidence["agent_id"], evidence["other_agent_id"])):
        rows = evidence[evidence["agent_id"].isin(members)]
        clusters.append({"size": len(members), "agent_ids": sorted(members),
                         "client_ids": sorted(set(rows["client_id"])),
                         "customer_count": int(rows["customer_id"].nunique()),
                         "flagged_agents": len(members & flagged)})
    clusters.sort(key=lambda c: (-c["size"], -c["customer_count"], c["agent_ids"][0]))
    return {"run": run_info(run), "shared_customers": len(customers), "clusters_total": len(clusters),
            "customers": customers[:TOP_CUSTOMERS], "clusters": clusters[:TOP_CLUSTERS],
            "limits": {"customers": TOP_CUSTOMERS, "clusters": TOP_CLUSTERS}}


def ring_candidate_groups(customers_by_agent, min_shared=RING_MIN_SHARED_CUSTOMERS):
    """Groups (size >= 2) of agents joined by sharing >= min_shared customers; customers_by_agent = {agent: set}."""
    agents = sorted(customers_by_agent)
    edges = [(a, b) for i, a in enumerate(agents) for b in agents[i + 1:]
             if len(customers_by_agent[a] & customers_by_agent[b]) >= min_shared]
    return [g for g in components(edges) if len(g) >= 2]


def ring_candidates(db_session, run):
    flagged = scores(db_session, run).query("model_flagged")["agent_id"].tolist()
    records = read(db_session, "SELECT agent_id, customer_id, client_id FROM activation_records "
                               "WHERE agent_id = ANY(:agents)", agents=flagged)
    customers = records.groupby("agent_id")["customer_id"].agg(set).to_dict()
    groups = sorted((sorted(g) for g in ring_candidate_groups(customers)), key=lambda g: (-len(g), g[0]))
    candidates = []
    for i, members in enumerate(groups, start=1):
        rows = records[records["agent_id"].isin(members)]
        owners = rows.groupby("customer_id")["agent_id"].nunique()
        shared = set(owners[owners >= 2].index)
        candidates.append({"candidate_id": f"cand_{i:02d}", "size": len(members), "agent_ids": members,
                           "shared_customers": len(shared),
                           "client_ids": sorted(set(rows.loc[rows["customer_id"].isin(shared), "client_id"]))})
    return {"run": run_info(run), "rule": RING_RULE, "min_shared_customers": RING_MIN_SHARED_CUSTOMERS,
            "flagged_agents": len(flagged), "candidates_total": len(candidates), "candidates": candidates}


VIEWS = {"summary": summary, "by-region": by_region, "by-client": by_client, "by-category": by_category,
         "timeline": timeline, "customer-sharing": customer_sharing, "ring-candidates": ring_candidates}
