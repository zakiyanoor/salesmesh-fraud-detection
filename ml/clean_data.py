"""
Data cleaning for the SalesMesh fraud detection pipeline (Step 2).

Checks the raw files, removes only rows that are invalid, flags the rest, and
writes a report of exactly what was checked and found. No check reads the
fraud labels, so no cleaning decision can depend on which agents are fraud.

Checks:
1. Schema and missing values in activation_records, agents and clients.
2. Duplicates: exact duplicate rows and duplicate record_ids are removed as
   ingestion errors. Duplicate events (same agent, customer, client and
   timestamp under different record_ids) are flagged and kept.
3. Near duplicates, flagged and kept: the same agent submitting the same
   customer for the same client within NEAR_DUPLICATE_MINUTES, and the same
   agent and client with a customer id one digit away within that window.
   Resubmission is a fraud pattern the features measure, so removing these
   rows would remove signal.
4. Formats and invalid values: id formats, activation_status, client_id in
   clients.csv, category equal to the client's category, region a county.
5. Impossible timestamps: unparseable, outside the observation window, or
   before the agent's registration. These rows are removed.
6. Outliers: per-agent and per-agent-day volume by the IQR rule and robust
   z-score. Flagged, NOT removed: in unsupervised anomaly detection the
   outliers are the behaviour being detected.

Failed and pending activations are kept and count as submissions: features
measure attempted activations, and status is independent of fraud here.

Flags are written to the run folder, never into activation_records_clean.csv,
so they cannot become model inputs.

Usage: python clean_data.py [--data-dir DIR] [--report PATH]
Output: <data-dir>/activation_records_clean.csv, results/data_cleaning_report.md
        and ml/runs/<run_id>/ (run_info.json, report, record_flags.csv, agent_outliers.csv)
"""

import argparse
from pathlib import Path

import pandas as pd

from data_generation import (
    ANALYSIS_END, ANALYSIS_START, CLIENT_CATEGORY, COUNTIES, CUSTOMER_ID_DIGITS, DEFAULT_OUT_DIR, clients_frame,
)

DEFAULT_REPORT = Path(__file__).resolve().parent / "results" / "data_cleaning_report.md"

EXPECTED_COLUMNS = [
    "record_id", "agent_id", "timestamp", "customer_id", "activation_status", "client_id", "category",
    "quality_score", "commission_kes",
]
REQUIRED_COLUMNS = ["agent_id", "timestamp", "customer_id"]
VALID_STATUSES = {"completed", "pending", "failed"}
CUSTOMER_ID_PATTERN = rf"^CUST\d{{{CUSTOMER_ID_DIGITS}}}$"
RECORD_ID_PATTERN = r"^R\d+$"
AGENT_ID_PATTERN = r"^A\d{5}$"
CLIENT_ID_PATTERN = r"^CL\d{2}$"

NEAR_DUPLICATE_MINUTES = 10
IQR_MULTIPLIER = 1.5
ROBUST_Z_THRESHOLD = 3.5


def outlier_flags(values):
    """IQR and robust-z outlier flags for a numeric Series (label-free)."""
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr_upper = q3 + IQR_MULTIPLIER * (q3 - q1)
    median = values.median()
    mad = (values - median).abs().median()
    robust_z = (values - median).abs() / (1.4826 * mad) if mad > 0 else pd.Series(0.0, index=values.index)
    flags = pd.DataFrame({"value": values, "iqr_outlier": values > iqr_upper,
                          "robust_z_outlier": robust_z > ROBUST_Z_THRESHOLD})
    summary = {"n": len(values), "min": values.min(), "median": median, "max": values.max(),
               "iqr_upper_fence": iqr_upper, "iqr_outliers": int(flags["iqr_outlier"].sum()),
               "robust_z_outliers": int(flags["robust_z_outlier"].sum())}
    return flags, summary


def one_digit_apart(a, b):
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def near_duplicates(df):
    """Record ids flagged as near duplicates of an earlier record by the same agent for the same client."""
    window = pd.Timedelta(minutes=NEAR_DUPLICATE_MINUTES)
    same_customer, one_digit = set(), set()
    for _, group in df.sort_values("timestamp").groupby(["agent_id", "client_id"], sort=False):
        times = group["timestamp"].tolist()
        customers = group["customer_id"].tolist()
        ids = group["record_id"].tolist()
        start = 0
        for j in range(len(times)):
            while times[j] - times[start] > window:
                start += 1
            for i in range(start, j):
                if times[j] == times[i]:
                    continue
                if customers[i] == customers[j]:
                    same_customer.add(ids[j])
                elif one_digit_apart(customers[i], customers[j]):
                    one_digit.add(ids[j])
    return same_customer, one_digit - same_customer


def check_agents(agents_df):
    registration = pd.to_datetime(agents_df["registration_timestamp"], errors="coerce")
    return {
        "rows": len(agents_df),
        "nulls": int(agents_df.isna().sum().sum()),
        "duplicate_agent_id": int(agents_df["agent_id"].duplicated().sum()),
        "malformed_agent_id": int((~agents_df["agent_id"].astype(str).str.match(AGENT_ID_PATTERN)).sum()),
        "unparseable_registration": int(registration.isna().sum()),
        "registration_after_window": int((registration > ANALYSIS_END + pd.Timedelta(days=1)).sum()),
        "region_not_a_county": int((~agents_df["region"].isin(COUNTIES)).sum()),
    }


def check_clients(clients_df):
    return {
        "rows": len(clients_df),
        "nulls": int(clients_df.isna().sum().sum()),
        "duplicate_client_id": int(clients_df["client_id"].duplicated().sum()),
        "malformed_client_id": int((~clients_df["client_id"].astype(str).str.match(CLIENT_ID_PATTERN)).sum()),
    }


def clean_data(activations_df, agents_df, clients_df=None):
    """Returns (clean_df, findings, record_flags, agent_outliers). Labels are never read."""
    clients_df = clients_frame() if clients_df is None else clients_df
    client_category = dict(zip(clients_df["client_id"], clients_df["category"]))
    df = activations_df.copy()
    findings = {"rows_in": len(df), "agents_table": check_agents(agents_df), "clients_table": check_clients(clients_df)}

    findings["missing_columns"] = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if findings["missing_columns"]:
        raise ValueError(f"activation records missing columns: {findings['missing_columns']}")

    findings["nulls_per_column"] = df[EXPECTED_COLUMNS].isna().sum().to_dict()
    missing_required = df[REQUIRED_COLUMNS].isna().any(axis=1)
    findings["removed_missing_required"] = int(missing_required.sum())
    df = df[~missing_required]

    exact_dupes = df.duplicated(keep="first")
    findings["removed_exact_duplicate_rows"] = int(exact_dupes.sum())
    df = df[~exact_dupes]

    dupe_ids = df.duplicated(subset="record_id", keep="first")
    findings["removed_duplicate_record_ids"] = int(dupe_ids.sum())
    df = df[~dupe_ids]

    registration = agents_df.set_index("agent_id")["registration_timestamp"].pipe(pd.to_datetime, errors="coerce")
    df = df.assign(timestamp=pd.to_datetime(df["timestamp"], errors="coerce"))
    window_end = ANALYSIS_END + pd.Timedelta(days=1)
    invalid = {
        "malformed_record_id": ~df["record_id"].astype(str).str.match(RECORD_ID_PATTERN),
        "malformed_agent_id": ~df["agent_id"].astype(str).str.match(AGENT_ID_PATTERN),
        "unknown_agent_id": ~df["agent_id"].isin(agents_df["agent_id"]),
        "malformed_customer_id": ~df["customer_id"].astype(str).str.match(CUSTOMER_ID_PATTERN),
        "unknown_client_id": ~df["client_id"].isin(client_category),
        "category_not_client_category": df["client_id"].isin(client_category)
        & (df["category"] != df["client_id"].map(client_category)),
        "invalid_activation_status": ~df["activation_status"].isin(VALID_STATUSES),
        "unparseable_timestamp": df["timestamp"].isna(),
        "timestamp_outside_window": df["timestamp"].notna()
        & ((df["timestamp"] < ANALYSIS_START) | (df["timestamp"] >= window_end)),
        "timestamp_before_registration": df["timestamp"] < df["agent_id"].map(registration),
    }
    findings["invalid"] = {name: int(mask.sum()) for name, mask in invalid.items()}
    any_invalid = pd.concat(invalid.values(), axis=1).any(axis=1)
    findings["removed_invalid"] = int(any_invalid.sum())
    df = df[~any_invalid]

    duplicate_events = df.duplicated(subset=["agent_id", "customer_id", "client_id", "timestamp"], keep="first")
    same_customer, one_digit = near_duplicates(df)
    record_flags = pd.concat([
        pd.DataFrame({"record_id": df.loc[duplicate_events, "record_id"], "flag": "duplicate_event"}),
        pd.DataFrame({"record_id": sorted(same_customer), "flag": "near_duplicate_same_customer"}),
        pd.DataFrame({"record_id": sorted(one_digit), "flag": "near_duplicate_one_digit_customer"}),
    ], ignore_index=True)
    flagged = record_flags.merge(df[["record_id", "agent_id"]], on="record_id")
    findings["flags"] = {
        flag: {"records": int(len(g)), "agents": int(g["agent_id"].nunique()),
               "max_per_agent": int(g.groupby("agent_id").size().max()) if len(g) else 0}
        for flag, g in flagged.groupby("flag")
    }
    for flag in ["duplicate_event", "near_duplicate_same_customer", "near_duplicate_one_digit_customer"]:
        findings["flags"].setdefault(flag, {"records": 0, "agents": 0, "max_per_agent": 0})

    findings["status_share"] = df["activation_status"].value_counts(normalize=True).round(3).to_dict()
    per_agent = df.groupby("agent_id").size()
    per_agent_day = df.groupby(["agent_id", df["timestamp"].dt.date]).size()
    agent_outliers, findings["outliers_per_agent_total"] = outlier_flags(per_agent)
    day_outliers, findings["outliers_per_agent_day"] = outlier_flags(per_agent_day)
    agent_outliers = agent_outliers.rename(columns={"value": "records"})
    agent_outliers["outlier_days"] = day_outliers[day_outliers["iqr_outlier"]].groupby(level=0).size()
    agent_outliers = agent_outliers.fillna({"outlier_days": 0}).astype({"outlier_days": int}).reset_index()
    findings["agents_with_no_records"] = int((~agents_df["agent_id"].isin(df["agent_id"])).sum())

    findings["rows_out"] = len(df)
    findings["rows_removed"] = findings["rows_in"] - findings["rows_out"]
    return df, findings, record_flags, agent_outliers


def render_report(findings, source, run_id):
    total = findings["outliers_per_agent_total"]
    daily = findings["outliers_per_agent_day"]
    nulls = ", ".join(f"{c}: {n}" for c, n in findings["nulls_per_column"].items())
    invalid = "\n".join(f"| {name.replace('_', ' ')} | {n} |" for name, n in findings["invalid"].items())
    agents = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in findings["agents_table"].items())
    clients = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in findings["clients_table"].items())
    flags = "\n".join(f"| {name.replace('_', ' ')} | {v['records']} | {v['agents']} | {v['max_per_agent']} |"
                      for name, v in findings["flags"].items())
    status = ", ".join(f"{s} {v:.1%}" for s, v in findings["status_share"].items())
    return f"""# Data cleaning report

Generated by `ml/clean_data.py` from `{source}` (run `{run_id}`). No check reads fraud labels.

| | Rows |
|---|---|
| Raw activation records | {findings['rows_in']} |
| Removed: missing agent_id / timestamp / customer_id | {findings['removed_missing_required']} |
| Removed: exact duplicate rows | {findings['removed_exact_duplicate_rows']} |
| Removed: duplicate record_ids | {findings['removed_duplicate_record_ids']} |
| Removed: invalid values, formats or impossible timestamps | {findings['removed_invalid']} |
| **Clean records** | **{findings['rows_out']}** |

## Missing values
Activation records, nulls per column: {nulls}.

## Reference tables
- agents.csv: {agents}.
- clients.csv: {clients}.

## Invalid values, formats and impossible timestamps (rows removed)
| Check | Rows |
|---|---|
{invalid}

## Duplicates and near duplicates (flagged, kept)
Near duplicate = a later record by the same agent for the same client within {NEAR_DUPLICATE_MINUTES} minutes of an earlier one, with the same customer id, or a customer id one digit away. Identical timestamps are counted as duplicate events instead.

| Flag | Records | Agents | Max per agent |
|---|---|---|---|
{flags}

These are kept because resubmitting a customer is one of the behaviours the features measure; removing them would remove signal. Record-level flags are in the run folder (`record_flags.csv`), not in the cleaned data, so they never become model inputs.

## Outliers (flagged, not removed)
| | Min | Median | Max | IQR upper fence | IQR outliers | Robust-z > {ROBUST_Z_THRESHOLD} |
|---|---|---|---|---|---|---|
| Submissions per agent (n={total['n']}) | {total['min']} | {total['median']:.0f} | {total['max']} | {total['iqr_upper_fence']:.1f} | {total['iqr_outliers']} | {total['robust_z_outliers']} |
| Submissions per agent-day (n={daily['n']}) | {daily['min']} | {daily['median']:.0f} | {daily['max']} | {daily['iqr_upper_fence']:.1f} | {daily['iqr_outliers']} | {daily['robust_z_outliers']} |

**Policy: flag, do not delete.** In unsupervised anomaly detection the outliers are the behaviour being detected; deleting them before modelling would delete fraud signal and make the evaluation optimistic. Per-agent flags are in `agent_outliers.csv` in the run folder. Agents with no records after cleaning: {findings['agents_with_no_records']}.

## Failed and pending activations
Status mix: {status}. **Kept, and counted as submissions.** Features measure attempted activations, fake customers are the submissions most likely to fail, and the live backend counts every record. Status is independent of fraud in this synthetic data, so the choice has no effect here and cannot be validated on it.
"""


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Clean raw activation records before feature engineering.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    inputs = [args.data_dir / f for f in ["activation_records.csv", "agents.csv", "clients.csv"]]
    activations_df, agents_df, clients_df = (pd.read_csv(p) for p in inputs)
    clean_df, findings, record_flags, agent_outliers = clean_data(activations_df, agents_df, clients_df)

    clean_path = args.data_dir / "activation_records_clean.csv"
    clean_df.to_csv(clean_path, index=False)
    run_dir = start_run("clean", None, {"near_duplicate_minutes": NEAR_DUPLICATE_MINUTES,
                                        "iqr_multiplier": IQR_MULTIPLIER, "robust_z_threshold": ROBUST_Z_THRESHOLD},
                        inputs + [clean_path])
    record_flags.to_csv(run_dir / "record_flags.csv", index=False)
    agent_outliers.to_csv(run_dir / "agent_outliers.csv", index=False)
    report = render_report(findings, "data/synthetic/activation_records.csv", run_dir.name)
    (run_dir / "data_cleaning_report.md").write_text(report, encoding="utf-8")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")

    print(f"Cleaned {findings['rows_in']} -> {findings['rows_out']} records ({findings['rows_removed']} removed).")
    print("Invalid:", findings["invalid"])
    print("Flags:", findings["flags"])
    print("Agents table:", findings["agents_table"], "| Clients table:", findings["clients_table"])
    print("Outliers per agent:", findings["outliers_per_agent_total"])
    print("Outliers per agent-day:", findings["outliers_per_agent_day"])
    print(f"Saved {clean_path}; run folder {run_dir}")


if __name__ == "__main__":
    main()
