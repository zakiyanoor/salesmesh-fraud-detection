# Setup and commands

Moved from the root `README.md` (issue #26). Architecture: `ARCHITECTURE.md`.

## Backend setup

All backend commands run from inside `backend/`. The virtual environment lives at the repository root.

```bash
python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux: source venv/bin/activate)
cd backend
pip install -r requirements.txt   # backend/requirements.txt: the API, database, scheduler, reports, and the frozen ML code it imports
```

Copy `backend/.env.example` to `backend/.env` and fill in the empty values:
- **Required:** `FLASK_SECRET_KEY`, `DB_PASSWORD`, and the three `DEMO_*_PASSWORD` values (at least 12 characters each).
- **`APP_ENV`:** the example sets `development`. If it is unset, the backend runs as `production`: no debug, `Secure` cookies and no CORS origin.
- **Optional:** the other settings (CORS origins, the cookie flags, a 60-minute session lifetime, the database and the scheduler) are explained in the file.
- **Never commit `backend/.env`.**

Then, from `backend/`:

```bash
python -m src.migrate      # create the database, tables and columns if missing (safe to repeat)
python -m src.load_data    # reload the five v3 files from ml/data/synthetic (hash and count checked; never labels.csv)
python -m src.auth         # demo accounts analyst_01, compliance_01, admin_01 (APP_ENV development/test; DEMO_*_PASSWORD)
python -m src.pipeline     # one detection run with the frozen lof_v3_4f model
python -m src.scheduler    # detection now and then every DETECTION_INTERVAL_MINUTES
python -m src.api          # the API on port 5000
pytest                     # tests, on the separate salesmesh_fraud_detection_test database
```

## Frontend

From `frontend/`: `npm ci`, then `npm run dev` (http://localhost:5173, with `/api` proxied to the backend) and `npm test`. Details: `../frontend/README.md`.

If some frontend tests time out on a busy computer, close heavy programs or run `npx vitest run --maxWorkers=6` (see `../backend/CHANGES.md`).

## Reproduce, score, retrain

From `ml/`, using the repository's virtual environment (`venv\Scripts\activate`), after `pip install -r requirements.txt` (the ML pipeline's own dependencies, `ml/requirements.txt`):

```bash
python run_pipeline.py                 # Steps 1-10: generate, clean, split, EDA, features, baselines, models, selection, explanations, system checks
python run_pipeline.py --dry-run       # list the steps without running them
python -m pytest -q tests              # ML tests
python retrain.py --features new_feature_vectors.csv   # refit on new unlabelled agents; cutoff from the validated alert rate
```

Scoring with the frozen model, in Python from `ml/`:

```python
from scoring import load_bundle, score_agents
bundle = load_bundle("runs/20261013-100433_explain/scoring_bundle.joblib")
scores = score_agents(bundle, features)  # agent_id, period, score, flag, threshold, model_version, top_features, reason
```

Step 11 (`final_evaluation.py`) has already been run and refuses to run again. The stress test (`stress_test.py`) has also been run once and refuses to run again. Details: `ml/README.md`.
