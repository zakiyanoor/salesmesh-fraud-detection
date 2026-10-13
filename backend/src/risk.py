"""risk_band (issue #18): one place for the band shown to analysts beside every agent."""

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
