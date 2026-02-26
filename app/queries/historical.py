"""Historical analysis with point-in-time matchup scores."""

from ..feed import get_feed
from .scoring import calc_matchup_score


async def get_historical_analysis(limit: int = 1000) -> dict:
    """
    Analyze historical games with calculated matchup scores.
    Uses POINT-IN-TIME data: for each game, calculates MS using only
    data that was available BEFORE that game was played.
    Returns games and win rate statistics by MS bucket.
    """
    feed = await get_feed()
    store = feed.store

    games = []
    ms_buckets = {
        "80+": {"wins": 0, "total": 0},
        "70-79": {"wins": 0, "total": 0},
        "60-69": {"wins": 0, "total": 0},
        "50-59": {"wins": 0, "total": 0},
        "40-49": {"wins": 0, "total": 0},
        "<40": {"wins": 0, "total": 0},
    }

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

            score = calc_matchup_score(
                my_wr,
                class_matchup,
                my_avg_elims,
                my_avg_deps,
                opp_avg_elims,
                opp_avg_deps,
                my_class,
            )

            won = match.team_won == my_team
            score_rounded = round(score, 1)

            # Update buckets (using rounded score to match display)
            if score_rounded >= 80:
                bucket = "80+"
            elif score_rounded >= 70:
                bucket = "70-79"
            elif score_rounded >= 60:
                bucket = "60-69"
            elif score_rounded >= 50:
                bucket = "50-59"
            elif score_rounded >= 40:
                bucket = "40-49"
            else:
                bucket = "<40"

            ms_buckets[bucket]["total"] += 1
            if won:
                ms_buckets[bucket]["wins"] += 1

            games.append(
                {
                    "match_id": match_id,
                    "date": match_date,
                    "champion": my_champ.get("name", ""),
                    "champion_class": my_class,
                    "opponent": opp_champ.get("name", ""),
                    "opponent_class": opp_class,
                    "matchup_score": score_rounded,
                    "result": "W" if won else "L",
                    "win_type": match.win_type,
                }
            )

    # Calculate bucket stats
    bucket_stats = []
    for bucket_name in ["80+", "70-79", "60-69", "50-59", "40-49", "<40"]:
        bucket = ms_buckets[bucket_name]
        win_rate = (
            round(100 * bucket["wins"] / bucket["total"], 1)
            if bucket["total"] > 0
            else 0
        )
        bucket_stats.append(
            {
                "range": bucket_name,
                "games": bucket["total"],
                "wins": bucket["wins"],
                "win_rate": win_rate,
            }
        )

    return {"games": games, "bucket_stats": bucket_stats}
