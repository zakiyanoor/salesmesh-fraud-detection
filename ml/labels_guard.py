"""
Test-set guard: the only way to get labelled data after the split (Step 5).

Steps 7-10 call load_labelled(data_dir, ["train", "validation"]). Asking for
"test" raises TestLabelsLocked unless unlock_test_labels() has been called,
and only the Step 11 final evaluation script (FINAL_EVALUATION_SCRIPT) may call
it. Test label rows are dropped as soon as labels.csv is read, so code paths
that do not unlock never hold them in memory. Features carry no labels, so test
features can be loaded with load_unlabelled.
"""

from pathlib import Path

import pandas as pd

FINAL_EVALUATION_SCRIPT = "final_evaluation.py"
LABEL_COLUMNS = ["agent_id", "is_fraud", "profile", "ring_id"]
_test_unlocked = False


class TestLabelsLocked(RuntimeError):
    pass


def unlock_test_labels():
    """Only FINAL_EVALUATION_SCRIPT may call this, once, at Step 11."""
    global _test_unlocked
    _test_unlocked = True


def test_labels_unlocked():
    return _test_unlocked


def load_split_table(data_dir):
    return pd.read_csv(Path(data_dir) / "split.csv")


def load_labels(data_dir, splits=("train", "validation")):
    """Label rows (with their split) for the requested splits only; test rows are dropped on read."""
    splits = list(splits)
    if "test" in splits and not _test_unlocked:
        raise TestLabelsLocked(f"test labels are locked until Step 11 ({FINAL_EVALUATION_SCRIPT})")
    split = load_split_table(data_dir)
    wanted = split[split["split"].isin(splits)]
    labels = pd.read_csv(Path(data_dir) / "labels.csv", keep_default_na=False)[LABEL_COLUMNS]
    return labels[labels["agent_id"].isin(wanted["agent_id"])].merge(wanted, on="agent_id").reset_index(drop=True)


def load_labelled(data_dir, splits=("train", "validation")):
    """{split: feature vectors joined with labels} for the requested splits only."""
    splits = list(splits)
    if "test" in splits and not _test_unlocked:
        raise TestLabelsLocked(f"test labels are locked until Step 11 ({FINAL_EVALUATION_SCRIPT})")
    data_dir = Path(data_dir)
    split = load_split_table(data_dir)
    wanted = split[split["split"].isin(splits)]
    labels = pd.read_csv(data_dir / "labels.csv", keep_default_na=False)[LABEL_COLUMNS]
    labels = labels[labels["agent_id"].isin(wanted["agent_id"])]
    missing = set(wanted["agent_id"]) - set(labels["agent_id"])
    if missing:
        raise ValueError(f"{len(missing)} agents in {splits} have no label")
    features = pd.read_csv(data_dir / "feature_vectors.csv")
    df = features.merge(wanted, on="agent_id").merge(labels, on="agent_id")
    return {name: df[df["split"] == name].reset_index(drop=True) for name in splits}


def load_unlabelled(data_dir, split_name):
    """Feature vectors for one split, without any label column."""
    data_dir = Path(data_dir)
    split = load_split_table(data_dir)
    features = pd.read_csv(data_dir / "feature_vectors.csv")
    return features.merge(split[split["split"] == split_name], on="agent_id").reset_index(drop=True)
