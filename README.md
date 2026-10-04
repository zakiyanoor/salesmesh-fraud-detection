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

## Repository layout
- `ml/`: offline ML work: synthetic data generation (`data_generation.py`), feature engineering (`feature_engineering.py`), the Isolation Forest / LOF model comparison scripts (`model.py`, `model_lof.py`), their outputs in `ml/data/synthetic/`, and evaluation results in `ml/results/`
- `backend/`: Flask API, auth, database layer, and the live detection pipeline (`src/pipeline.py`, `src/detector.py`)
- `frontend/`: React dashboard

## Setup

### ML

The ML scripts use the same virtual environment and `backend/requirements.txt`. Run them from inside `ml/` (data paths such as `data/synthetic/...` are relative to it), in this order:

```bash
cd ml
python data_generation.py      # -> data/synthetic/agents.csv, activation_records.csv
python feature_engineering.py  # -> data/synthetic/feature_vectors.csv
python model.py                # Isolation Forest baseline -> data/synthetic/fraud_flags.csv
python model_lof.py            # LOF -> data/synthetic/fraud_flags_lof.csv
```

### Backend

All backend commands run from inside `backend/`. The virtual environment lives at the repo root.

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
python -m src.load_data    # load the CSVs from ml/data/synthetic/ into PostgreSQL
python -m src.pipeline     # run the detection pipeline
```
