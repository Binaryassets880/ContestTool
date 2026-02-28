"""Team composition analysis - classify supporters and detect team patterns.

V4.0 - Based on insight that team composition PATTERNS matter more than
averaging supporter stats. Key patterns:
- 2 gacha together = BENEFIT (can reach 10 deposits as team)
- Lone gacha = LIABILITY (racing to 10 alone while teammate does other things)
- 2 elim specialists = Strong offense, denies opponent gacha
"""

from typing import Literal


# Role grade thresholds based on career stats
ELIM_GRADE_A = 1.5  # >1.5 elims/game
ELIM_GRADE_B = 1.0  # 1.0-1.49 elims/game
GACHA_GRADE_A = 2.5  # >2.5 deps/game
GACHA_GRADE_B = 1.5  # 1.5-2.49 deps/game
WART_RIDER_THRESHOLD = 150  # >150 wart/game

# Champion classes that benefit from specific compositions
GACHA_SYNERGY_CLASSES = {"Striker", "Grinder"}
ELIM_SYNERGY_CLASSES = {"Defender", "Bruiser", "Center"}

# Composition pattern types
PATTERNS = Literal[
    "2G_AA",  # Two A-grade gacha runners
    "2G_AB",  # A + B grade gacha
    "2G_BB",  # Two B-grade gacha
    "2E_AA",  # Two A-grade eliminators
    "2E_AB",  # A + B grade eliminators
    "2E_BB",  # Two B-grade eliminators
    "LONE_G",  # 1 gacha + non-gacha (LIABILITY)
    "MIXED",  # 1 gacha + 1 elim
    "WART",  # Wart-focused composition
    "BALANCED",  # No strong patterns
]


def get_elim_grade(career_elims: float) -> str:
    """Get elimination grade (A/B/C) based on career average."""
    if career_elims >= ELIM_GRADE_A:
        return "A"
    elif career_elims >= ELIM_GRADE_B:
        return "B"
    else:
        return "C"


def get_gacha_grade(career_deps: float) -> str:
    """Get gacha grade (A/B/C) based on career deposit average."""
    if career_deps >= GACHA_GRADE_A:
        return "A"
    elif career_deps >= GACHA_GRADE_B:
        return "B"
    else:
        return "C"


def classify_supporter(stats: dict) -> dict:
    """
    Classify a supporter by career stats into role grades.

    Args:
        stats: Dict with career_elims, career_deps, career_wart

    Returns:
        Dict with:
        - elim_grade: A/B/C based on elimination average
        - gacha_grade: A/B/C based on deposit average
        - is_wart_rider: True if high wart distance
        - primary_role: ELIM, GACHA, HYBRID, WART, or BALANCED

    Thresholds:
    - Grade A Eliminator: >1.5 elims/game
    - Grade B Eliminator: 1.0-1.49 elims/game
    - Grade C Eliminator: <1.0 elims/game
    - Grade A Gacha: >2.5 deps/game
    - Grade B Gacha: 1.5-2.49 deps/game
    - Grade C Gacha: <1.5 deps/game
    - Wart Rider: >150 wart/game
    """
    elims = stats.get("career_elims", 1.0)
    deps = stats.get("career_deps", 1.5)
    wart = stats.get("career_wart", 0)

    elim_grade = get_elim_grade(elims)
    gacha_grade = get_gacha_grade(deps)
    is_wart_rider = wart >= WART_RIDER_THRESHOLD

    # Determine primary role based on grades
    # Priority: Strong specialists first, then hybrid, then wart, then balanced
    if elim_grade == "A" and gacha_grade in ("B", "C"):
        primary_role = "ELIM"
    elif gacha_grade == "A" and elim_grade in ("B", "C"):
        primary_role = "GACHA"
    elif elim_grade == "A" and gacha_grade == "A":
        primary_role = "HYBRID"
    elif is_wart_rider and elim_grade != "A":
        # Wart rider only if not a strong eliminator
        primary_role = "WART"
    else:
        primary_role = "BALANCED"

    return {
        "elim_grade": elim_grade,
        "gacha_grade": gacha_grade,
        "is_wart_rider": is_wart_rider,
        "primary_role": primary_role,
        "career_elims": round(elims, 2),
        "career_deps": round(deps, 2),
        "career_wart": round(wart, 1),
    }


def detect_team_composition(supporters: list[dict], champion_class: str = "") -> dict:
    """
    Detect the team's strategic composition pattern.

    Args:
        supporters: List of dicts with career stats (career_elims, career_deps, career_wart)
        champion_class: Champion's class (for context)

    Returns:
        Dict with:
        - pattern: The composition pattern code (2G_AA, LONE_G, etc.)
        - pattern_name: Human-readable pattern name
        - roles: List of classified supporter dicts
        - gacha_count: Number of gacha-role supporters
        - elim_count: Number of elim-role supporters
        - is_synergistic: True if pattern synergizes with champion class

    Pattern priority:
    1. 2 gacha (2G_AA, 2G_AB, 2G_BB)
    2. 2 elim (2E_AA, 2E_AB, 2E_BB)
    3. Lone gacha (LONE_G) - LIABILITY
    4. Mixed (1 gacha + 1 elim)
    5. Wart focused
    6. Balanced
    """
    # Classify each supporter
    roles = [classify_supporter(s) for s in supporters]

    gacha_count = sum(1 for r in roles if r["primary_role"] == "GACHA")
    elim_count = sum(1 for r in roles if r["primary_role"] == "ELIM")
    wart_count = sum(1 for r in roles if r["primary_role"] == "WART")
    hybrid_count = sum(1 for r in roles if r["primary_role"] == "HYBRID")

    # Determine pattern
    pattern = "BALANCED"
    pattern_name = "Balanced"

    if gacha_count >= 2:
        # Double gacha - determine grade
        gacha_grades = sorted(
            [r["gacha_grade"] for r in roles if r["primary_role"] == "GACHA"],
            reverse=True,
        )
        if len(gacha_grades) >= 2 and gacha_grades[0] == "A" and gacha_grades[1] == "A":
            pattern = "2G_AA"
            pattern_name = "Double Gacha (A+A)"
        elif gacha_grades[0] == "A":
            pattern = "2G_AB"
            pattern_name = "Double Gacha (A+B)"
        else:
            pattern = "2G_BB"
            pattern_name = "Double Gacha (B+B)"
    elif elim_count >= 2:
        # Double elim - determine grade
        elim_grades = sorted(
            [r["elim_grade"] for r in roles if r["primary_role"] == "ELIM"],
            reverse=True,
        )
        if len(elim_grades) >= 2 and elim_grades[0] == "A" and elim_grades[1] == "A":
            pattern = "2E_AA"
            pattern_name = "Double Elim (A+A)"
        elif elim_grades[0] == "A":
            pattern = "2E_AB"
            pattern_name = "Double Elim (A+B)"
        else:
            pattern = "2E_BB"
            pattern_name = "Double Elim (B+B)"
    elif gacha_count == 1 and elim_count == 0:
        # LONE GACHA - key liability pattern
        pattern = "LONE_G"
        pattern_name = "Lone Gacha (Liability)"
    elif gacha_count == 1 and elim_count == 1:
        # Mixed strategy
        pattern = "MIXED"
        pattern_name = "Mixed (Gacha+Elim)"
    elif wart_count >= 1 and elim_count == 0 and gacha_count == 0:
        pattern = "WART"
        pattern_name = "Wart Focused"
    elif hybrid_count >= 1:
        # Has hybrid supporter(s)
        if gacha_count == 1 or hybrid_count >= 1:
            # Hybrid + something or just hybrids
            pattern = "MIXED"
            pattern_name = "Mixed (Hybrid)"
    # else: BALANCED (default)

    # Check if pattern synergizes with champion class
    is_synergistic = False
    if pattern.startswith("2G") and champion_class in GACHA_SYNERGY_CLASSES:
        is_synergistic = True
    elif pattern.startswith("2E") and champion_class in ELIM_SYNERGY_CLASSES:
        is_synergistic = True

    return {
        "pattern": pattern,
        "pattern_name": pattern_name,
        "roles": roles,
        "gacha_count": gacha_count,
        "elim_count": elim_count,
        "wart_count": wart_count,
        "is_synergistic": is_synergistic,
        "champion_class": champion_class,
    }


def get_pattern_display(pattern: str) -> dict:
    """Get display info for a composition pattern."""
    PATTERN_INFO = {
        "2G_AA": {
            "name": "2 Gacha (A+A)",
            "short": "2G-AA",
            "color": "#00d4ff",  # Cyan - strong gacha
            "description": "Two elite depositors racing together",
        },
        "2G_AB": {
            "name": "2 Gacha (A+B)",
            "short": "2G-AB",
            "color": "#00aacc",
            "description": "Elite + good depositor team",
        },
        "2G_BB": {
            "name": "2 Gacha (B+B)",
            "short": "2G-BB",
            "color": "#008899",
            "description": "Two decent depositors",
        },
        "2E_AA": {
            "name": "2 Elim (A+A)",
            "short": "2E-AA",
            "color": "#ff4444",  # Red - strong elim
            "description": "Two elite eliminators",
        },
        "2E_AB": {
            "name": "2 Elim (A+B)",
            "short": "2E-AB",
            "color": "#cc3333",
            "description": "Elite + good eliminator team",
        },
        "2E_BB": {
            "name": "2 Elim (B+B)",
            "short": "2E-BB",
            "color": "#992222",
            "description": "Two decent eliminators",
        },
        "LONE_G": {
            "name": "Lone Gacha",
            "short": "LONE",
            "color": "#ff9900",  # Orange - warning
            "description": "Single depositor racing alone (liability)",
        },
        "MIXED": {
            "name": "Mixed",
            "short": "MIX",
            "color": "#aa88ff",  # Purple
            "description": "Gacha + Elim or Hybrid supporters",
        },
        "WART": {
            "name": "Wart Focus",
            "short": "WART",
            "color": "#88aa88",  # Green-gray
            "description": "High wart distance supporters",
        },
        "BALANCED": {
            "name": "Balanced",
            "short": "BAL",
            "color": "#888888",  # Gray
            "description": "No strong specialization",
        },
    }
    return PATTERN_INFO.get(
        pattern,
        {
            "name": pattern,
            "short": pattern[:4],
            "color": "#888888",
            "description": "Unknown pattern",
        },
    )
