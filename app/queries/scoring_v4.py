"""V4 Composition-based matchup scoring.

Based on historical analysis of 12,000+ matches showing:
1. Team composition patterns matter more than averaged stats
2. LONE_G is a liability (47.3% WR, but class-dependent)
3. 2E_AA is strongest overall (62.2% WR)
4. Class-composition synergies are critical:
   - Strikers with LONE_G: 36.2% WR (terrible)
   - Bruisers with 2G_AA: 31.9% WR (terrible)
   - Defenders with MIXED: 63.2% WR (excellent)
5. Champion WR% has very low predictive value
"""

from .composition import detect_team_composition, classify_supporter, get_pattern_display

# Gacha classes for opponent threat detection
GACHA_CLASSES = {"Striker", "Grinder"}

# Overall pattern base win rates (from analysis)
PATTERN_BASE_WR = {
    "2E_AA": 62.2,
    "2E_AB": 55.0,  # Estimated
    "2E_BB": 50.0,  # Estimated
    "MIXED": 53.5,
    "BALANCED": 50.5,
    "2G_AA": 49.5,
    "2G_AB": 48.0,  # Estimated
    "2G_BB": 46.0,  # Estimated
    "LONE_G": 47.3,
    "WART": 45.6,
}

# Class-specific composition adjustments (WR deviation from class average)
# Based on historical analysis: class_comp_wr - class_avg_wr
CLASS_COMP_ADJ = {
    # Striker: Base ~42%, composition has BIG impact
    "Striker": {
        "2G_AA": +4.6,    # 46.9% vs 42.3% base
        "MIXED": +1.6,    # 43.9%
        "BALANCED": 0,
        "LONE_G": -6.1,   # 36.2% (MAJOR penalty)
        "WART": -6.6,     # 35.7%
        "2E_AA": +2.0,    # Estimated
    },
    # Defender: Base ~55%, very flexible
    "Defender": {
        "MIXED": +8.5,    # 63.2% vs 54.7% base
        "LONE_G": +0.5,   # 55.2% (actually fine!)
        "WART": +0.6,     # 55.3%
        "2G_AA": -1.0,    # 53.7%
        "BALANCED": 0,
        "2E_AA": +5.0,    # Estimated
    },
    # Bruiser: Base ~53%, gacha is BAD
    "Bruiser": {
        "BALANCED": 0,
        "MIXED": -4.9,    # 48.4%
        "LONE_G": -11.8,  # 41.5% (penalty)
        "WART": -12.3,    # 41.0%
        "2G_AA": -21.4,   # 31.9% (TERRIBLE!)
        "2E_AA": +10.0,   # Estimated strong
    },
    # Sprinter: Similar to Defender
    "Sprinter": {
        "MIXED": +5.0,
        "2E_AA": +8.0,
        "BALANCED": 0,
        "LONE_G": -3.0,
        "2G_AA": -5.0,
        "WART": -5.0,
    },
    # Center: Similar to Bruiser, elim-focused
    "Center": {
        "2E_AA": +10.0,
        "BALANCED": 0,
        "MIXED": -2.0,
        "LONE_G": -8.0,
        "2G_AA": -15.0,
        "WART": -8.0,
    },
    # Grinder: Mixed, more flexible
    "Grinder": {
        "2E_AA": +7.0,
        "BALANCED": 0,
        "LONE_G": 0,      # 50% (neutral for Grinders)
        "2G_AA": +3.0,
        "MIXED": -9.0,    # 40.6%
        "WART": -11.0,    # 38.1%
    },
    # Forward: Balanced
    "Forward": {
        "2E_AA": +5.0,
        "MIXED": +3.0,
        "BALANCED": 0,
        "LONE_G": -3.0,
        "2G_AA": -2.0,
        "WART": -5.0,
    },
}

# Composition vs composition adjustments (deviation from 50%)
# Key matchups from analysis
COMP_VS_COMP_ADJ = {
    # Strong patterns
    ("2E_AA", "BALANCED"): +7.4,   # 57.4% WR
    ("2E_AA", "LONE_G"): +10.0,    # Estimated strong
    ("MIXED", "BALANCED"): +5.2,   # 55.2% WR
    ("MIXED", "LONE_G"): +2.8,     # 52.8% WR
    ("BALANCED", "LONE_G"): +2.9,  # 52.9% WR
    ("BALANCED", "WART"): +4.7,    # 54.7% WR
    ("2G_AA", "LONE_G"): +6.4,     # 56.4% (inverse of 43.6%)

    # Weak patterns (inverse of above)
    ("BALANCED", "2E_AA"): -7.4,
    ("LONE_G", "2E_AA"): -10.0,
    ("BALANCED", "MIXED"): -5.2,
    ("LONE_G", "MIXED"): -2.8,
    ("LONE_G", "BALANCED"): -2.9,
    ("WART", "BALANCED"): -4.7,
    ("LONE_G", "2G_AA"): -6.4,

    # Gacha vs Gacha
    ("2G_AA", "2G_AA"): 0,         # Even
    ("2G_AA", "BALANCED"): -2.9,   # 47.1% WR
    ("BALANCED", "2G_AA"): +2.9,   # 52.9% WR
}


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


def calc_composition_score(
    champion_wr: float,
    class_matchup: float,
    my_supporters: list[dict],
    opp_supporters: list[dict],
    my_class: str,
    opp_class: str,
) -> tuple[float, str, dict]:
    """
    Calculate matchup score using team composition patterns.

    Weight distribution:
    - Champion WR: ~5% (very low, max ±3 pts)
    - Class matchup: ~20% (max ±10 pts)
    - My composition quality: ~35% (max ±15 pts based on class+comp)
    - Composition vs composition: ~25% (max ±10 pts)
    - Opponent gacha threat: ~15% (up to -8 pts if facing gacha class with depositors)

    Args:
        champion_wr: Champion's historical win rate (0-100)
        class_matchup: Class vs class win rate (0-100)
        my_supporters: List of dicts with career_elims, career_deps, career_wart
        opp_supporters: List of dicts with career_elims, career_deps, career_wart
        my_class: Champion's class
        opp_class: Opponent champion's class

    Returns:
        (score, grade, factors) tuple
    """
    factors = {}

    # Detect compositions
    my_comp = detect_team_composition(my_supporters, my_class)
    opp_comp = detect_team_composition(opp_supporters, opp_class)

    my_pattern = my_comp["pattern"]
    opp_pattern = opp_comp["pattern"]

    factors["my_pattern"] = my_pattern
    factors["opp_pattern"] = opp_pattern

    # Start at 50 (neutral)
    score = 50.0

    # 1. Champion WR adjustment (VERY LOW weight, max ±3 pts)
    champ_adj = (champion_wr - 50) * 0.06
    champ_adj = max(-3, min(3, champ_adj))
    score += champ_adj
    factors["champion_adj"] = round(champ_adj, 1)

    # 2. Class matchup adjustment (max ±10 pts)
    class_adj = (class_matchup - 50) * 0.4
    class_adj = max(-10, min(10, class_adj))
    score += class_adj
    factors["class_adj"] = round(class_adj, 1)

    # 3. My composition quality (class-specific adjustment)
    # This is the main factor - how well does my composition work with my champion class?
    class_comp_map = CLASS_COMP_ADJ.get(my_class, {})
    my_comp_adj = class_comp_map.get(my_pattern, 0)
    # Scale and cap at ±15
    my_comp_adj = max(-15, min(15, my_comp_adj))
    score += my_comp_adj
    factors["my_comp_adj"] = round(my_comp_adj, 1)

    # 4. Composition vs composition adjustment
    comp_matchup_key = (my_pattern, opp_pattern)
    comp_vs_adj = COMP_VS_COMP_ADJ.get(comp_matchup_key, 0)
    # Cap at ±10
    comp_vs_adj = max(-10, min(10, comp_vs_adj))
    score += comp_vs_adj
    factors["comp_vs_adj"] = round(comp_vs_adj, 1)

    # 5. Opponent composition quality penalty/bonus
    # If opponent has bad composition, that's good for us
    opp_class_comp_map = CLASS_COMP_ADJ.get(opp_class, {})
    opp_comp_quality = opp_class_comp_map.get(opp_pattern, 0)
    # Flip sign: their bad comp = our bonus
    opp_penalty_bonus = -opp_comp_quality * 0.3  # Dampened
    opp_penalty_bonus = max(-5, min(5, opp_penalty_bonus))
    score += opp_penalty_bonus
    factors["opp_comp_penalty"] = round(opp_penalty_bonus, 1)

    # 6. Gacha threat detection (when facing Striker/Grinder)
    if opp_class in GACHA_CLASSES and opp_pattern.startswith("2G"):
        # Strong gacha team against us
        gacha_threat = -5
        score += gacha_threat
        factors["gacha_threat"] = gacha_threat

    # 7. Synergy bonus (if my composition synergizes with my class)
    if my_comp.get("is_synergistic"):
        synergy_bonus = 3
        score += synergy_bonus
        factors["synergy_bonus"] = synergy_bonus

    # Clamp to realistic bounds (25-75)
    score = max(25, min(75, round(score, 1)))
    grade = get_grade(score)

    return score, grade, factors


def calc_composition_score_simple(
    my_supporters: list[dict],
    opp_supporters: list[dict],
    my_class: str,
    opp_class: str,
    champion_wr: float = 50.0,
    class_matchup: float = 50.0,
) -> tuple[float, str, dict]:
    """
    Simplified version with default WR values for quick testing.
    """
    return calc_composition_score(
        champion_wr=champion_wr,
        class_matchup=class_matchup,
        my_supporters=my_supporters,
        opp_supporters=opp_supporters,
        my_class=my_class,
        opp_class=opp_class,
    )
