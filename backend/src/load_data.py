"""
Loads the synthetic CSV data (agents, activation records, feature vectors,
fraud flags) into the PostgreSQL database, using the SQLAlchemy models
defined in db.py.

Run this after db.py has created the tables, and after the data generation,
feature engineering, and model scripts have produced their CSV outputs.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from src.db import get_session, Agent, ActivationRecord, FeatureVector, FraudFlag

# The CSVs are produced by the scripts in ml/ (repo root), not by the backend.
SYNTHETIC_DATA_DIR = Path(__file__).resolve().parents[2] / "ml" / "data" / "synthetic"

def load_agents(session):
    df = pd.read_csv(SYNTHETIC_DATA_DIR / "agents.csv")
    for _, row in df.iterrows():
        agent = Agent(
            agent_id=row["agent_id"],
            registration_timestamp=pd.to_datetime(row["registration_timestamp"]),
            region=row["region"],
        )
        session.merge(agent)
    session.commit()
    print(f"Loaded {len(df)} agents.")


def load_activation_records(session):
    df = pd.read_csv(SYNTHETIC_DATA_DIR / "activation_records.csv")
    for _, row in df.iterrows():
        record = ActivationRecord(
            record_id=row["record_id"],
            agent_id=row["agent_id"],
            timestamp=pd.to_datetime(row["timestamp"]),
            customer_id=row["customer_id"],
            activation_status=row["activation_status"],
            client_id=row.get("client_id"),
            category=row.get("category"),
        )
        session.merge(record)
    session.commit()
    print(f"Loaded {len(df)} activation records.")


def load_feature_vectors(session):
    df = pd.read_csv(SYNTHETIC_DATA_DIR / "feature_vectors.csv")
    for _, row in df.iterrows():
        vector = FeatureVector(
            vector_id=row["vector_id"],
            agent_id=row["agent_id"],
            analysis_period=row["analysis_period"],
            submission_frequency=int(row["submission_frequency"]),
            time_of_day_dist=float(row["time_of_day_dist"]),
            customer_similarity=float(row["customer_similarity"]),
            collusion_score=float(row["collusion_score"]),
        )
        session.merge(vector)
    session.commit()
    print(f"Loaded {len(df)} feature vectors.")


def load_fraud_flags(session):
    """
    Loads the Isolation Forest flags (ml/model.py) as the fraud flags. They
    are produced by the same artifact the live detector loads
    (ml/models/isolation_forest_v2.joblib), so a detection cycle over the
    loaded records reproduces them.
    """
    df = pd.read_csv(SYNTHETIC_DATA_DIR / "fraud_flags.csv")
    for _, row in df.iterrows():
        flag = FraudFlag(
            flag_id=row["flag_id"],
            vector_id=row["vector_id"],
            suspicion_score=float(row["suspicion_score"]),
            flag_status=row["flag_status"],
            model_version=row["model_version"],
        )
        session.merge(flag)
    session.commit()
    print(f"Loaded {len(df)} fraud flags.")


def main():
    session = get_session()
    try:
        print("Loading data into PostgreSQL...")
        load_agents(session)
        load_activation_records(session)
        load_feature_vectors(session)
        load_fraud_flags(session)
        print("\nAll data loaded successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error during load, rolled back: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()