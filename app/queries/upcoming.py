"""Get upcoming matches summary - reimplemented for feed data store."""

from collections import defaultdict

from ..feed import get_feed
from .scoring import calc_matchup_score


async def get_upcoming_summary() -> list[dict]:
    """Get all champions with their aggregated matchup scores for upcoming games."""
    feed = await get_feed()
    store = feed.store

    champ_scores: dict[int, list[float]] = defaultdict(list)
    champ_info: dict[int, dict] = {}

    for match_id in store.scheduled_matches:
        match = store.matches.get(match_id)
        if not match:
            continue

        # Get champions and supporters for each team
        teams: dict[int, dict] = {
            1: {"champion": None, "supporters": []},
            2: {"champion": None, "supporters": []},
        }

        for player in match.players:
            team = player.get("team")
            if not team or team not in teams:
                continue
            if player.get("is_champion"):
                teams[team]["champion"] = player
            else:
                teams[team]["supporters"].append(player)

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

            # Get supporter averages
            my_supp_stats = [
                store.get_career_stats(s["token_id"])
                for s in teams[my_team]["supporters"]
                if s.get("token_id")
            ]
            opp_supp_stats = [
                store.get_career_stats(s["token_id"])
                for s in teams[opp_team]["supporters"]
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

            score = calc_matchup_score(
                base_wr,
                class_matchup,
                my_avg_elims,
                my_avg_deps,
                opp_avg_elims,
                opp_avg_deps,
                my_class,
            )

            champ_scores[token_id].append(score)

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
        expected_wins = sum(s / 100 for s in scores)
        results.append(
            {
                **info,
                "games": len(scores),
                "avg_score": round(sum(scores) / len(scores), 1),
                "expected_wins": round(expected_wins, 1),
                "favorable": sum(1 for s in scores if s >= 60),
                "unfavorable": sum(1 for s in scores if s < 40),
            }
        )

    return sorted(results, key=lambda x: x["expected_wins"], reverse=True)
