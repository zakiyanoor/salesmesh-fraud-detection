import re
from pathlib import Path

import pytest

from run_utils import file_sha256

ML = Path(__file__).resolve().parents[1]
FREEZE = ML / "results" / "FREEZE.md"
ROW = re.compile(r"^\| [^|]+ \| `([^`]+)` \| `([0-9a-f]{64})` \|$")


def frozen_rows():
    if not FREEZE.exists():
        return []
    return [m.groups() for line in FREEZE.read_text(encoding="utf-8").splitlines() if (m := ROW.match(line))]


@pytest.mark.skipif(not FREEZE.exists(), reason="FREEZE.md not written yet")
def test_freeze_lists_files():
    assert len(frozen_rows()) >= 10


@pytest.mark.parametrize("path, digest", frozen_rows())
def test_frozen_file_is_unchanged(path, digest):
    assert file_sha256(ML / path) == digest, f"{path} changed since FREEZE.md was written"
