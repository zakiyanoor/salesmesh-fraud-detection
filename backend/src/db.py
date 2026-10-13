"""
Database models and connection setup for the SalesMesh fraud detection system.

Defines the five entities from the ERD (Section 3.4.3):
Agents, Activation Records, Feature Vectors, Fraud Flags, Review Decisions,
plus the Admin Action Log audit trail, and the v3 tables: clients,
agent_identity (fictional personal data, never a model input), agent_categories,
agent_scores and duplicate_evidence (one row set per detection run),
detection_runs (scheduler status) and data_loads (loader provenance).

DB_NAME (default salesmesh_fraud_detection) and the other DB_* settings come
from the environment, so the tests can use their own database.

Uses SQLAlchemy as the ORM (Section 3.5.4), connecting to PostgreSQL.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, text, Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, JSON, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, validates
from datetime import datetime

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "salesmesh_fraud_detection")

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
    # Snapshot taken after the analysis window, for administrative reasons
    # unrelated to fraud; never a model input.
    account_status = Column(String)

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
    quality_score = Column(Integer)
    commission_kes = Column(Integer)

    agent = relationship("Agent", back_populates="activation_records")


# --- Entity: Feature Vectors ---
class FeatureVector(Base):
    __tablename__ = "feature_vectors"

    vector_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"))
    analysis_period = Column(String)
    submission_frequency = Column(Integer)
    # Holds the v3 time_of_day_entropy (same formula as v2); the column name is
    # kept so the existing API fields and the frontend keep working.
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
    # The actor: an admin_id, "anonymous" (not logged in) or "system:<model_version>".
    admin_id = Column(String, nullable=False)
    # e.g. "login", "login_failure", "access_denied", "propose_decision", "ai_flag"
    action = Column(String, nullable=False)
    target_agent_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    category = Column(String)
    actor_type = Column(String, default="user")
    details = Column(Text)
    request_ip = Column(String)


# --- v3 reference and context tables (loaded from ml/data/synthetic) ---
class Client(Base):
    __tablename__ = "clients"

    client_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    commission_per_activation_kes = Column(Integer, nullable=False)


class AgentIdentity(Base):
    """Fictional, randomly generated identity. Never a model input; masked in every API response."""
    __tablename__ = "agent_identity"

    agent_id = Column(String, ForeignKey("agents.agent_id"), primary_key=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False, unique=True)
    national_id_number = Column(String, nullable=False, unique=True)


class AgentCategory(Base):
    __tablename__ = "agent_categories"

    agent_id = Column(String, ForeignKey("agents.agent_id"), primary_key=True)
    category = Column(String, primary_key=True)
    certification_status = Column(String, nullable=False)
    certified_at = Column(DateTime, nullable=False)


# --- v3 detection results ---
FLAG_SOURCES = ("ML", "Rule", "Both", "None")
DUPLICATE_REASONS = ("shared customer", "repeat after completed")


class DetectionRun(Base):
    __tablename__ = "detection_runs"

    run_id = Column(String, primary_key=True)
    trigger = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime)
    model_version = Column(String)
    threshold = Column(Float)
    agents_scored = Column(Integer)
    flagged_count = Column(Integer)
    rule_flagged_count = Column(Integer)
    both_count = Column(Integer)
    error = Column(Text)


class AgentScore(Base):
    __tablename__ = "agent_scores"
    __table_args__ = (UniqueConstraint("run_id", "agent_id"),)

    score_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("detection_runs.run_id"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    flagged = Column(Boolean, nullable=False)
    rule_flagged = Column(Boolean, nullable=False)
    duplicate_pairs = Column(Integer, nullable=False)
    flag_source = Column(String, nullable=False)
    top_features = Column(String)
    reasons = Column(Text)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @validates("flag_source")
    def validate_flag_source(self, key, value):
        if value not in FLAG_SOURCES:
            raise ValueError(f"flag_source must be one of {FLAG_SOURCES}, got {value!r}")
        return value


class DuplicateEvidence(Base):
    __tablename__ = "duplicate_evidence"

    evidence_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("detection_runs.run_id"), nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    customer_id = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    other_agent_id = Column(String)
    reason = Column(String, nullable=False)
    record_ids = Column(Text, nullable=False)

    @validates("reason")
    def validate_reason(self, key, value):
        if value not in DUPLICATE_REASONS:
            raise ValueError(f"reason must be one of {DUPLICATE_REASONS}, got {value!r}")
        return value


class DataLoad(Base):
    __tablename__ = "data_loads"

    load_id = Column(String, primary_key=True)
    loaded_at = Column(DateTime, nullable=False)
    file_hashes = Column(JSON, nullable=False)
    row_counts = Column(JSON, nullable=False)


AUDIT_CATEGORIES = ("authentication", "authorization", "ai_decision", "review", "report", "admin")
AUDIT_COLUMNS = {"category": "VARCHAR", "actor_type": "VARCHAR", "details": "TEXT", "request_ip": "VARCHAR"}
APPEND_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION admin_action_log_append_only() RETURNS trigger AS $fn$
BEGIN
    IF current_setting('salesmesh.audit_maintenance', true) = 'on' THEN
        RETURN COALESCE(NEW, OLD);
    END IF;
    RAISE EXCEPTION 'admin_action_log is append only: % is not allowed', TG_OP;
END
$fn$ LANGUAGE plpgsql
"""


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
        # v3 (issue #4): context columns from ml/data/synthetic.
        conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS account_status VARCHAR"))
        conn.execute(text("ALTER TABLE activation_records ADD COLUMN IF NOT EXISTS quality_score INTEGER"))
        conn.execute(text("ALTER TABLE activation_records ADD COLUMN IF NOT EXISTS commission_kes INTEGER"))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_activation_records_agent_id ON activation_records (agent_id)"
        ))
        # Issue #18: audit log columns, a backfill for older rows, and the
        # append-only guard. The guard lets only a transaction that sets
        # salesmesh.audit_maintenance (this migration) change existing rows.
        for column, kind in AUDIT_COLUMNS.items():
            conn.execute(text(f"ALTER TABLE admin_action_log ADD COLUMN IF NOT EXISTS {column} {kind}"))
        conn.execute(text("SET LOCAL salesmesh.audit_maintenance = 'on'"))
        conn.execute(text(
            "UPDATE admin_action_log SET actor_type = COALESCE(actor_type, 'user'), category = CASE "
            "WHEN action IN ('login', 'logout', 'login_failure') THEN 'authentication' "
            "WHEN action IN ('propose_decision', 'confirm_decision') THEN 'review' "
            "WHEN action = 'access_denied' THEN 'authorization' ELSE 'admin' END "
            "WHERE category IS NULL OR actor_type IS NULL"
        ))
        conn.execute(text(APPEND_ONLY_FUNCTION))
        for name, timing in (("admin_action_log_append_only", "BEFORE UPDATE OR DELETE ON admin_action_log FOR EACH ROW"),
                             ("admin_action_log_no_truncate", "BEFORE TRUNCATE ON admin_action_log FOR EACH STATEMENT")):
            conn.execute(text(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{name}') THEN "
                f"CREATE TRIGGER {name} {timing} EXECUTE FUNCTION admin_action_log_append_only(); END IF; END $$"
            ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_admin_action_log_timestamp ON admin_action_log (timestamp)"
        ))


def create_all_tables():
    """Creates all tables if they don't already exist, then applies column migrations."""
    import src.auth  # noqa: F401  (registers the administrators table on Base)

    Base.metadata.create_all(engine)
    migrate_schema()
    print("All tables created successfully.")


def create_database_if_missing(name=DB_NAME):
    """Creates the PostgreSQL database `name` if it does not exist (connects to the server's postgres db)."""
    server = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres", isolation_level="AUTOCOMMIT"
    )
    try:
        with server.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
            return not exists
    finally:
        server.dispose()


def get_session():
    """Returns a new database session for use in scripts."""
    return SessionLocal()


if __name__ == "__main__":
    create_all_tables()