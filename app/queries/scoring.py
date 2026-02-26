"""Matchup score calculation - exact copy from database.py for compatibility."""


def calc_matchup_score(
    base_wr: float,
    class_matchup: float,
    own_elims: float,
    own_deps: float,
    opp_elims: float,
    opp_deps: float,
    my_class: str = "Defender",
) -> float:
    """
    Calculate matchup score based on predictive factors.

    V2 - More conservative after real-world testing showed overconfidence.

    Key insight: Aggregate statistics don't translate directly to individual games.
    The formula now uses smaller coefficients and caps the impact of any single factor.
    """
    score = base_wr

    # Class matchup adjustment - capped at +/- 10 points
    class_adj = (class_matchup - 50) * 0.4
    class_adj = max(-10, min(10, class_adj))
    score += class_adj

    # Elim differential - reduced from 20 to 10 pts per 1.0 diff
    # Also capped at +/- 15 points to prevent extreme scores
    elim_diff = own_elims - opp_elims
    elim_adj = elim_diff * 10
    elim_adj = max(-15, min(15, elim_adj))
    score += elim_adj

    # Deposits penalty for Defenders (kept small)
    if my_class == "Defender" and own_deps >= 1.5:
        score -= 3

    # Clamp to 0-100 range
    return max(0, min(100, score))


def get_edge_label(score: float) -> str:
    """Get edge label for a matchup score."""
    if score >= 60:
        return "Favorable"
    elif score >= 40:
        return "Even"
    else:
        return "Tough"
