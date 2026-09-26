from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = ["submission_frequency", "time_of_day_dist", "customer_similarity", "collusion_score"]


@dataclass
class DetectionResult:
    agent_id: str
    suspicion_score: float
    is_flagged: bool


class FraudDetector:
    def __init__(self, contamination: float = 0.13, n_neighbors: int = 20) -> None:
        self._contamination = contamination
        self._n_neighbors = n_neighbors

    def score(self, feature_rows: list[dict]) -> list[DetectionResult]:
        if not feature_rows:
            return []

        matrix = np.array([[row[col] for col in FEATURE_COLUMNS] for row in feature_rows])
        scaled = StandardScaler().fit_transform(matrix)

        model = LocalOutlierFactor(
            n_neighbors=min(self._n_neighbors, len(feature_rows) - 1),
            contamination=self._contamination,
            novelty=False,
        )
        predictions = model.fit_predict(scaled)
        raw_scores = model.negative_outlier_factor_
        normalized = self._normalize(raw_scores)

        return [
            DetectionResult(
                agent_id=row["agent_id"],
                suspicion_score=float(normalized[i]),
                is_flagged=bool(predictions[i] == -1),
            )
            for i, row in enumerate(feature_rows)
        ]

    @staticmethod
    def _normalize(raw_scores: np.ndarray) -> np.ndarray:
        span = raw_scores.max() - raw_scores.min()
        if span == 0:
            return np.zeros_like(raw_scores)
        return 1 - (raw_scores - raw_scores.min()) / span