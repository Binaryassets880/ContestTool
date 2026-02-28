"""Historical analysis with point-in-time matchup scores."""

from ..feed import get_feed
from .scoring import calc_matchup_score
from .scoring_v4 import calc_composition_score, get_grade
from .composition import detect_team_composition
from .fantasy import calc_projected_fp, calc_actual_fp


async def get_historical_analysis(limit: int = 50000) -> dict:
    """
    Analyze historical games with calculated matchup scores.
    Uses POINT-IN-TIME data: for each game, calculates MS using only
    data that was available BEFORE that game was played.
    Returns games and win rate statistics by MS bucket.
    Includes both V3.3 and V4 (composition) scores for comparison.
    """
    feed = await get_feed()
    store = feed.store

    games = []
    # Grade buckets for V3.3: A (70+), B (60-69), C (50-59), D (40-49), F (<40)
    grade_buckets = {
        "A": {"wins": 0, "total": 0},
        "B": {"wins": 0, "total": 0},
        "C": {"wins": 0, "total": 0},
        "D": {"wins": 0, "total": 0},
        "F": {"wins": 0, "total": 0},
    }
    # Grade buckets for V4 (composition-based)
    grade_buckets_v4 = {
        "A": {"wins": 0, "total": 0},
        "B": {"wins": 0, "total": 0},
        "C": {"wins": 0, "total": 0},
        "D": {"wins": 0, "total": 0},
        "F": {"wins": 0, "total": 0},
    }

    # FP tracking for summary stats
    fp_totals = {"proj_sum": 0.0, "actual_sum": 0.0, "count": 0}

    # Sort scored matches by date descending
    sorted_matches = sorted(
        store.scored_matches,
        key=lambda m: store.matches[m].match_date,
        reverse=True,
    )[:limit]

    for match_id in sorted_matches:
        match = store.matches.get(match_id)
        if not match:
            continue

        match_date = match.match_date

        # Get champions and supporters for each team
        champions: dict[int, dict] = {}
        supporters: dict[int, list] = {1: [], 2: []}

        for player in match.players:
            team = player.get("team")
            if not team:
                continue
            if player.get("is_champion"):
                champions[team] = player
            else:
                supporters[team].append(player)

        if 1 not in champions or 2 not in champions:
            continue

        # Calculate point-in-time stats for both perspectives
        for my_team, opp_team in [(1, 2), (2, 1)]:
            my_champ = champions[my_team]
            opp_champ = champions[opp_team]

            my_token = my_champ.get("token_id")
            if not my_token:
                continue

            # Point-in-time win rate
            my_wr = store.get_champion_winrate_before_date(my_token, match_date)

            # Point-in-time supporter stats
            my_supp_stats = [
                store.get_career_stats_before_date(s["token_id"], match_date)
                for s in supporters[my_team]
                if s.get("token_id")
            ]
            opp_supp_stats = [
                store.get_career_stats_before_date(s["token_id"], match_date)
                for s in supporters[opp_team]
                if s.get("token_id")
            ]

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

            # Class matchup (using all-time data, as per original)
            my_class = my_champ.get("class", "")
            opp_class = opp_champ.get("class", "")
            class_matchup = store.get_class_matchup(my_class, opp_class)

            # V3.3 score (legacy)
            score = calc_matchup_score(
                my_wr,
                class_matchup,
                my_avg_elims,
                my_avg_deps,
                opp_avg_elims,
                opp_avg_deps,
                my_class,
                opp_class,
            )

            won = match.team_won == my_team
            score_rounded = round(score, 1)

            # V4 composition-based score
            score_v4, grade_v4, factors = calc_composition_score(
                champion_wr=my_wr,
                class_matchup=class_matchup,
                my_supporters=my_supp_stats,
                opp_supporters=opp_supp_stats,
                my_class=my_class,
                opp_class=opp_class,
            )
            my_pattern = factors.get("my_pattern", "BALANCED")
            opp_pattern = factors.get("opp_pattern", "BALANCED")

            # Update V3.3 grade buckets
            if score_rounded >= 70:
                grade = "A"
            elif score_rounded >= 60:
                grade = "B"
            elif score_rounded >= 50:
                grade = "C"
            elif score_rounded >= 40:
                grade = "D"
            else:
                grade = "F"

            grade_buckets[grade]["total"] += 1
            if won:
                grade_buckets[grade]["wins"] += 1

            # Update V4 grade buckets
            grade_buckets_v4[grade_v4]["total"] += 1
            if won:
                grade_buckets_v4[grade_v4]["wins"] += 1

            # Get champion's point-in-time career stats for FP projection
            champ_pit_stats = store.get_career_stats_before_date(my_token, match_date)
            proj_fp = calc_projected_fp(
                champ_pit_stats["career_elims"],
                champ_pit_stats["career_deps"],
                champ_pit_stats["career_wart"],
                score_rounded,
            )

            # Get champion's actual performance from this match
            actual_elims, actual_deps, actual_wart = 0.0, 0.0, 0.0
            for perf in match.performances:
                if perf.get("token_id") == my_token:
                    actual_elims = perf.get("eliminations", 0) or 0
                    actual_deps = perf.get("deposits", 0) or 0
                    actual_wart = perf.get("wart_distance", 0) or 0
                    break

            actual_fp = calc_actual_fp(actual_elims, actual_deps, actual_wart, won)
            fp_diff = round(actual_fp - proj_fp, 1)

            # Track FP totals for summary
            fp_totals["proj_sum"] += proj_fp
            fp_totals["actual_sum"] += actual_fp
            fp_totals["count"] += 1

            # Build supporter info with point-in-time stats
            my_supporters_info = []
            for i, s in enumerate(supporters[my_team]):
                if s.get("token_id"):
                    stats = my_supp_stats[i] if i < len(my_supp_stats) else {}
                    my_supporters_info.append({
                        "token_id": s.get("token_id"),
                        "name": s.get("name", ""),
                        "class": s.get("class", ""),
                        "career_elims": round(stats.get("career_elims", 1.0), 2),
                        "career_deps": round(stats.get("career_deps", 1.5), 2),
                        "career_wart": round(stats.get("career_wart", 0), 1),
                    })

            opp_supporters_info = []
            for i, s in enumerate(supporters[opp_team]):
                if s.get("token_id"):
                    stats = opp_supp_stats[i] if i < len(opp_supp_stats) else {}
                    opp_supporters_info.append({
                        "token_id": s.get("token_id"),
                        "name": s.get("name", ""),
                        "class": s.get("class", ""),
                        "career_elims": round(stats.get("career_elims", 1.0), 2),
                        "career_deps": round(stats.get("career_deps", 1.5), 2),
                        "career_wart": round(stats.get("career_wart", 0), 1),
                    })

            games.append(
                {
                    "match_id": match_id,
                    "date": match_date,
                    "champion": my_champ.get("name", ""),
                    "champion_class": my_class,
                    "opponent": opp_champ.get("name", ""),
                    "opponent_class": opp_class,
                    "matchup_score": score_rounded,  # V3.3 score
                    "matchup_score_v4": score_v4,  # V4 composition score
                    "grade": grade,  # V3.3 grade
                    "grade_v4": grade_v4,  # V4 grade
                    "my_pattern": my_pattern,  # Team composition pattern
                    "opp_pattern": opp_pattern,  # Opponent composition pattern
                    "result": "W" if won else "L",
                    "win_type": match.win_type,
                    "my_supporters": my_supporters_info,
                    "opp_supporters": opp_supporters_info,
                    "proj_fp": proj_fp,
                    "actual_fp": actual_fp,
                    "fp_diff": fp_diff,
                }
            )

    # Calculate bucket stats by grade (V3.3)
    bucket_stats = []
    for grade_name in ["A", "B", "C", "D", "F"]:
        bucket = grade_buckets[grade_name]
        win_rate = (
            round(100 * bucket["wins"] / bucket["total"], 1)
            if bucket["total"] > 0
            else 0
        )
        bucket_stats.append(
            {
                "grade": grade_name,
                "games": bucket["total"],
                "wins": bucket["wins"],
                "win_rate": win_rate,
            }
        )

    # Calculate bucket stats by grade (V4 composition-based)
    bucket_stats_v4 = []
    for grade_name in ["A", "B", "C", "D", "F"]:
        bucket = grade_buckets_v4[grade_name]
        win_rate = (
            round(100 * bucket["wins"] / bucket["total"], 1)
            if bucket["total"] > 0
            else 0
        )
        bucket_stats_v4.append(
            {
                "grade": grade_name,
                "games": bucket["total"],
                "wins": bucket["wins"],
                "win_rate": win_rate,
            }
        )

    # Calculate FP summary stats
    fp_stats = {
        "avg_proj_fp": (
            round(fp_totals["proj_sum"] / fp_totals["count"], 1)
            if fp_totals["count"] > 0
            else 0
        ),
        "avg_actual_fp": (
            round(fp_totals["actual_sum"] / fp_totals["count"], 1)
            if fp_totals["count"] > 0
            else 0
        ),
        "total_games": fp_totals["count"],
    }

    return {
        "games": games,
        "bucket_stats": bucket_stats,  # V3.3 stats
        "bucket_stats_v4": bucket_stats_v4,  # V4 composition stats
        "fp_stats": fp_stats,
    }
