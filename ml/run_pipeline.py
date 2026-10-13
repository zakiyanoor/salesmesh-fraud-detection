"""
Reproduce command: runs Steps 1 to 10 in order, each step writing its own
ml/runs/<run_id>/ folder. Test labels are never read: every step loads labels
through labels_guard (EDA runs after the split with --without-test), and Step 11
is not part of it.

--seed sets the data generation seed only; every later step keeps its own
fixed seed (split 42, models 42 and 1-5, bootstrap 0).

Usage: python run_pipeline.py [--seed N] [--skip-generation] [--dry-run]
"""

import argparse
import subprocess
import sys
from pathlib import Path

from data_generation import DEFAULT_SEED

ML = Path(__file__).resolve().parent


def pipeline_steps(seed=DEFAULT_SEED, skip_generation=False):
    """[(step name, command arguments)] in run order."""
    steps = [
        ("1 generate data", ["data_generation.py", "--seed", str(seed)]),
        ("2 clean", ["clean_data.py"]),
        ("5 split", ["split.py"]),
        ("3 EDA (training and validation agents only)", ["eda.py", "--without-test"]),
        ("4 features", ["feature_engineering.py"]),
        ("4 feature checks", ["feature_analysis.py"]),
        ("6 preprocessing", ["preprocessing.py"]),
        ("7 baselines", ["baselines.py"]),
        ("8 default models", ["train_models.py"]),
        ("9 selection", ["selection.py"]),
        ("9B learning curve", ["learning_curve.py"]),
        ("10 explanations", ["explainability.py"]),
        ("10 system checks", ["system_checks.py"]),
    ]
    return steps[1:] if skip_generation else steps


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run ML pipeline Steps 1 to 10 in order.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    steps = pipeline_steps(args.seed, args.skip_generation)
    for number, (name, command) in enumerate(steps, start=1):
        line = f"[{number}/{len(steps)}] {name}: python {' '.join(command)}"
        print(line, flush=True)
        if not args.dry_run:
            subprocess.run([sys.executable, *command], cwd=ML, check=True)
    if args.dry_run:
        print("Dry run: nothing was executed.")


if __name__ == "__main__":
    main()
