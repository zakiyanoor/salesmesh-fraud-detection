"""
The one place the backend reaches into ml/ (issue #4).

Feature engineering, scoring and the duplicate activation rule are imported
from ml/ rather than copied, so the backend computes exactly what the frozen
pipeline computed. The frozen scoring bundle (lof_v3_4f: scaler, LOF model,
cutoff and explanation reference) is loaded from FROZEN_EXPLAIN_RUN; its sha256
must match ml/results/FREEZE.md and its cutoff must match the selection run's
operating_point.json, or loading fails.

Never used: ml/models/isolation_forest_v2.joblib and the v2 leftovers in
ml/data/synthetic. Nothing here reads labels.csv or rings.csv.
"""

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ML_DIR = Path(__file__).resolve().parents[2] / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

import baselines  # noqa: E402
import feature_engineering  # noqa: E402
import scoring as ml_scoring  # noqa: E402

FROZEN_EXPLAIN_RUN = "20261013-100433_explain"
FROZEN_SELECTION_RUN = "20261013-093050_selection_s42"
BUNDLE_PATH = ML_DIR / "runs" / FROZEN_EXPLAIN_RUN / "scoring_bundle.joblib"
OPERATING_POINT_PATH = ML_DIR / "runs" / FROZEN_SELECTION_RUN / "operating_point.json"
FREEZE_PATH = ML_DIR / "results" / "FREEZE.md"
MODEL_VERSION = "lof_v3_4f"

MODEL_FEATURES = list(feature_engineering.MODEL_FEATURES)
compute_feature_vectors = feature_engineering.compute_feature_vectors
score_agents = ml_scoring.score_agents
duplicate_activation_counts = baselines.duplicate_activation_counts


class FrozenModelError(RuntimeError):
    pass


def frozen_bundle_hash():
    rel = f"runs/{FROZEN_EXPLAIN_RUN}/scoring_bundle.joblib"
    match = re.search(rf"^\| [^|]+ \| `{re.escape(rel)}` \| `([0-9a-f]{{64}})` \|$",
                      FREEZE_PATH.read_text(encoding="utf-8"), flags=re.M)
    if not match:
        raise FrozenModelError(f"{rel} is not listed in {FREEZE_PATH}")
    return match.group(1)


@lru_cache(maxsize=1)
def load_frozen_bundle():
    from src.load_data import file_sha256

    if file_sha256(BUNDLE_PATH) != frozen_bundle_hash():
        raise FrozenModelError(f"{BUNDLE_PATH} does not match its hash in FREEZE.md")
    bundle = ml_scoring.load_bundle(BUNDLE_PATH)
    operating_point = json.loads(OPERATING_POINT_PATH.read_text(encoding="utf-8"))
    if bundle["model_version"] != MODEL_VERSION or operating_point["model_version"] != MODEL_VERSION:
        raise FrozenModelError(f"expected {MODEL_VERSION}, got {bundle['model_version']}")
    if float(bundle["operating_point"]["threshold"]) != float(operating_point["threshold"]):
        raise FrozenModelError("bundle cutoff differs from operating_point.json")
    if list(bundle["feature_columns"]) != MODEL_FEATURES:
        raise FrozenModelError(f"bundle features {bundle['feature_columns']} are not {MODEL_FEATURES}")
    return bundle
