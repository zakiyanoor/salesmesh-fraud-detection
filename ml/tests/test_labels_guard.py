"""The test set stays locked through Steps 7-10."""

import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

import labels_guard

ML_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ML_DIR / "data" / "synthetic"
STEP_7_TO_10_MODULES = ["baselines.py", "detectors.py", "train_models.py", "metrics.py", "selection.py", "learning_curve.py"]
have_pipeline_data = pytest.mark.skipif(not (DATA_DIR / "split.csv").exists(), reason="pipeline outputs not generated")


def test_test_labels_are_locked_by_default(tmp_path):
    assert not labels_guard.test_labels_unlocked()
    with pytest.raises(labels_guard.TestLabelsLocked):
        labels_guard.load_labelled(tmp_path, ["train", "test"])


def test_only_the_final_evaluation_script_unlocks_test_labels():
    callers = [p.name for p in ML_DIR.glob("*.py")
               if p.name != "labels_guard.py" and "unlock_test_labels(" in p.read_text(encoding="utf-8")]
    assert set(callers) <= {labels_guard.FINAL_EVALUATION_SCRIPT}


@pytest.mark.parametrize("module", STEP_7_TO_10_MODULES)
def test_step_7_to_10_code_never_reads_labels_directly_or_asks_for_test(module):
    source = (ML_DIR / module).read_text(encoding="utf-8")
    assert not re.search(r"read_csv\([^)]*labels", source)
    assert "unlock_test_labels" not in source
    assert not re.search(r"load_labelled\([^)]*['\"]test['\"]", source)


@have_pipeline_data
def test_step_7_and_8_run_without_any_test_label(tmp_path, monkeypatch):
    for name in ["feature_vectors.csv", "split.csv"]:
        shutil.copy(DATA_DIR / name, tmp_path / name)
    split = pd.read_csv(DATA_DIR / "split.csv")
    labels = pd.read_csv(DATA_DIR / "labels.csv", keep_default_na=False)
    test_ids = set(split.loc[split["split"] == "test", "agent_id"])
    labels[~labels["agent_id"].isin(test_ids)].to_csv(tmp_path / "labels.csv", index=False)

    requested = []
    original = labels_guard.load_labelled

    def recording(data_dir, splits=("train", "validation")):
        requested.append(list(splits))
        return original(data_dir, splits)

    import baselines
    import train_models

    monkeypatch.setattr(baselines, "load_labelled", recording)
    monkeypatch.setattr(train_models, "load_labelled", recording)
    baselines.run_baselines(tmp_path)
    train_models.run_models(tmp_path)
    assert requested and all("test" not in splits for splits in requested)


@have_pipeline_data
def test_unlabelled_test_features_carry_no_labels():
    test_features = labels_guard.load_unlabelled(DATA_DIR, "test")
    assert len(test_features) == 150
    assert not {"is_fraud", "profile", "ring_id"} & set(test_features.columns)
