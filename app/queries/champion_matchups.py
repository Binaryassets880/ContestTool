"""Get detailed matchups for a specific champion."""

from typing import Optional

from ..feed import get_feed
from .scoring import calc_matchup_score, get_edge_label


async def get_champion_matchups(token_id: int) -> Optional[dict]:
    """Get detailed matchup breakdown for a specific champion."""
    feed = await get_feed()
    store = feed.store

    # Get champion info
    champ_info = store.get_champion_info(token_id)
    if not champ_info:
        return None

    champion = {
        "token_id": token_id,
        "name": champ_info["name"],
        "class": champ_info["class"],
        "base_win_rate": champ_info["win_pct"],
    }

    matchups = []

    # Find all scheduled matches for this champion
    for match_id in store.matches_by_token.get(token_id, []):
        match = store.matches.get(match_id)
        if not match or match.state != "scheduled":
            continue

        # Find champion's team and opponent
        my_team = None
        opp_team = None
        my_champ = None
        opp_champ = None
        my_supporters = []
        opp_supporters = []

        for player in match.players:
            if player.get("token_id") == token_id and player.get("is_champion"):
                my_team = player.get("team")
                my_champ = player

        if my_team is None:
            continue

        opp_team = 2 if my_team == 1 else 1

        for player in match.players:
            team = player.get("team")
            if player.get("is_champion"):
                if team == opp_team:
                    opp_champ = player
            else:
                if team == my_team:
                    my_supporters.append(player)
                elif team == opp_team:
                    opp_supporters.append(player)

        if not opp_champ:
            continue

        # Get opponent win rate
        opp_info = store.get_champion_info(opp_champ["token_id"])
        opp_win_rate = opp_info["win_pct"] if opp_info else 50.0

        # Get class matchup
        my_class = champion["class"]
        opp_class = opp_champ.get("class", "")
        class_matchup = store.get_class_matchup(my_class, opp_class)

        # Get supporter stats with details
        my_supp_details = []
        for s in my_supporters:
            if s.get("token_id"):
                stats = store.get_career_stats(s["token_id"])
                my_supp_details.append(
                    {
                        "token_id": s["token_id"],
                        "name": s.get("name", ""),
                        "class": s.get("class", ""),
                        "career_elims": round(stats["career_elims"], 2),
                        "career_deps": round(stats["career_deps"], 2),
                        "career_wart": round(stats["career_wart"], 2),
                    }
                )

        opp_supp_details = []
        for s in opp_supporters:
            if s.get("token_id"):
                stats = store.get_career_stats(s["token_id"])
                opp_supp_details.append(
                    {
                        "token_id": s["token_id"],
                        "name": s.get("name", ""),
                        "class": s.get("class", ""),
                        "career_elims": round(stats["career_elims"], 2),
                        "career_deps": round(stats["career_deps"], 2),
                        "career_wart": round(stats["career_wart"], 2),
                    }
                )

        # Calculate averages
        my_avg_elims = (
            sum(s["career_elims"] for s in my_supp_details) / len(my_supp_details)
            if my_supp_details
            else 1.0
        )
        my_avg_deps = (
            sum(s["career_deps"] for s in my_supp_details) / len(my_supp_details)
            if my_supp_details
            else 1.5
        )
        opp_avg_elims = (
            sum(s["career_elims"] for s in opp_supp_details) / len(opp_supp_details)
            if opp_supp_details
            else 1.0
        )
        opp_avg_deps = (
            sum(s["career_deps"] for s in opp_supp_details) / len(opp_supp_details)
            if opp_supp_details
            else 1.5
        )

        score = calc_matchup_score(
            champion["base_win_rate"],
            class_matchup,
            my_avg_elims,
            my_avg_deps,
            opp_avg_elims,
            opp_avg_deps,
            my_class,
        )

        matchups.append(
            {
                "date": match.match_date,
                "opponent": opp_champ.get("name", ""),
                "opponent_class": opp_class,
                "opponent_win_rate": opp_win_rate,
                "my_supporters": my_supp_details,
                "opp_supporters": opp_supp_details,
                "my_avg_elims": round(my_avg_elims, 2),
                "my_avg_deps": round(my_avg_deps, 2),
                "opp_avg_elims": round(opp_avg_elims, 2),
                "opp_avg_deps": round(opp_avg_deps, 2),
                "score": round(score, 1),
                "edge": get_edge_label(score),
            }
        )

    # Sort by date
    matchups.sort(key=lambda m: m["date"])

    return {"champion": champion, "matchups": matchups}
