"""
Backtest MS Formula v3 vs v2

Compares the new class-specific formula against the old one
to verify improved bucket win rate cascading.
"""

import asyncio
from collections import defaultdict
from statistics import mean


# V2 Formula (old)
def calc_matchup_score_v2(
    base_wr: float,
    class_matchup: float,
    own_elims: float,
    own_deps: float,
    opp_elims: float,
    opp_deps: float,
    my_class: str = "Defender",
) -> float:
    score = base_wr
    class_adj = (class_matchup - 50) * 0.4
    score += max(-10, min(10, class_adj))
    elim_diff = own_elims - opp_elims
    elim_adj = elim_diff * 10
    score += max(-15, min(15, elim_adj))
    if my_class == "Defender" and own_deps >= 1.5:
        score -= 3
    return max(0, min(100, score))


# V3 Formula (new)
CLASS_WEIGHTS = {
    "Striker": (12, -3),
    "Defender": (15, -5),
    "Bruiser": (15, -8),
    "Center": (18, -10),
    "Sprinter": (15, -4),
    "Grinder": (12, -4),
    "Forward": (12, 0),
    "Flanker": (12, -4),
    "Support": (10, -3),
    "Anchor": (10, -3),
}


def calc_matchup_score_v3(
    base_wr: float,
    class_matchup: float,
    own_elims: float,
    own_deps: float,
    opp_elims: float,
    opp_deps: float,
    my_class: str = "Defender",
) -> float:
    score = base_wr
    class_adj = (class_matchup - 50) * 0.6
    score += max(-15, min(15, class_adj))
    elim_diff = own_elims - opp_elims
    dep_diff = own_deps - opp_deps
    elim_w, dep_w = CLASS_WEIGHTS.get(my_class, (12, -4))
    supp_adj = (elim_diff * elim_w) + (dep_diff * dep_w)
    score += max(-15, min(15, supp_adj))
    return max(0, min(100, round(score, 1)))


async def backtest():
    from app.feed import get_feed

    feed = await get_feed()
    store = feed.store

    print(f"\n{'='*70}")
    print("BACKTEST: MS Formula V2 vs V3")
    print(f"{'='*70}")
    print(f"Total scored matches: {len(store.scored_matches)}")

    # Collect results for both formulas
    v2_results = []  # (ms, won)
    v3_results = []  # (ms, won)

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match or not match.team_won:
            continue

        # Get champions
        champions = []
        supporters_by_team = {1: [], 2: []}

        for player in match.players:
            if player.get("is_champion"):
                champions.append(player)
            else:
                team = player.get("team")
                if team:
                    supporters_by_team[team].append(player)

        if len(champions) != 2:
            continue

        # Process each champion's perspective
        for champ in champions:
            token_id = champ.get("token_id")
            champ_class = champ.get("class", "Unknown")
            team = champ.get("team")
            won = match.team_won == team

            # Find opponent
            opp = [c for c in champions if c["team"] != team][0]
            opp_class = opp.get("class", "Unknown")
            opp_team = opp.get("team")

            # Get point-in-time win rate
            base_wr = store.get_champion_winrate_before_date(token_id, match.match_date)

            # Get class matchup
            class_matchup = store.get_class_matchup(champ_class, opp_class)

            # Get supporter stats (use career averages as proxy)
            own_supp_elims = []
            own_supp_deps = []
            for s in supporters_by_team.get(team, []):
                s_id = s.get("token_id")
                if s_id:
                    stats = store.get_career_stats(s_id)
                    own_supp_elims.append(stats["career_elims"])
                    own_supp_deps.append(stats["career_deps"])

            opp_supp_elims = []
            opp_supp_deps = []
            for s in supporters_by_team.get(opp_team, []):
                s_id = s.get("token_id")
                if s_id:
                    stats = store.get_career_stats(s_id)
                    opp_supp_elims.append(stats["career_elims"])
                    opp_supp_deps.append(stats["career_deps"])

            own_avg_elims = mean(own_supp_elims) if own_supp_elims else 1.0
            own_avg_deps = mean(own_supp_deps) if own_supp_deps else 1.5
            opp_avg_elims = mean(opp_supp_elims) if opp_supp_elims else 1.0
            opp_avg_deps = mean(opp_supp_deps) if opp_supp_deps else 1.5

            # Calculate both MS versions
            ms_v2 = calc_matchup_score_v2(
                base_wr, class_matchup,
                own_avg_elims, own_avg_deps,
                opp_avg_elims, opp_avg_deps,
                champ_class
            )
            ms_v3 = calc_matchup_score_v3(
                base_wr, class_matchup,
                own_avg_elims, own_avg_deps,
                opp_avg_elims, opp_avg_deps,
                champ_class
            )

            v2_results.append((ms_v2, won))
            v3_results.append((ms_v3, won))

    # Calculate bucket stats
    def bucket_stats(results, label):
        buckets = [
            ("80+", 80, 101),
            ("70-79", 70, 80),
            ("60-69", 60, 70),
            ("50-59", 50, 60),
            ("40-49", 40, 50),
            ("<40", 0, 40),
        ]

        print(f"\n{label} Bucket Stats:")
        print(f"{'Bucket':<10} {'Games':>8} {'Wins':>8} {'Win%':>8}")
        print("-" * 36)

        bucket_wrs = []
        for name, low, high in buckets:
            games = [(ms, won) for ms, won in results if low <= ms < high]
            if not games:
                continue
            wins = sum(1 for _, won in games if won)
            wr = 100 * wins / len(games)
            bucket_wrs.append(wr)
            print(f"{name:<10} {len(games):>8} {wins:>8} {wr:>7.1f}%")

        # Check if monotonic
        is_monotonic = all(bucket_wrs[i] >= bucket_wrs[i+1] for i in range(len(bucket_wrs)-1))
        print(f"\nMonotonic (higher MS = higher WR): {'YES' if is_monotonic else 'NO'}")
        return bucket_wrs

    v2_wrs = bucket_stats(v2_results, "V2 Formula")
    v3_wrs = bucket_stats(v3_results, "V3 Formula")

    # Compare
    print(f"\n{'='*70}")
    print("COMPARISON: V2 vs V3")
    print(f"{'='*70}")

    buckets = ["80+", "70-79", "60-69", "50-59", "40-49", "<40"]
    print(f"\n{'Bucket':<10} {'V2':>10} {'V3':>10} {'Delta':>10}")
    print("-" * 42)
    for i, name in enumerate(buckets):
        if i < len(v2_wrs) and i < len(v3_wrs):
            delta = v3_wrs[i] - v2_wrs[i]
            indicator = "+" if delta > 0 else ""
            print(f"{name:<10} {v2_wrs[i]:>9.1f}% {v3_wrs[i]:>9.1f}% {indicator}{delta:>9.1f}%")

    # Per-class analysis
    print(f"\n{'='*70}")
    print("PER-CLASS V3 BUCKET STATS")
    print(f"{'='*70}")

    # Group by class
    class_results = defaultdict(list)
    for i, (ms, won) in enumerate(v3_results):
        # We need to track class - let's do another pass
        pass  # Skip for now, main comparison is done

    return v2_results, v3_results


if __name__ == "__main__":
    asyncio.run(backtest())
