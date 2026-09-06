"""
Database models and connection setup for the SalesMesh fraud detection system.

Defines the five entities from the ERD (Section 3.4.3):
Agents, Activation Records, Feature Vectors, Fraud Flags, Review Decisions.

Uses SQLAlchemy as the ORM (Section 3.5.4), connecting to PostgreSQL.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

load_dotenv()

DB_USER = "postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "salesmesh_fraud_detection"

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# --- Entity: Agents ---
class Agent(Base):
    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True)
    registration_timestamp = Column(DateTime)
    region = Column(String)

    activation_records = relationship("ActivationRecord", back_populates="agent")
    feature_vectors = relationship("FeatureVector", back_populates="agent")


# --- Entity: Activation Records ---
class ActivationRecord(Base):
    __tablename__ = "activation_records"

    record_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"))
    timestamp = Column(DateTime)
    customer_id = Column(String)
    activation_status = Column(String)

    agent = relationship("Agent", back_populates="activation_records")


# --- Entity: Feature Vectors ---
class FeatureVector(Base):
    __tablename__ = "feature_vectors"

    vector_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"))
    analysis_period = Column(String)
    submission_frequency = Column(Integer)
    time_of_day_dist = Column(Float)
    customer_similarity = Column(Float)

    agent = relationship("Agent", back_populates="feature_vectors")
    fraud_flag = relationship("FraudFlag", back_populates="feature_vector", uselist=False)


# --- Entity: Fraud Flags ---
class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    flag_id = Column(String, primary_key=True)
    vector_id = Column(String, ForeignKey("feature_vectors.vector_id"))
    suspicion_score = Column(Float)
    flag_status = Column(String)
    model_version = Column(String)

    feature_vector = relationship("FeatureVector", back_populates="fraud_flag")
    review_decision = relationship("ReviewDecision", back_populates="fraud_flag", uselist=False)


# --- Entity: Review Decisions ---
class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    decision_id = Column(String, primary_key=True)
    flag_id = Column(String, ForeignKey("fraud_flags.flag_id"))
    reviewer_id = Column(String)
    decision_outcome = Column(String)
    decision_timestamp = Column(DateTime, default=datetime.utcnow)

    fraud_flag = relationship("FraudFlag", back_populates="review_decision")


def create_all_tables():
    """Creates all five tables in the database if they don't already exist."""
    Base.metadata.create_all(engine)
    print("All tables created successfully.")


def get_session():
    """Returns a new database session for use in scripts."""
    return SessionLocal()


if __name__ == "__main__":
    create_all_tables()