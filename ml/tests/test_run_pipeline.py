"""The reproduce command lists Steps 1 to 10 in order and never reaches the test set."""

import inspect

import run_pipeline

EXPECTED = ["data_generation.py", "clean_data.py", "split.py", "eda.py", "feature_engineering.py",
            "feature_analysis.py", "preprocessing.py", "baselines.py", "train_models.py", "selection.py",
            "learning_curve.py", "explainability.py", "system_checks.py"]


def test_dry_run_lists_the_steps_in_order(capsys):
    run_pipeline.main(["--dry-run", "--seed", "7"])
    lines = capsys.readouterr().out.strip().splitlines()
    scripts = [line.split("python ")[1].split()[0] for line in lines[:-1]]
    assert scripts == EXPECTED
    assert "data_generation.py --seed 7" in lines[0]
    assert "eda.py --without-test" in lines[3]
    assert lines[-1] == "Dry run: nothing was executed."


def test_skip_generation_starts_at_cleaning():
    assert [c[0] for _, c in run_pipeline.pipeline_steps(skip_generation=True)] == EXPECTED[1:]


def test_pipeline_never_reaches_the_test_set():
    commands = " ".join(" ".join(c) for _, c in run_pipeline.pipeline_steps())
    assert "final_evaluation" not in commands and "freeze.py" not in commands
    source = inspect.getsource(run_pipeline)
    assert "unlock_test_labels" not in source and "labels.csv" not in source
