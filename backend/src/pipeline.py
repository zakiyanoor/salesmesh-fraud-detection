"""
Detection pipeline entry point.

Scoring is done by src.scoring_service with the frozen v3 model (lof_v3_4f)
and the feature code imported from ml/ (issue #4). The v2 feature functions and
the v2 Isolation Forest detector that used to live here are retired; see
backend/CHANGES.md.

Usage (from backend/): python -m src.pipeline
"""

from __future__ import annotations

from src.scoring_service import run_detection_cycle

ANALYSIS_PERIOD_FORMAT = "%Y-%m"


def compute_client_category_breakdown(records: list) -> dict:
    """
    Distinct clients and categories touched by an agent's activation records.

    client_id and category are pass-through context from other SalesMesh
    modules: they carry no fraud signal and are never model inputs. They are
    surfaced, unchanged, as evidence for admins reviewing a flag
    (GET /api/agents/<agent_id>).
    """
    return {
        "client_ids": sorted({r.client_id for r in records if r.client_id}),
        "categories": sorted({r.category for r in records if r.category}),
    }


def derive_analysis_period(records: list) -> str:
    """"YYYY-MM" when the records fall in one calendar month, else "YYYY-MM_to_YYYY-MM"."""
    timestamps = [r.timestamp for r in records]
    first, last = min(timestamps).strftime(ANALYSIS_PERIOD_FORMAT), max(timestamps).strftime(ANALYSIS_PERIOD_FORMAT)
    return first if first == last else f"{first}_to_{last}"


__all__ = ["run_detection_cycle", "compute_client_category_breakdown", "derive_analysis_period"]


if __name__ == "__main__":
    print(run_detection_cycle())
