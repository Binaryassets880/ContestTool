"""Historical analysis of team compositions.

Analyzes scored matches to build:
1. Composition vs composition win rate matrix
2. Champion class + composition win rates
3. Validation of key hypotheses (lone gacha penalty, etc.)
"""

from collections import defaultdict
from ..feed import get_feed
from .composition import classify_supporter, detect_team_composition


async def build_composition_matrix(use_point_in_time: bool = False) -> dict:
    """
    Analyze all scored matches to build composition win rate matrix.

    Args:
        use_point_in_time: If True, use stats available before each match date.
                          If False, use current cumulative stats (faster).

    Returns:
        {
            "comp_vs_comp": {
                ("2G_AA", "2E_AB"): {"wins": 145, "games": 300, "wr": 48.3},
                ...
            },
            "class_comp_stats": {
                "Striker": {
                    "2G_AA": {"wins": 50, "games": 100, "wr": 50.0},
                    ...
                },
                ...
            },
            "overall_pattern_stats": {
                "2G_AA": {"wins": 500, "games": 1000, "wr": 50.0},
                ...
            },
            "lone_gacha_validation": {...}
        }
    """
    feed = await get_feed()
    store = feed.store

    # Trackers
    comp_vs_comp: dict = defaultdict(lambda: {"wins": 0, "games": 0})
    class_comp: dict = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "games": 0}))
    overall_pattern: dict = defaultdict(lambda: {"wins": 0, "games": 0})

    # For lone gacha validation
    lone_gacha_tracker = {
        "lone_gacha": {"wins": 0, "games": 0},
        "double_gacha": {"wins": 0, "games": 0},
        "no_gacha": {"wins": 0, "games": 0},
    }

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match:
            continue

        match_date = match.match_date

        # Extract teams
        teams: dict[int, dict] = {
            1: {"champion": None, "champion_class": "", "supporters": []},
            2: {"champion": None, "champion_class": "", "supporters": []},
        }

        for player in match.players:
            team = player.get("team")
            if not team or team not in teams:
                continue

            token_id = player.get("token_id")
            if not token_id:
                continue

            if player.get("is_champion"):
                teams[team]["champion"] = player
                teams[team]["champion_class"] = player.get("class", "")
            else:
                # Get supporter stats
                if use_point_in_time:
                    stats = store.get_career_stats_before_date(token_id, match_date)
                else:
                    stats = store.get_career_stats(token_id)
                teams[team]["supporters"].append(stats)

        # Skip if either team lacks champion or supporters
        if not teams[1]["champion"] or not teams[2]["champion"]:
            continue
        if len(teams[1]["supporters"]) < 2 or len(teams[2]["supporters"]) < 2:
            continue

        # Detect compositions
        comp1 = detect_team_composition(
            teams[1]["supporters"], teams[1]["champion_class"]
        )
        comp2 = detect_team_composition(
            teams[2]["supporters"], teams[2]["champion_class"]
        )

        pattern1 = comp1["pattern"]
        pattern2 = comp2["pattern"]
        class1 = teams[1]["champion_class"]
        class2 = teams[2]["champion_class"]

        # Track comp vs comp from team 1's perspective
        comp_vs_comp[(pattern1, pattern2)]["games"] += 1
        if match.team_won == 1:
            comp_vs_comp[(pattern1, pattern2)]["wins"] += 1

        # Track comp vs comp from team 2's perspective
        comp_vs_comp[(pattern2, pattern1)]["games"] += 1
        if match.team_won == 2:
            comp_vs_comp[(pattern2, pattern1)]["wins"] += 1

        # Track class + composition for team 1
        class_comp[class1][pattern1]["games"] += 1
        if match.team_won == 1:
            class_comp[class1][pattern1]["wins"] += 1

        # Track class + composition for team 2
        class_comp[class2][pattern2]["games"] += 1
        if match.team_won == 2:
            class_comp[class2][pattern2]["wins"] += 1

        # Track overall pattern stats for team 1
        overall_pattern[pattern1]["games"] += 1
        if match.team_won == 1:
            overall_pattern[pattern1]["wins"] += 1

        # Track overall pattern stats for team 2
        overall_pattern[pattern2]["games"] += 1
        if match.team_won == 2:
            overall_pattern[pattern2]["wins"] += 1

        # Lone gacha validation
        for team_num in [1, 2]:
            pattern = comp1["pattern"] if team_num == 1 else comp2["pattern"]
            won = match.team_won == team_num

            if pattern == "LONE_G":
                lone_gacha_tracker["lone_gacha"]["games"] += 1
                if won:
                    lone_gacha_tracker["lone_gacha"]["wins"] += 1
            elif pattern.startswith("2G"):
                lone_gacha_tracker["double_gacha"]["games"] += 1
                if won:
                    lone_gacha_tracker["double_gacha"]["wins"] += 1
            elif comp1["gacha_count"] == 0 if team_num == 1 else comp2["gacha_count"] == 0:
                lone_gacha_tracker["no_gacha"]["games"] += 1
                if won:
                    lone_gacha_tracker["no_gacha"]["wins"] += 1

    # Calculate win rates
    def add_winrate(stats: dict) -> dict:
        if stats["games"] > 0:
            stats["wr"] = round(100 * stats["wins"] / stats["games"], 1)
        else:
            stats["wr"] = 50.0
        return stats

    # Convert comp_vs_comp
    comp_vs_comp_result = {
        key: add_winrate(dict(stats)) for key, stats in comp_vs_comp.items()
    }

    # Convert class_comp
    class_comp_result = {}
    for champ_class, patterns in class_comp.items():
        class_comp_result[champ_class] = {
            pattern: add_winrate(dict(stats)) for pattern, stats in patterns.items()
        }

    # Convert overall_pattern
    overall_pattern_result = {
        pattern: add_winrate(dict(stats)) for pattern, stats in overall_pattern.items()
    }

    # Lone gacha validation
    lone_gacha_validation = {
        key: add_winrate(dict(stats)) for key, stats in lone_gacha_tracker.items()
    }

    return {
        "comp_vs_comp": comp_vs_comp_result,
        "class_comp_stats": class_comp_result,
        "overall_pattern_stats": overall_pattern_result,
        "lone_gacha_validation": lone_gacha_validation,
    }


async def validate_hypotheses() -> dict:
    """
    Validate key hypotheses about team compositions.

    Returns dict with hypothesis results and supporting data.
    """
    matrix = await build_composition_matrix()

    results = {}

    # Hypothesis 1: Lone gacha has lower win rate than double gacha
    lone_g = matrix["lone_gacha_validation"]["lone_gacha"]
    double_g = matrix["lone_gacha_validation"]["double_gacha"]

    results["lone_gacha_is_worse"] = {
        "hypothesis": "Lone gacha teams have lower win rate than double gacha teams",
        "lone_gacha_wr": lone_g["wr"],
        "double_gacha_wr": double_g["wr"],
        "difference": round(double_g["wr"] - lone_g["wr"], 1),
        "lone_gacha_games": lone_g["games"],
        "double_gacha_games": double_g["games"],
        "confirmed": lone_g["wr"] < double_g["wr"],
    }

    # Hypothesis 2: Different champion classes have optimal compositions
    class_best_comps = {}
    for champ_class, patterns in matrix["class_comp_stats"].items():
        # Find best pattern with at least 20 games
        valid_patterns = {p: s for p, s in patterns.items() if s["games"] >= 20}
        if valid_patterns:
            best_pattern = max(valid_patterns.items(), key=lambda x: x[1]["wr"])
            worst_pattern = min(valid_patterns.items(), key=lambda x: x[1]["wr"])
            class_best_comps[champ_class] = {
                "best": {"pattern": best_pattern[0], **best_pattern[1]},
                "worst": {"pattern": worst_pattern[0], **worst_pattern[1]},
                "spread": round(best_pattern[1]["wr"] - worst_pattern[1]["wr"], 1),
            }

    results["class_optimal_compositions"] = {
        "hypothesis": "Different champion classes have different optimal compositions",
        "data": class_best_comps,
        "confirmed": any(c["spread"] > 5 for c in class_best_comps.values()),
    }

    # Hypothesis 3: Composition matchup explains significant variance
    # Look at extreme composition matchups
    comp_matchups = matrix["comp_vs_comp"]
    extreme_matchups = [
        {"matchup": k, **v}
        for k, v in comp_matchups.items()
        if v["games"] >= 20 and (v["wr"] >= 60 or v["wr"] <= 40)
    ]
    extreme_matchups.sort(key=lambda x: abs(x["wr"] - 50), reverse=True)

    results["composition_matchups_matter"] = {
        "hypothesis": "Certain composition matchups strongly favor one side",
        "extreme_matchups": extreme_matchups[:10],  # Top 10 most extreme
        "confirmed": len(extreme_matchups) > 0,
    }

    return results


async def get_composition_analysis_summary() -> dict:
    """
    Get a summary of composition analysis for the API/frontend.
    """
    matrix = await build_composition_matrix()
    hypotheses = await validate_hypotheses()

    # Overall pattern win rates (sorted by games)
    pattern_summary = sorted(
        [{"pattern": p, **s} for p, s in matrix["overall_pattern_stats"].items()],
        key=lambda x: x["games"],
        reverse=True,
    )

    # Best compositions by class
    class_summary = {}
    for champ_class, patterns in matrix["class_comp_stats"].items():
        valid = sorted(
            [{"pattern": p, **s} for p, s in patterns.items() if s["games"] >= 10],
            key=lambda x: x["wr"],
            reverse=True,
        )
        if valid:
            class_summary[champ_class] = valid[:3]  # Top 3

    return {
        "pattern_summary": pattern_summary,
        "class_summary": class_summary,
        "lone_gacha_validation": matrix["lone_gacha_validation"],
        "hypotheses": hypotheses,
    }
