"""Get upcoming matches summary - reimplemented for feed data store."""

from collections import defaultdict

from ..feed import get_feed
from .scoring import calc_matchup_score, get_grade
from .scoring_v4 import calc_composition_score
from .composition import detect_team_composition
from .fantasy import calc_projected_fp


async def get_upcoming_summary() -> list[dict]:
    """Get all champions with their aggregated matchup scores for upcoming games."""
    feed = await get_feed()
    store = feed.store

    champ_scores: dict[int, list[float]] = defaultdict(list)
    champ_scores_v4: dict[int, list[float]] = defaultdict(list)  # V4 composition scores
    champ_patterns: dict[int, list[str]] = defaultdict(list)  # Team patterns
    champ_fp: dict[int, list[float]] = defaultdict(list)  # FP projections per game
    champ_info: dict[int, dict] = {}

    for match_id in store.scheduled_matches:
        match = store.matches.get(match_id)
        if not match:
            continue

        # Get champions and supporters for each team
        teams: dict[int, dict] = {
            1: {"champion": None, "supporters": [], "supporter_stats": []},
            2: {"champion": None, "supporters": [], "supporter_stats": []},
        }

        for player in match.players:
            team = player.get("team")
            if not team or team not in teams:
                continue
            if player.get("is_champion"):
                teams[team]["champion"] = player
            else:
                teams[team]["supporters"].append(player)
                # Also collect stats for composition detection
                if player.get("token_id"):
                    stats = store.get_career_stats(player["token_id"])
                    teams[team]["supporter_stats"].append(stats)

        if not teams[1]["champion"] or not teams[2]["champion"]:
            continue

        # Calculate scores for both teams
        for my_team, opp_team in [(1, 2), (2, 1)]:
            my_champ = teams[my_team]["champion"]
            opp_champ = teams[opp_team]["champion"]

            token_id = my_champ["token_id"]
            my_class = my_champ.get("class", "")
            opp_class = opp_champ.get("class", "")

            # Get base win rate
            champ_wr = store.champion_winrates.get(token_id, {})
            base_wr = champ_wr.get("win_pct", 50.0)

            # Get class matchup
            class_matchup = store.get_class_matchup(my_class, opp_class)

            # Get supporter stats lists
            my_supp_stats = teams[my_team]["supporter_stats"]
            opp_supp_stats = teams[opp_team]["supporter_stats"]

            # Calculate averages for v3.3 scoring
            my_avg_elims = (
                sum(s["career_elims"] for s in my_supp_stats) / len(my_supp_stats)
                if my_supp_stats
                else 1.0
            )
            my_avg_deps = (
                sum(s["career_deps"] for s in my_supp_stats) / len(my_supp_stats)
                if my_supp_stats
                else 1.5
            )
            opp_avg_elims = (
                sum(s["career_elims"] for s in opp_supp_stats) / len(opp_supp_stats)
                if opp_supp_stats
                else 1.0
            )
            opp_avg_deps = (
                sum(s["career_deps"] for s in opp_supp_stats) / len(opp_supp_stats)
                if opp_supp_stats
                else 1.5
            )

            # V3.3 score (legacy)
            score = calc_matchup_score(
                base_wr,
                class_matchup,
                my_avg_elims,
                my_avg_deps,
                opp_avg_elims,
                opp_avg_deps,
                my_class,
                opp_class,
            )

            champ_scores[token_id].append(score)

            # V4 composition-based score
            score_v4, grade_v4, factors = calc_composition_score(
                champion_wr=base_wr,
                class_matchup=class_matchup,
                my_supporters=my_supp_stats,
                opp_supporters=opp_supp_stats,
                my_class=my_class,
                opp_class=opp_class,
            )
            champ_scores_v4[token_id].append(score_v4)
            champ_patterns[token_id].append(factors.get("my_pattern", "BALANCED"))

            # Calculate projected fantasy points using CHAMPION's career stats
            # Use V4 score for FP projection (composition-aware)
            champ_stats = store.get_career_stats(token_id)
            proj_fp = calc_projected_fp(
                champ_stats["career_elims"],
                champ_stats["career_deps"],
                champ_stats["career_wart"],
                score_v4,  # Use V4 composition score
            )
            champ_fp[token_id].append(proj_fp)

            if token_id not in champ_info:
                champ_info[token_id] = {
                    "token_id": token_id,
                    "name": my_champ.get("name", ""),
                    "class": my_class,
                    "base_win_rate": base_wr,
                }

    # Build final results
    results = []
    for token_id, scores in champ_scores.items():
        info = champ_info[token_id]
        scores_v4 = champ_scores_v4[token_id]
        patterns = champ_patterns[token_id]

        # Use V4 scores for primary metrics
        expected_wins = sum(s / 100 for s in scores_v4)
        fp_list = champ_fp[token_id]
        total_fp = sum(fp_list)
        avg_fp = total_fp / len(fp_list) if fp_list else 0

        # Count games by grade (using V4 scores)
        grades = [get_grade(s) for s in scores_v4]
        grade_a = sum(1 for g in grades if g == "A")
        grade_b = sum(1 for g in grades if g == "B")
        grade_d = sum(1 for g in grades if g == "D")
        grade_f = sum(1 for g in grades if g == "F")

        # Determine average grade (using V4)
        avg_score_v4 = sum(scores_v4) / len(scores_v4) if scores_v4 else 50
        avg_grade = get_grade(avg_score_v4)

        # Also compute legacy v3.3 average for comparison
        avg_score_v3 = sum(scores) / len(scores) if scores else 50

        # Find most common pattern
        from collections import Counter
        pattern_counts = Counter(patterns)
        most_common_pattern = pattern_counts.most_common(1)[0][0] if patterns else "BALANCED"

        results.append(
            {
                **info,
                "games": len(scores_v4),
                "avg_score": round(avg_score_v4, 1),  # V4 score as primary
                "avg_score_v3": round(avg_score_v3, 1),  # Legacy for comparison
                "avg_grade": avg_grade,
                "expected_wins": round(expected_wins, 1),
                "grade_a": grade_a,
                "grade_b": grade_b,
                "good_games": grade_a + grade_b,  # A + B combined
                "grade_d": grade_d,
                "grade_f": grade_f,
                "bad_games": grade_d + grade_f,  # D + F combined
                "avg_proj_fp": round(avg_fp, 1),
                "total_proj_fp": round(total_fp, 1),
                "team_pattern": most_common_pattern,  # Most common composition pattern
                "patterns": dict(pattern_counts),  # All patterns with counts
            }
        )

    return sorted(results, key=lambda x: x["expected_wins"], reverse=True)
