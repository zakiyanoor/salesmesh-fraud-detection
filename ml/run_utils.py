"""Run folders: each run writes ml/runs/<run_id>/run_info.json plus its own outputs."""

import hashlib
import json
import platform
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent / "runs"
LIBRARIES = ["numpy", "pandas", "scikit-learn", "faker", "matplotlib", "joblib", "shap"]


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def library_versions():
    versions = {"python": platform.python_version()}
    for lib in LIBRARIES:
        try:
            versions[lib] = version(lib)
        except PackageNotFoundError:
            versions[lib] = None
    return versions


def start_run(kind, seed, parameters, data_files, runs_dir=RUNS_DIR):
    """Creates ml/runs/<timestamp>_<kind>_s<seed>/ and writes run_info.json; returns the folder."""
    now = datetime.now()
    base = f"{now:%Y%m%d-%H%M%S}_{kind}_s{seed}"
    run_dir = Path(runs_dir) / base
    suffix = 1
    while run_dir.exists():
        suffix += 1
        run_dir = Path(runs_dir) / f"{base}_{suffix}"
    run_dir.mkdir(parents=True)
    info = {
        "run_id": run_dir.name,
        "kind": kind,
        "timestamp": now.isoformat(timespec="seconds"),
        "seed": seed,
        "parameters": parameters,
        "data_files": {Path(p).name: file_sha256(p) for p in data_files},
        "library_versions": library_versions(),
    }
    (run_dir / "run_info.json").write_text(json.dumps(info, indent=2, default=str))
    return run_dir
