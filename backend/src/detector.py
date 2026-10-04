"""
Inference-only fraud detector for the live backend.

Loads the Isolation Forest artifact trained and evaluated offline in ml/
(ml/model.py -> ml/models/isolation_forest_v2.joblib) and scores agents with
it. Nothing is fitted here: the scaler, the forest, the flag threshold
(contamination 0.10, a stated assumption -- see ml/preprocessing.py) and the
training score range used to map raw scores to 0-1 suspicion scores all come
from the artifact, so an agent's score does not depend on which other agents
are in the batch. To change the model, retrain in ml/ and redeploy the file.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import joblib
import numpy as np

FEATURE_COLUMNS = ["submission_frequency", "time_of_day_dist", "customer_similarity", "collusion_score"]

DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "ml" / "models" / "isolation_forest_v2.joblib"


@dataclass
class DetectionResult:
    agent_id: str
    suspicion_score: float
    is_flagged: bool


class FraudDetector:
    def __init__(self, artifact_path: Path | str = DEFAULT_ARTIFACT_PATH) -> None:
        artifact = joblib.load(artifact_path)
        if artifact["feature_columns"] != FEATURE_COLUMNS:
            raise ValueError(
                f"model artifact expects features {artifact['feature_columns']}, backend computes {FEATURE_COLUMNS}"
            )
        self.model_version: str = artifact["model_version"]
        self._scaler = artifact["scaler"]
        self._model = artifact["model"]
        self._score_min = artifact["train_score_min"]
        self._score_max = artifact["train_score_max"]

    def score(self, feature_rows: list[dict]) -> list[DetectionResult]:
        if not feature_rows:
            return []

        matrix = np.array([[row[col] for col in FEATURE_COLUMNS] for row in feature_rows], dtype=float)
        scaled = self._scaler.transform(matrix)
        raw_scores = -self._model.score_samples(scaled)
        flagged = self._model.predict(scaled) == -1
        normalized = self._normalize(raw_scores)

        return [
            DetectionResult(
                agent_id=row["agent_id"],
                suspicion_score=float(normalized[i]),
                is_flagged=bool(flagged[i]),
            )
            for i, row in enumerate(feature_rows)
        ]

    def _normalize(self, raw_scores: np.ndarray) -> np.ndarray:
        """Maps raw anomaly scores to 0-1 using the training score range (same as ml/preprocessing.py)."""
        span = self._score_max - self._score_min
        if span == 0:
            return np.zeros_like(raw_scores)
        return np.clip((raw_scores - self._score_min) / span, 0.0, 1.0)
