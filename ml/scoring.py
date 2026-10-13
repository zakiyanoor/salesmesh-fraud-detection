"""
Scoring with a saved bundle (used from Step 10 on).

A bundle is a joblib dict: the detector artifact (name, feature_columns,
scaler, model), model_version, operating_point (with "threshold"),
reference_stats (training median and IQR per feature) and explanation_method.
Any detector whose model has score_samples works without code changes, and the
threshold is read from the bundle, never from code.

Output schema (OUTPUT_COLUMNS): agent_id, analysis_period_start,
analysis_period_end, score, flag, threshold, model_version, top_features, reason.
top_features is filled for every agent; reason only for flagged agents
(unflagged rows carry NOT_FLAGGED_REASON).
"""

import joblib
import numpy as np
import pandas as pd

from detectors import Detector
from explain import reasons, top_features

OUTPUT_COLUMNS = ["agent_id", "analysis_period_start", "analysis_period_end", "score", "flag", "threshold",
                  "model_version", "top_features", "reason"]
NOT_FLAGGED_REASON = "not flagged"


def load_bundle(path):
    return joblib.load(path)


def detector_from(bundle):
    return Detector(bundle["name"], list(bundle["feature_columns"]), bundle["scaler"], bundle["model"])


def score_agents(bundle, features):
    detector = detector_from(bundle)
    threshold = float(bundle["operating_point"]["threshold"])
    scores = detector.score(features)
    flags = scores >= threshold
    reference = bundle["reference_stats"]
    out = pd.DataFrame({
        "agent_id": features["agent_id"].values,
        "analysis_period_start": features["analysis_period_start"].values,
        "analysis_period_end": features["analysis_period_end"].values,
        "score": scores, "flag": flags, "threshold": threshold, "model_version": bundle["model_version"],
        "top_features": top_features(reference, detector.columns, features), "reason": NOT_FLAGGED_REASON,
    })
    if flags.any():
        out.loc[flags, "reason"] = reasons(reference, detector.columns, features[np.asarray(flags)])
    return out[OUTPUT_COLUMNS]
