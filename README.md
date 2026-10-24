# SalesMesh Fraud Detection System

[![CI](https://github.com/zakiyanoor/salesmesh-fraud-detection/actions/workflows/ci.yml/badge.svg)](https://github.com/zakiyanoor/salesmesh-fraud-detection/actions/workflows/ci.yml)

Flags fraudulent and colluding sales agents on the SalesMesh onboarding platform for review by an analyst (module U-CS 56, AI Fraud Detection). A flag is a request for human review, not a decision. All data is synthetic.

## The system is a hybrid

The system flags an agent when the frozen anomaly model `lof_v3_4f` **or** the duplicate activation rule fires; each flag records its source (`flag_source` ML, Rule or Both). The two catch different fraud: the rule finds weak and duplicate fraud the model misses, and the model finds sequential fraud the rule never flags.

| | Test set, seed 42 (19 fraud of 150) | 10 other datasets (seeds 101–110), mean |
|---|---|---|
| **Hybrid (model or rule)** | recall **1.000** (19/19), precision 0.655, 29 flagged | recall **0.979**, precision 0.805 |
| Model alone | recall 0.789, precision 0.600, PR AUC 0.845 | recall 0.689, precision 0.748, PR AUC 0.811 |
| Rule alone | recall 0.842, precision 1.000 | recall 0.811, precision 1.000 |

- The hybrid was a **pre-declared secondary analysis**; the pre-registered primary result is the model alone.
- The hybrid's PR AUC is computed on a 0/1 flag, so it is not shown beside the score-based ones.
- The rule's precision of 1.000 is a ceiling that comes from how the synthetic data was generated.
- **Stress test:** after a shift in the data, the model degraded more than the rule, though not significantly. Under rule-aware evasion, the hybrid's recall fell to 0.623 (the model alone), and duplicate and weak fraud went undetected. See `ml/results/STRESS_TEST_RESULTS.md`.

**How it works:**
- **Model:** a Local Outlier Factor on four behaviour features (`submission_frequency`, `time_of_day_entropy`, `customer_similarity`, `collusion_score`). No label is used in training.
- **Data:** 1000 agents (130 fraud) and 135,494 activations, split 70/15/15 by agent.
- **Choices:** made on validation under rules written in advance. The test set was read once (`ml/results/FREEZE.md`).

## Limitations

- **Synthetic data only;** these results cannot show performance on real SalesMesh agents.
- **Weak fraud** (fraudulent 10% to 25% of the time) is missed by the model and caught only by the rule.
- **Small evaluation sets** (19 to 20 fraud agents), so the intervals are wide.
- **Scores and ranks are not probabilities;** the cutoff assumes a 5:1 cost of a miss to a false alarm.
- **Process disclosures:** label-aware generator changes and a post hoc rule amendment are listed in `ml/results/DEVIATIONS_FROM_PROPOSAL.md`.

## Quick start

```bash
python -m venv venv && venv\Scripts\activate
cd backend && pip install -r requirements.txt   # then copy .env.example to .env and fill it in
python -m src.migrate && python -m src.load_data && python -m src.auth && python -m src.pipeline
python -m src.api                               # API on port 5000
cd ../frontend && npm ci && npm run dev         # dashboard on http://localhost:5173
```

Full setup, every command, and how to reproduce, score and retrain: `docs/SETUP.md`.

## Documentation

| Topic | Where |
|---|---|
| Model and data cards | `ml/MODEL_CARD.md`, `ml/DATA_CARD.md` |
| Final test, stability, stress test | `ml/results/FINAL_TEST_RESULTS.md`, `ml/results/STRESS_TEST_RESULTS.md` |
| ML pipeline | `ml/README.md` |
| Architecture, roles, repository layout | `docs/ARCHITECTURE.md` |
| API reference; dashboard | `docs/API.md`; `docs/FRONTEND.md` |
| Changes | `backend/CHANGES.md`, `ml/results/CHANGES.md` |

## Licence

Copyright (c) 2026 Zakiya Noor. All rights reserved. See `LICENSE`.
