"""
Loads the synthetic CSV data (agents, activation records, feature vectors,
fraud flags) into the PostgreSQL database, using the SQLAlchemy models
defined in db.py.

Run this after db.py has created the tables, and after the data generation,
feature engineering, and model scripts have produced their CSV outputs.
"""

import pandas as pd
from datetime import datetime
from src.db import get_session, Agent, ActivationRecord, FeatureVector, FraudFlag

def load_agents(session):
    df = pd.read_csv("data/synthetic/agents.csv")
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
    df = pd.read_csv("data/synthetic/activation_records.csv")
    for _, row in df.iterrows():
        record = ActivationRecord(
            record_id=row["record_id"],
            agent_id=row["agent_id"],
            timestamp=pd.to_datetime(row["timestamp"]),
            customer_id=row["customer_id"],
            client_id=row["client_id"],
            category=row["category"],
            activation_status=row["activation_status"],
        )
        session.merge(record)
    session.commit()
    print(f"Loaded {len(df)} activation records.")


def load_feature_vectors(session):
    df = pd.read_csv("data/synthetic/feature_vectors.csv")
    for _, row in df.iterrows():
        vector = FeatureVector(
            vector_id=row["vector_id"],
            agent_id=row["agent_id"],
            analysis_period=row["analysis_period"],
            submission_frequency=int(row["submission_frequency"]),
            time_of_day_dist=float(row["time_of_day_dist"]),
            customer_similarity=float(row["customer_similarity"]),
        )
        session.merge(vector)
    session.commit()
    print(f"Loaded {len(df)} feature vectors.")


def load_fraud_flags(session):
    """
    Loads the LOF results as the primary fraud flags, since LOF was
    selected as the best-performing model (Section 3.2.4).
    """
    df = pd.read_csv("data/synthetic/fraud_flags_lof.csv")
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