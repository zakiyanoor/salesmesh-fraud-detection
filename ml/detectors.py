"""
Anomaly detectors (Step 8): Isolation Forest and Local Outlier Factor.

Both are fitted on TRAINING features only, with a StandardScaler fitted on the
same agents, and never see a label. Scores are oriented so higher = more
anomalous. LOF uses novelty=True so it can score agents it was not fitted on;
its training-agent scores come from negative_outlier_factor_ (each training
agent scored without counting itself as a neighbour).
"""

from dataclasses import dataclass

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

MODEL_SEED = 42
IF_DEFAULTS = {"n_estimators": 200, "max_samples": "auto", "contamination": "auto"}
LOF_DEFAULTS = {"n_neighbors": 20, "contamination": "auto"}


@dataclass
class Detector:
    name: str
    columns: list
    scaler: StandardScaler
    model: object

    def _matrix(self, df):
        return self.scaler.transform(df[self.columns].values)

    def score(self, df):
        """Anomaly score for agents; higher = more anomalous."""
        return -self.model.score_samples(self._matrix(df))

    def training_scores(self, train_df):
        if isinstance(self.model, LocalOutlierFactor):
            return -self.model.negative_outlier_factor_
        return self.score(train_df)

    def artifact(self):
        return {"name": self.name, "feature_columns": list(self.columns), "scaler": self.scaler, "model": self.model}


def fit_isolation_forest(train_df, columns, seed=MODEL_SEED, **params):
    settings = {**IF_DEFAULTS, **params}
    scaler = StandardScaler().fit(train_df[list(columns)].values)
    model = IsolationForest(random_state=seed, **settings).fit(scaler.transform(train_df[list(columns)].values))
    return Detector("isolation_forest", list(columns), scaler, model)


def fit_lof(train_df, columns, seed=MODEL_SEED, **params):
    """LOF is deterministic; seed is accepted for a uniform interface and unused."""
    settings = {**LOF_DEFAULTS, **params}
    scaler = StandardScaler().fit(train_df[list(columns)].values)
    model = LocalOutlierFactor(novelty=True, **settings).fit(scaler.transform(train_df[list(columns)].values))
    return Detector("lof", list(columns), scaler, model)


FITTERS = {"isolation_forest": fit_isolation_forest, "lof": fit_lof}
