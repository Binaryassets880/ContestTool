"""Get team composition statistics table."""

from collections import Counter, defaultdict

from ..feed import get_feed
from .composition import classify_supporter


def classify_champion_subtype(champ_class: str, career_stats: dict) -> str:
    """Sub-classify Sprinters and Grinders based on career stats.

    Sprinters: (Wart) if wart-focused, (Gacha) if deposit-focused
    Grinders: (Elims) if elim-focused, (Gacha) if deposit-focused

    Key insight: deposits >= 1.5 is the differentiator for Gacha playstyle.
    """
    deps = career_stats.get("career_deps", 0)

    if champ_class == "Sprinter":
        # Gacha Sprinters deposit heavily; Wart Sprinters run the course
        if deps >= 1.5:
            return "Sprinter (Gacha)"
        else:
            return "Sprinter (Wart)"

    elif champ_class == "Grinder":
        # Gacha Grinders deposit heavily; Elim Grinders focus on eliminations
        if deps >= 1.5:
            return "Grinder (Gacha)"
        else:
            return "Grinder (Elims)"

    return champ_class


async def get_composition_table(min_games: int = 50) -> list[dict]:
    """Get team composition win rates for display table.

    Returns compositions (champion class + supporter roles) with:
    - Overall win rate and record
    - Best matchup (composition beaten most often)
    - Worst matchup (composition lost to most often)
    """
    feed = await get_feed()
    store = feed.store

    # Track stats per composition
    comp_stats = defaultdict(
        lambda: {"wins": 0, "games": 0, "beat": Counter(), "lost_to": Counter()}
    )

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match or not match.team_won:
            continue

        # Build teams
        teams = {
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
                if player.get("token_id"):
                    stats = store.get_career_stats(player["token_id"])
                    role = classify_supporter(stats)
                    teams[team]["supporters"].append(role["primary_role"])

        # Build composition keys for each team
        comp_keys = {}
        for t in [1, 2]:
            champ = teams[t]["champion"]
            supps = teams[t]["supporters"]
            if not champ or len(supps) != 2:
                continue
            champ_class = champ.get("class", "Unknown")

            # Sub-classify Sprinters and Grinders based on champion career stats
            if champ_class in ("Sprinter", "Grinder"):
                token_id = champ.get("token_id")
                if token_id:
                    champ_stats = store.get_career_stats(token_id)
                    champ_class = classify_champion_subtype(champ_class, champ_stats)

            # Sort supporters for consistency (order doesn't matter)
            supp_sorted = tuple(sorted(supps))
            comp_keys[t] = (champ_class, supp_sorted[0], supp_sorted[1])

        if 1 not in comp_keys or 2 not in comp_keys:
            continue

        winner = match.team_won
        loser = 2 if winner == 1 else 1

        winner_key = comp_keys[winner]
        loser_key = comp_keys[loser]

        # Update stats
        comp_stats[winner_key]["wins"] += 1
        comp_stats[winner_key]["games"] += 1
        comp_stats[winner_key]["beat"][loser_key] += 1

        comp_stats[loser_key]["games"] += 1
        comp_stats[loser_key]["lost_to"][winner_key] += 1

    # Minimum games for head-to-head matchups to be considered
    MIN_H2H_GAMES = 3

    # Build results
    results = []
    for (champ_class, supp1, supp2), stats in comp_stats.items():
        if stats["games"] < min_games:
            continue

        my_key = (champ_class, supp1, supp2)
        win_rate = stats["wins"] / stats["games"] * 100 if stats["games"] > 0 else 50.0

        # Calculate head-to-head win rates against all opponents
        # Combine beat and lost_to to get full picture
        all_opponents = set(stats["beat"].keys()) | set(stats["lost_to"].keys())

        h2h_records = []
        for opp_key in all_opponents:
            wins_vs = stats["beat"].get(opp_key, 0)
            losses_vs = stats["lost_to"].get(opp_key, 0)
            total_vs = wins_vs + losses_vs

            if total_vs >= MIN_H2H_GAMES:
                wr_vs = wins_vs / total_vs * 100
                h2h_records.append({
                    "key": opp_key,
                    "wins": wins_vs,
                    "losses": losses_vs,
                    "games": total_vs,
                    "win_rate": wr_vs,
                })

        # Best matchup = highest win rate (min 3 games)
        best_matchup = None
        if h2h_records:
            best = max(h2h_records, key=lambda x: x["win_rate"])
            if best["win_rate"] > 50:  # Only show if actually favorable
                best_matchup = {
                    "class": best["key"][0],
                    "supp1": best["key"][1],
                    "supp2": best["key"][2],
                    "wins": best["wins"],
                    "games": best["games"],
                    "win_rate": round(best["win_rate"], 1),
                }

        # Worst matchup = lowest win rate (min 3 games)
        worst_matchup = None
        if h2h_records:
            worst = min(h2h_records, key=lambda x: x["win_rate"])
            if worst["win_rate"] < 50:  # Only show if actually unfavorable
                worst_matchup = {
                    "class": worst["key"][0],
                    "supp1": worst["key"][1],
                    "supp2": worst["key"][2],
                    "losses": worst["losses"],
                    "games": worst["games"],
                    "win_rate": round(worst["win_rate"], 1),
                }

        results.append(
            {
                "champion_class": champ_class,
                "supp1": supp1,
                "supp2": supp2,
                "wins": stats["wins"],
                "games": stats["games"],
                "win_rate": round(win_rate, 1),
                "best_matchup": best_matchup,
                "worst_matchup": worst_matchup,
            }
        )

    # Sort by win rate descending
    results.sort(key=lambda x: x["win_rate"], reverse=True)

    return results
