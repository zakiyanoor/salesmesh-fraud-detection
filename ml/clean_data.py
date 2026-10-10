"""
Data cleaning step for the SalesMesh fraud detection pipeline.

Runs between data generation and feature engineering. It checks the raw
activation records explicitly, removes only what is invalid, and writes a
report of exactly what was checked and found, even when nothing needed
removing.

Checks (none of them read the fraud labels, so cleaning decisions cannot be
influenced by which agents are fraudulent):
1. Schema: every expected column is present.
2. Missing values: nulls per column. Rows missing agent_id, timestamp or
   customer_id are removed (no feature can be computed from them).
3. Duplicates: (a) exact duplicate rows, (b) duplicate record_ids, and
   (c) duplicate events: the same agent, customer and timestamp under
   different record_ids. (a) and (b) are removed as ingestion errors.
   (c) is reported but kept: an agent resubmitting the same customer is
   itself one of the fraud patterns customer_similarity measures, and
   identical timestamps to the second are what a scripted resubmission
   would look like.
4. Validity: timestamps parse and fall inside the analysis window,
   activation_status is one of completed/pending/failed, customer_id matches
   CUST + CUSTOMER_ID_DIGITS digits, agent_id exists in agents.csv. Invalid rows are removed.
5. Statistical outliers: per-agent total submissions and per-agent-day
   submission counts, by the IQR rule (above Q3 + 1.5 * IQR) and by robust
   z-score (|x - median| / (1.4826 * MAD) > 3.5). Outliers are reported but
   NOT removed: in unsupervised anomaly detection the outliers are the very
   thing being detected, so removing them before modelling would remove the
   fraud signal.

Decision: failed and pending activations count toward submission_frequency.
- submission_frequency measures submission behaviour, i.e. attempted
  activations. Fake or duplicate customers are the submissions most likely
  to fail verification, so excluding failed records would hide part of the
  behaviour being detected.
- The live backend pipeline (backend/src/pipeline.py,
  compute_submission_frequency) counts every record regardless of status.
  Counting the same way here keeps offline evaluation consistent with what
  the deployed system computes.
- In this synthetic data activation_status is drawn independently of fraud
  status (85% completed / 10% pending / 5% failed for every agent), so the
  choice cannot change results here and cannot be validated on this data.
  activation_status is kept in the cleaned output so a status-filtered
  variant can be tested on real data.

Usage: python clean_data.py [--data-dir DIR] [--report PATH]
Input:  <data-dir>/activation_records.csv, <data-dir>/agents.csv
Output: <data-dir>/activation_records_clean.csv and a markdown report
        (default: results/data_cleaning_report.md)
"""

import argparse
from pathlib import Path

import pandas as pd

from data_generation import ANALYSIS_END, ANALYSIS_START, CUSTOMER_ID_DIGITS, DEFAULT_OUT_DIR

DEFAULT_REPORT = Path(__file__).resolve().parent / "results" / "data_cleaning_report.md"

EXPECTED_COLUMNS = [
    "record_id", "agent_id", "timestamp", "customer_id", "activation_status", "client_id", "category",
]
REQUIRED_COLUMNS = ["agent_id", "timestamp", "customer_id"]
VALID_STATUSES = {"completed", "pending", "failed"}
CUSTOMER_ID_PATTERN = rf"^CUST\d{{{CUSTOMER_ID_DIGITS}}}$"

IQR_MULTIPLIER = 1.5
ROBUST_Z_THRESHOLD = 3.5


def outlier_summary(values):
    """IQR and robust-z outlier counts for a numeric Series (label-free)."""
    q1, q3 = values.quantile(0.25), values.quantile(0.75)
    iqr_upper = q3 + IQR_MULTIPLIER * (q3 - q1)
    median = values.median()
    mad = (values - median).abs().median()
    robust_z = (values - median).abs() / (1.4826 * mad) if mad > 0 else pd.Series(0.0, index=values.index)
    return {
        "n": len(values),
        "min": values.min(),
        "median": median,
        "max": values.max(),
        "iqr_upper_fence": iqr_upper,
        "iqr_outliers": int((values > iqr_upper).sum()),
        "robust_z_outliers": int((robust_z > ROBUST_Z_THRESHOLD).sum()),
    }


def clean_data(activations_df, agents_df):
    """Returns (clean_df, findings). See the module docstring for what is checked and why."""
    df = activations_df.copy()
    findings = {"rows_in": len(df)}

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

    findings["kept_duplicate_events"] = int(
        df.duplicated(subset=["agent_id", "customer_id", "timestamp"], keep="first").sum()
    )

    df = df.assign(timestamp=pd.to_datetime(df["timestamp"], errors="coerce"))
    window_end = ANALYSIS_END + pd.Timedelta(days=1)
    invalid = {
        "unparseable_timestamp": df["timestamp"].isna(),
        "timestamp_outside_window": df["timestamp"].notna()
        & ((df["timestamp"] < ANALYSIS_START) | (df["timestamp"] >= window_end)),
        "invalid_activation_status": ~df["activation_status"].isin(VALID_STATUSES),
        "malformed_customer_id": ~df["customer_id"].astype(str).str.match(CUSTOMER_ID_PATTERN),
        "unknown_agent_id": ~df["agent_id"].isin(agents_df["agent_id"]),
    }
    findings["invalid"] = {name: int(mask.sum()) for name, mask in invalid.items()}
    any_invalid = pd.concat(invalid.values(), axis=1).any(axis=1)
    findings["removed_invalid"] = int(any_invalid.sum())
    df = df[~any_invalid]

    findings["status_share"] = df["activation_status"].value_counts(normalize=True).round(3).to_dict()
    per_agent = df.groupby("agent_id").size()
    per_agent_day = df.groupby(["agent_id", df["timestamp"].dt.date]).size()
    findings["outliers_per_agent_total"] = outlier_summary(per_agent)
    findings["outliers_per_agent_day"] = outlier_summary(per_agent_day)
    findings["agents_with_no_records"] = int((~agents_df["agent_id"].isin(df["agent_id"])).sum())

    findings["rows_out"] = len(df)
    findings["rows_removed"] = findings["rows_in"] - findings["rows_out"]
    return df, findings


def render_report(findings, source):
    total = findings["outliers_per_agent_total"]
    daily = findings["outliers_per_agent_day"]
    nulls = ", ".join(f"{c}: {n}" for c, n in findings["nulls_per_column"].items())
    invalid = "\n".join(f"  - {name.replace('_', ' ')}: {n}" for name, n in findings["invalid"].items())
    status = ", ".join(f"{s} {v:.1%}" for s, v in findings["status_share"].items())
    return f"""# Data cleaning report

Generated by `ml/clean_data.py` from `{source}`. The checks do not read fraud labels.

| | Rows |
|---|---|
| Raw activation records | {findings['rows_in']} |
| Removed: missing agent_id / timestamp / customer_id | {findings['removed_missing_required']} |
| Removed: exact duplicate rows | {findings['removed_exact_duplicate_rows']} |
| Removed: duplicate record_ids | {findings['removed_duplicate_record_ids']} |
| Removed: invalid values | {findings['removed_invalid']} |
| **Clean records** | **{findings['rows_out']}** |

## What was checked
- **Missing values per column:** {nulls}.
- **Duplicate events kept** (same agent, customer and timestamp, different record_id): {findings['kept_duplicate_events']}. Kept, because resubmitting a customer is a fraud pattern the features measure.
- **Validity checks** (rows failing any check are removed):
{invalid}
- **Agents with no records after cleaning:** {findings['agents_with_no_records']}.

## Statistical outliers (reported, not removed)
| | Min | Median | Max | IQR upper fence | IQR outliers | Robust-z > {ROBUST_Z_THRESHOLD} |
|---|---|---|---|---|---|---|
| Submissions per agent (n={total['n']}) | {total['min']} | {total['median']:.0f} | {total['max']} | {total['iqr_upper_fence']:.1f} | {total['iqr_outliers']} | {total['robust_z_outliers']} |
| Submissions per agent-day (n={daily['n']}) | {daily['min']} | {daily['median']:.0f} | {daily['max']} | {daily['iqr_upper_fence']:.1f} | {daily['iqr_outliers']} | {daily['robust_z_outliers']} |

Outliers are not removed: in unsupervised anomaly detection they are the signal being detected.

## Decision: failed and pending activations
Activation status mix: {status}. **Failed and pending records count toward submission_frequency.** The metric measures submission behaviour (attempts), fake customers are the submissions most likely to fail, and the live backend pipeline counts every record. In this synthetic data status is independent of fraud, so the choice has no effect here and cannot be validated on it.
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clean raw activation records before feature engineering.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    activations_df = pd.read_csv(args.data_dir / "activation_records.csv")
    agents_df = pd.read_csv(args.data_dir / "agents.csv")
    clean_df, findings = clean_data(activations_df, agents_df)

    clean_df.to_csv(args.data_dir / "activation_records_clean.csv", index=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(findings, "data/synthetic/activation_records.csv"), encoding="utf-8")

    print(f"Cleaned {findings['rows_in']} -> {findings['rows_out']} records ({findings['rows_removed']} removed).")
    print(f"Saved to {args.data_dir / 'activation_records_clean.csv'}" + (f"; report at {args.report}" if args.report else ""))


if __name__ == "__main__":
    main()
