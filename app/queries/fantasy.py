"""Fantasy point calculations for Grand Arena Contest Tool.

Scoring:
- Eliminations: 80 pts each
- Deposits: 50 pts each
- Wart Distance: 45 pts per 80 units (0.5625 pts/unit)
- Victory: 300 pts

Only champions score fantasy points (not supporters).
"""

# Fantasy scoring constants
FP_ELIM = 80  # Points per elimination
FP_DEP = 50  # Points per deposit
FP_WART = 0.5625  # Points per wart distance unit (45/80)
FP_WIN = 300  # Points for victory


def calc_projected_fp(
    avg_elims: float,
    avg_deps: float,
    avg_wart: float,
    matchup_score: float,
) -> float:
    """
    Calculate projected fantasy points based on career averages and win probability.

    Args:
        avg_elims: Career average eliminations per game
        avg_deps: Career average deposits per game
        avg_wart: Career average wart distance per game
        matchup_score: Matchup score (0-100) representing win probability

    Returns:
        Projected fantasy points as float
    """
    stat_points = (avg_elims * FP_ELIM) + (avg_deps * FP_DEP) + (avg_wart * FP_WART)
    win_points = (matchup_score / 100) * FP_WIN
    return round(stat_points + win_points, 1)


def calc_actual_fp(
    elims: float,
    deps: float,
    wart: float,
    won: bool,
) -> float:
    """
    Calculate actual fantasy points from game performance.

    Args:
        elims: Actual eliminations in game
        deps: Actual deposits in game
        wart: Actual wart distance in game
        won: Whether the champion won

    Returns:
        Actual fantasy points as float
    """
    stat_points = (elims * FP_ELIM) + (deps * FP_DEP) + (wart * FP_WART)
    win_points = FP_WIN if won else 0
    return round(stat_points + win_points, 1)


def get_fp_tier(fp: float) -> str:
    """
    Get fantasy point tier label for display.

    Args:
        fp: Fantasy points value

    Returns:
        Tier label string
    """
    if fp >= 500:
        return "Elite"
    elif fp >= 400:
        return "Strong"
    elif fp >= 300:
        return "Average"
    else:
        return "Below Avg"
