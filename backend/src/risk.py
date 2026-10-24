"""risk_band (issue #18) and score_percentiles (issue #26): what analysts see beside every agent's score."""

from bisect import bisect_left

REVIEW_SCORE = 1.3
RISK_BANDS = ("high", "review", "low")


def risk_band(flag_source, anomaly_score, threshold):
    """
    high: the model flagged the agent (flag_source ML or Both).
    review: the rule alone flagged it (Rule), or its score is at or above
            REVIEW_SCORE but below the cutoff.
    low: everything else. None when the agent has not been scored.
    """
    if flag_source is None:
        return None
    if flag_source in ("ML", "Both"):
        return "high"
    if flag_source == "Rule" or REVIEW_SCORE <= anomaly_score < threshold:
        return "review"
    return "low"


def score_percentiles(scores):
    """
    {agent_id: percentile} for one detection run's {agent_id: anomaly_score}:
    the share of agents in that run with a strictly lower score, 0 to 100,
    rounded to 1 decimal. Tied scores share a percentile. A rank within the
    run, not a probability.
    """
    ordered = sorted(scores.values())
    n = len(ordered)
    return {agent: round(100 * bisect_left(ordered, s) / n, 1) for agent, s in scores.items()}
