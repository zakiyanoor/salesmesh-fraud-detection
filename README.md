# SalesMesh Fraud Detection System

AI-based anomaly detection system identifying fraudulent and colluding sales agents on the SalesMesh onboarding platform.

## Problem
SalesMesh pays agents commission per customer activation, creating incentive for fraud: fake customers, duplicate submissions, and multi-agent collusion.

## Approach
Unsupervised anomaly detection (Local Outlier Factor, benchmarked against Isolation Forest) scoring agents on four behavioural features: submission frequency, time-of-day distribution, customer similarity, and cross-agent collusion overlap.

## Architecture
- **Data**: PostgreSQL (Agents, Activation Records, Feature Vectors, Fraud Flags, Review Decisions, Administrators)
- **Backend**: Flask REST API, session-based auth, SQLAlchemy ORM
- **Detection**: Adapter-pattern `FraudDetector` (swappable model), scheduled via APScheduler
- **Frontend**: React + MUI dashboard

## Setup

### Backend

All backend commands run from inside `backend/` (data paths such as `data/synthetic/...` are relative to it). The virtual environment lives at the repo root.

```bash
python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux: source venv/bin/activate)
cd backend
pip install -r requirements.txt
```

Create `backend/.env` with `DB_PASSWORD` and `FLASK_SECRET_KEY`.

From `backend/`:

```bash
pytest                     # run tests
python -m src.pipeline     # run the detection pipeline
```
