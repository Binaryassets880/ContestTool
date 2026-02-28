"""Matchup score calculation with class-specific win factors.

V3.3 - Based on analysis of 23,680 matches showing:
1. Elim diff is universally positive (more elims = more wins)
2. Dep diff is NEGATIVE for most classes (deposit-heavy supporters sacrifice offense)
3. Class matchup matters significantly (Defenders beat Strikers 67-33)
4. Different classes have different optimal supporter compositions
5. Against gacha classes (Striker, Grinder), opponent deposits = THREAT
6. NEW: Realistic bounds (25-75) - no matchup is ever 0% or 100%
7. NEW: Letter grades (A/B/C/D/F) for actionable decisions
"""

# Gacha classes where opponent deposits are a threat (they can gacha-win faster)
GACHA_CLASSES = {"Striker", "Grinder"}

# Class-specific weights for supporter adjustments
# Format: (elim_weight, dep_weight)
# Positive = helps win rate, Negative = hurts win rate
CLASS_WEIGHTS = {
    "Striker": (12, -3),   # Wins via gacha (54%), but still needs elims
    "Defender": (15, -5),  # Wins via elims (75%), deps hurt
    "Bruiser": (15, -8),   # Pure elim (83%), deps hurt most
    "Center": (18, -10),   # Pure elim (83%), highest elim dependency
    "Sprinter": (15, -4),  # Elim-focused (75%)
    "Grinder": (12, -4),   # Mixed (63% elim, 33% gacha)
    "Forward": (12, 0),    # Mixed, deps neutral
    "Flanker": (12, -4),   # Elim-focused (80%)
    "Support": (10, -3),   # Lower sample, conservative
    "Anchor": (10, -3),    # Lower sample, conservative
}


def calc_matchup_score(
    base_wr: float,
    class_matchup: float,
    own_elims: float,
    own_deps: float,
    opp_elims: float,
    opp_deps: float,
    my_class: str = "Defender",
    opp_class: str = "",
) -> float:
    """
    Calculate matchup score using class-specific win factors.

    V3.3 formula based on 23,680 match analysis:
    - Stronger class matchup weight (data shows 67% vs 33% swings)
    - Class-specific supporter coefficients
    - Negative dep weight (deposit supporters = weaker offense)
    - Opponent class awareness for gacha threat detection
    - Realistic bounds: 25-75 (no matchup is 0% or 100%)
    """
    score = base_wr

    # Class matchup: stronger weight (+/-15 pts max)
    # Analysis showed massive class advantages (e.g., Defender vs Striker = 67%)
    class_adj = (class_matchup - 50) * 0.6
    score += max(-15, min(15, class_adj))

    # Supporter differentials
    elim_diff = own_elims - opp_elims
    dep_diff = own_deps - opp_deps

    # Get class-specific weights
    elim_w, dep_w = CLASS_WEIGHTS.get(my_class, (12, -4))

    # Apply supporter adjustment with class-specific weights
    # Positive elim_diff = good (my supporters kill more)
    # Positive dep_diff = usually BAD (my supporters sacrifice offense for deposits)
    supp_adj = (elim_diff * elim_w) + (dep_diff * dep_w)
    score += max(-15, min(15, supp_adj))

    # NEW: When facing gacha classes, opponent deposits are a THREAT
    # Applied as SEPARATE penalty (not inside capped supp_adj) so it always has impact
    if opp_class in GACHA_CLASSES:
        # Penalize based on opponent's deposit power (above baseline of 1.5)
        # Strong depositors (3g+) can gacha-win quickly
        opp_dep_threat = max(0, (opp_deps - 1.5)) * 8
        score -= min(20, opp_dep_threat)  # Cap at -20 pts max

    # Clamp to realistic bounds (25-75)
    # Even worst matchups have ~25% upset chance, best matchups cap at ~75%
    return max(25, min(75, round(score, 1)))


def get_grade(score: float) -> str:
    """Get letter grade for matchup score.

    A (70-75): Must-play in lineup
    B (60-69): Good matchup, likely include
    C (50-59): Coin flip, use if needed
    D (40-49): Unfavorable, avoid if possible
    F (25-39): Bad matchup, strong avoid
    """
    if score >= 70:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


# Keep old function for backwards compatibility during transition
def get_edge_label(score: float) -> str:
    """Deprecated: Use get_grade() instead."""
    return get_grade(score)
