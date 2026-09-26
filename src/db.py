"""
Database models and connection setup for the SalesMesh fraud detection system.

Defines the five entities from the ERD (Section 3.4.3):
Agents, Activation Records, Feature Vectors, Fraud Flags, Review Decisions,
plus the Admin Action Log audit trail.

Uses SQLAlchemy as the ORM (Section 3.5.4), connecting to PostgreSQL.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Column, String, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, validates
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

DECISION_PENDING = "pending_confirmation"
DECISION_CONFIRMED = "confirmed"
DECISION_STATUSES = (DECISION_PENDING, DECISION_CONFIRMED)


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
    # Pass-through context from other SalesMesh modules (client management,
    # catalogue) -- this service doesn't own them and never treats them as
    # fraud features (see FEATURE_COLUMNS in detector.py). Nullable: records
    # written before these columns existed have no value.
    client_id = Column(String)
    category = Column(String)

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
    # Fraction of the agent's customers also served by other agents. Nullable:
    # vectors written before this feature existed have no value.
    collusion_score = Column(Float)

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
    # Dual control: a fraud_analyst proposes the decision, and it only takes
    # effect once a different admin with the compliance_officer role confirms it.
    status = Column(String, nullable=False, default=DECISION_PENDING)
    confirmed_by = Column(String)

    fraud_flag = relationship("FraudFlag", back_populates="review_decision")

    @validates("status")
    def validate_status(self, key, value):
        if value not in DECISION_STATUSES:
            raise ValueError(f"status must be one of {DECISION_STATUSES}, got {value!r}")
        return value


# --- Audit trail: Admin Action Log ---
class AdminActionLog(Base):
    __tablename__ = "admin_action_log"

    log_id = Column(String, primary_key=True)
    admin_id = Column(String, nullable=False)
    # e.g. "login", "logout", "propose_decision", "confirm_decision"
    action = Column(String, nullable=False)
    target_agent_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


def migrate_schema():
    """
    Adds columns introduced after a table was first created.

    Base.metadata.create_all() only creates missing tables; it never alters an
    existing one, so a new model column needs an explicit ALTER. Every
    statement here must be idempotent (ADD COLUMN IF NOT EXISTS) so it is safe
    to run on every start.
    """
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE feature_vectors ADD COLUMN IF NOT EXISTS collusion_score DOUBLE PRECISION"
        ))
        conn.execute(text(
            "ALTER TABLE activation_records ADD COLUMN IF NOT EXISTS client_id VARCHAR"
        ))
        conn.execute(text(
            "ALTER TABLE activation_records ADD COLUMN IF NOT EXISTS category VARCHAR"
        ))
        # Decisions recorded before dual control existed were never confirmed
        # by a compliance officer, so they start out pending rather than being
        # silently treated as confirmed.
        conn.execute(text(
            "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS status VARCHAR "
            f"NOT NULL DEFAULT '{DECISION_PENDING}'"
        ))
        conn.execute(text(
            "ALTER TABLE review_decisions ADD COLUMN IF NOT EXISTS confirmed_by VARCHAR"
        ))
        # admin_action_log is a new table, so create_all() creates it; nothing
        # to ALTER here.


def create_all_tables():
    """Creates all tables if they don't already exist, then applies column migrations."""
    Base.metadata.create_all(engine)
    migrate_schema()
    print("All tables created successfully.")


def get_session():
    """Returns a new database session for use in scripts."""
    return SessionLocal()


if __name__ == "__main__":
    create_all_tables()