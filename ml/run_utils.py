"""Run folders: each run writes ml/runs/<run_id>/run_info.json plus its own outputs."""

import hashlib
import json
import os
import platform
import subprocess
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


def total_ram_gb():
    try:
        if platform.system() == "Windows":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                            ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                            ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                            ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                            ("avail_ext_virtual", ctypes.c_ulonglong)]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.total_phys / 2 ** 30, 1)
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30, 1)
    except (AttributeError, OSError, ValueError):
        return None


def git_commit():
    """Read-only: the checked-out commit, or None outside a git repository."""
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def system_info():
    return {
        "python": platform.python_version(),
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "ram_gb": total_ram_gb(),
        "git_commit": git_commit(),
    }


def start_run(kind, seed, parameters, data_files, runs_dir=RUNS_DIR):
    """Creates ml/runs/<timestamp>_<kind>[_s<seed>]/ and writes run_info.json; returns the folder."""
    now = datetime.now()
    base = f"{now:%Y%m%d-%H%M%S}_{kind}" + (f"_s{seed}" if seed is not None else "")
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
        "system": system_info(),
        "library_versions": library_versions(),
    }
    (run_dir / "run_info.json").write_text(json.dumps(info, indent=2, default=str))
    return run_dir
