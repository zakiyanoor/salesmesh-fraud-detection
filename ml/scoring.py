"""
Scoring with a saved bundle (used from Step 10 on).

A bundle is a joblib dict: the detector artifact (name, feature_columns,
scaler, model), model_version, operating_point (with "threshold"),
reference_medians and explanation_method. Any detector whose model has
score_samples works without code changes, and the threshold is read from the
bundle, never from code. Explanations are computed for flagged agents only.

Output schema (OUTPUT_COLUMNS): agent_id, analysis_period_start,
analysis_period_end, score, flag, threshold, model_version, top_features, reason.
Unflagged rows carry empty top_features and reason "not flagged".
"""

import joblib
import numpy as np
import pandas as pd

from detectors import Detector
from explain import explain_rows

OUTPUT_COLUMNS = ["agent_id", "analysis_period_start", "analysis_period_end", "score", "flag", "threshold",
                  "model_version", "top_features", "reason"]
NOT_FLAGGED_REASON = "not flagged"


def load_bundle(path):
    return joblib.load(path)


def detector_from(bundle):
    return Detector(bundle["name"], list(bundle["feature_columns"]), bundle["scaler"], bundle["model"])


def score_agents(bundle, features, explain=True):
    detector = detector_from(bundle)
    threshold = float(bundle["operating_point"]["threshold"])
    scores = detector.score(features)
    flags = scores >= threshold
    out = pd.DataFrame({
        "agent_id": features["agent_id"].values,
        "analysis_period_start": features["analysis_period_start"].values,
        "analysis_period_end": features["analysis_period_end"].values,
        "score": scores, "flag": flags, "threshold": threshold, "model_version": bundle["model_version"],
        "top_features": "", "reason": NOT_FLAGGED_REASON,
    })
    if explain and flags.any():
        tops, reasons = explain_rows(detector.scaler, detector.columns, bundle["reference_medians"],
                                     features[np.asarray(flags)])
        out.loc[flags, "top_features"] = tops
        out.loc[flags, "reason"] = reasons
    return out[OUTPUT_COLUMNS]
