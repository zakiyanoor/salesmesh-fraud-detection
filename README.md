# SalesMesh Fraud Detection System

AI-based anomaly detection system identifying fraudulent and colluding sales agents on the SalesMesh onboarding platform.

## Problem
SalesMesh pays agents commission per customer activation, creating incentive for fraud: fake customers, duplicate submissions, and multi-agent collusion.

## Approach
Unsupervised anomaly detection (Local Outlier Factor, benchmarked against Isolation Forest) scoring agents on four behavioural features: submission frequency, time-of-day distribution, customer similarity, and cross-agent collusion overlap.

## Architecture
- **Data**: PostgreSQL (Agents, Activation Records, Feature Vectors, Fraud Flags, Review Decisions, Administrators)
- **Backend**: Flask REST API, session-based auth, SQLAlchemy ORM
- **Detection**: Isolation Forest trained offline in `ml/` (`ml/model.py`) and saved to `ml/models/isolation_forest_v2.joblib`; the backend's `FraudDetector` only loads that artifact and scores agents (no refitting). Detection cycles are scheduled via APScheduler
- **Frontend**: React + MUI dashboard

## Repository layout
- `ml/`: offline ML pipeline: synthetic data generation, cleaning, feature engineering, train/test split, Isolation Forest / LOF / baseline models, and evaluation (data in `ml/data/synthetic/`, results in `ml/results/`)
- `backend/`: Flask API, auth, database layer, and the live detection pipeline (`src/pipeline.py`, `src/detector.py`)
- `frontend/`: React dashboard

## Setup

### ML

The ML scripts use the same virtual environment and `backend/requirements.txt`. Run them from inside `ml/`, in this order:

```bash
cd ml
python data_generation.py      # synthetic agents + activation records (seed 42)
python clean_data.py           # validity/duplicate/null/outlier checks -> results/data_cleaning_report.md
python feature_engineering.py  # per-agent feature vectors
python split.py                # stratified 80/20 train/test split of agents
python model.py                # Isolation Forest, fitted on training agents only
python model_lof.py            # LOF (novelty mode), fitted on training agents only
python baseline.py             # submission-frequency rule baseline
python run_experiments.py      # full pipeline over seeds 1-5 -> results/multi_seed_results.csv
python evaluate.py             # final evaluation on the held-out test agents
```

Results and limitations are written up in `ml/results/evaluation_summary.md`.

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
