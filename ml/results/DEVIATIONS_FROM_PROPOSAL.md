Deviations from the proposal (Chapters 1 to 3)

What the delivered ML work (U-CS 56, AI Fraud Detection) does differently from Chapters 1 to 3, each with a one-line reason. The proposal's wording is quoted from Chapters 1 to 3 where it matters.

1. SMOTE was not used

Chapter 3 (Section 3.2.1, Data Acquisition) proposed generating synthetic fraud cases by applying SMOTE to the behavioural feature vectors. Reason: the detectors are unsupervised and never see a label, so oversampling the labelled minority class would not change what they learn. Imbalance is handled by a stratified split, PR AUC as the main metric, and a cost-based cutoff (MODEL_CARD.md, "Class imbalance handling").

2. The data is fully synthetic

No real SalesMesh data was used: agents, customers, clients and activations all come from ml/data_generation.py (seed 42, 1000 agents, 13% fraud). Reason: no real labelled SalesMesh activation data with confirmed fraud exists for this project; synthetic data with known labels is the only way to measure detection.

3. The four chosen features differ from Chapter 3

Chapter 3 (Section 3.2.3, Model Training) lists four features:

submission frequency over rolling time windows;
the time-of-day entropy of submissions;
the mean pairwise similarity of customer identifiers submitted by the same agent;
the ratio of an agent's submission volume to the platform average for their region and vertical.

Section 3.2.2 (Data Preprocessing) describes only the first three, so Chapter 3 is not consistent with itself and should be corrected when it is redone.

Used in the delivered model:

submission_frequency: busiest 24-hour window;
time_of_day_entropy;
customer_similarity: mean digit-position similarity of customer ids over all pairs of submissions;
collusion_score: share of customers shared with other agents.

Differences:

collusion_score was added. It is not in Chapter 3.
The volume ratio (volume_vs_peers, with peers defined by primary category and former region) was tested as a candidate and not chosen, because it added nothing in the ablation (differences within noise).

Reason:

collusion between agents is a fraud pattern in Chapter 2, and a per-agent behaviour feature cannot see it, so a feature built on shared customers was needed;
the chosen four came from validation results under a selection rule written in advance.
4. Split: 70/15/15 with a validation set, instead of 80/20

Reason: an 80/20 split has nowhere to choose models and cutoffs except the test set. In v2 that led to a deployment choice made after seeing test results. A validation set keeps the test set for one final reading. The split is at agent level, stratified by fraud pattern.

5. The threshold is selected on validation, not calibrated

Chapter 3 (Section 3.6) refers to a "calibrated threshold". The delivered cutoff (1.445) minimises expected cost at 5:1 on validation agents, and is stored in operating_point.json. Reason: an unsupervised anomaly score has no probability scale. The scores are not calibrated probabilities, and they are not presented as such.

6. React instead of Streamlit

Chapter 3 (Section 3.5.3) proposed a Streamlit dashboard. The analyst interface is a React app. Reason: the dashboard needs role based screens, an audit log, report downloads and a mobile friendly layout. React with a component library supports these and responsive design better than Streamlit. The ML side supplies scores, flags and reasons through the backend.

7. Analysis window of 1 to 30 August 2026

The data covers one 30-day window, 2026-08-01 to 2026-08-30 (Africa/Nairobi). Reason: Chapter 3 refers to an analysis period without giving its length. One month gives each agent enough activations (about 135 on average) to compute the features, and keeps the data small enough to regenerate and test repeatedly. It is a synthetic window, not a real period.

8. Address components are not in the data

Chapter 3 (Section 3.2.2) refers to identifiers or address components. In the delivered data, customers have ids only, with no names, phone numbers or addresses. Reason:

address matching needs realistic address data that could not be generated credibly;
leaving it out also avoids handling personal data.

Customer similarity is therefore measured on identifiers alone.

9. Wording of objectives iii and iv

Chapter 1 (Section 1.3.1) currently reads:

iii. "To develop a machine learning-based anomaly detection system using Isolation Forest and Local Outlier Factor for sales agent fraud on the SalesMesh onboarding platform." This is word for word the same as the general objective, so it should be reworded to describe a distinct task, for example the development of the feature pipeline, detectors and scoring.
iv. "To test the performance of the developed anomaly detection system against SalesMesh activation data using standard evaluation metrics." This should say synthetic SalesMesh activation data.

Reason: the delivered work detects anomalies in synthetic activation records, so the objectives should name that data source.

10. Weak fraud is not detected

The model catches none of the weak fraud agents (0 of 4 on test; recall about 0.09 in cross-validation). Reason: weak fraud agents make only 10% to 25% fraudulent submissions and otherwise behave normally, so they are not anomalous on per-agent behaviour features. The acceptance criteria set no recall target for this pattern.

11. The duplicate rule baseline and the union result

A rule baseline not in the proposal, duplicate_activation_rule, was added. It flags an agent if any (customer, client) pair it used is also used by another agent, or is repeated after a completed activation. Its union with the model was reported as a pre-declared secondary analysis.

On test: the rule scored PR AUC 0.862 with precision 1.000; the union had recall 1.000 and precision 0.655.
Reason it was added: it shows how much a simple integrity rule catches, the weak fraud the model misses in particular.
Limit: its perfect precision depends on the generator making rules R1 and R2 absolute for honest agents, so it is a reference ceiling, not a real-world estimate.
The primary result is the model alone.
Disclosures
The acceptance criteria were drafted after the default validation results had been seen, on the earlier (v3a) data, and before any test result.
The selection rule was amended post hoc (2026-10-11), on validation only, after the original tie rule chose a weak candidate. The tie order between LOF and Isolation Forest is recorded in selection_notes.md.
The generator was changed after labelled summaries had been seen: four label-aware changes, plus the integrity fix (change 5).
The four label-aware changes: v2 repeat-share widening; v3 Step 1 customer id length; Step 1B popular customers and weak rings; Step 1C removal of hard limits.
The integrity fix (2026-10-13) came after validation results had been seen.
Details: DATA_CARD.md.
The supervisor's review of the acceptance criteria was pending at the time of the test, because the supervisor was away. The criteria were applied exactly as hashed in FREEZE.md.
v2 was deployed post hoc: the v2 switch of the live detector to Isolation Forest was decided after seeing test results.