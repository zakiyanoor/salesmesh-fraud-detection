"""Rule: record, activation, agent and other ID columns are never model inputs."""

import numpy as np
import pandas as pd

import detectors
import feature_engineering
import preprocessing

ID_COLUMNS = {"record_id", "activation_id", "agent_id", "vector_id", "flag_id", "customer_id", "client_id", "ring_id"}


def is_id_column(name):
    return name in ID_COLUMNS or name.endswith("_id")


def test_feature_columns_contain_no_id_column():
    offending = [c for c in feature_engineering.FEATURE_COLUMNS if is_id_column(c)]
    assert not offending, f"ID columns in FEATURE_COLUMNS: {offending}"


def feature_frame(n=40, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.random((n, len(feature_engineering.FEATURE_COLUMNS))),
                      columns=feature_engineering.FEATURE_COLUMNS)
    df.insert(0, "agent_id", [f"A{10000 + i}" for i in range(n)])
    df.insert(1, "vector_id", [f"FV{i}" for i in range(n)])
    df["record_id"] = [f"R{i}" for i in range(n)]
    return df


def test_feature_matrix_ignores_id_columns():
    df = feature_frame()
    scaler = preprocessing.fit_scaler(df)
    matrix = preprocessing.scaled_features(scaler, df)
    assert matrix.shape == (len(df), len(feature_engineering.FEATURE_COLUMNS))
    assert scaler.n_features_in_ == len(feature_engineering.FEATURE_COLUMNS)

    shuffled_ids = df.assign(agent_id=df["agent_id"].iloc[::-1].values, record_id="R0", vector_id="FV0")
    assert np.array_equal(matrix, preprocessing.scaled_features(scaler, shuffled_ids))


def test_fitted_models_see_only_feature_columns():
    df = feature_frame()
    for fit in detectors.FITTERS.values():
        detector = fit(df, feature_engineering.FEATURE_COLUMNS)
        assert detector.model.n_features_in_ == len(feature_engineering.FEATURE_COLUMNS)
        assert not any(is_id_column(c) for c in detector.columns)
        assert not hasattr(detector.model, "feature_names_in_") or not any(
            is_id_column(c) for c in detector.model.feature_names_in_)


def test_real_feature_matrix_contains_no_id_columns():
    import data_generation as dg

    data = dg.generate_dataset(3, n_agents=150, fraud_rate=0.15)
    features = feature_engineering.compute_feature_vectors(data.activations, data.agents)
    assert {"vector_id", "agent_id"} <= set(features.columns)
    scaler = preprocessing.fit_scaler(features)
    matrix = preprocessing.scaled_features(scaler, features)
    assert matrix.shape == (len(features), len(feature_engineering.FEATURE_COLUMNS))
    assert not any(is_id_column(c) for c in feature_engineering.FEATURE_COLUMNS)
    assert "peer_group" not in feature_engineering.FEATURE_COLUMNS
    assert np.isfinite(matrix).all()
