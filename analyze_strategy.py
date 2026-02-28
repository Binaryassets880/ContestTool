"""
Fantasy Contest Strategy Analysis

Analyzes historical data to determine optimal lineup composition
for 50/50 contests (need to beat median, not win outright).

Key questions:
1. What's the average FP per game by class?
2. What's the variance/consistency by class?
3. How much does winning matter vs raw stats?
4. What lineup composition maximizes floor (consistency)?
"""

import asyncio
import json
from collections import defaultdict
from statistics import mean, stdev, median

# Fantasy scoring constants
FP_ELIM = 80
FP_DEP = 50
FP_WART = 0.5625
FP_WIN = 300


def calc_fp(elims: float, deps: float, wart: float, won: bool) -> float:
    """Calculate fantasy points."""
    stat_points = (elims * FP_ELIM) + (deps * FP_DEP) + (wart * FP_WART)
    win_points = FP_WIN if won else 0
    return round(stat_points + win_points, 1)


async def analyze():
    # Import here to avoid circular imports
    from app.feed import get_feed

    feed = await get_feed()
    store = feed.store

    print(f"\n{'='*60}")
    print("FANTASY CONTEST STRATEGY ANALYSIS")
    print(f"{'='*60}")
    print(f"\nTotal scored matches: {len(store.scored_matches)}")

    # Collect all champion performances
    # Structure: {token_id: [(class, elims, deps, wart, won, fp), ...]}
    champion_games: dict[int, list] = defaultdict(list)

    # Also track by class for aggregate analysis
    class_fps: dict[str, list] = defaultdict(list)
    class_stats: dict[str, dict] = defaultdict(lambda: {
        "elims": [], "deps": [], "wart": [], "wins": 0, "games": 0
    })

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match:
            continue

        # Map token_id to their performance
        perf_map = {p["token_id"]: p for p in match.performances if p.get("token_id")}

        for player in match.players:
            if not player.get("is_champion"):
                continue

            token_id = player.get("token_id")
            player_class = player.get("class", "Unknown")
            team = player.get("team")
            won = match.team_won == team

            # Get performance
            perf = perf_map.get(token_id, {})
            elims = perf.get("eliminations", 0) or 0
            deps = perf.get("deposits", 0) or 0
            wart = perf.get("wart_distance", 0) or 0

            fp = calc_fp(elims, deps, wart, won)

            champion_games[token_id].append({
                "class": player_class,
                "elims": elims,
                "deps": deps,
                "wart": wart,
                "won": won,
                "fp": fp,
                "name": player.get("name", "")
            })

            class_fps[player_class].append(fp)
            class_stats[player_class]["elims"].append(elims)
            class_stats[player_class]["deps"].append(deps)
            class_stats[player_class]["wart"].append(wart)
            class_stats[player_class]["games"] += 1
            if won:
                class_stats[player_class]["wins"] += 1

    # ==========================================
    # ANALYSIS 1: FP by Class
    # ==========================================
    print(f"\n{'='*60}")
    print("ANALYSIS 1: FANTASY POINTS BY CLASS")
    print(f"{'='*60}")
    print(f"\n{'Class':<12} {'Games':>6} {'Avg FP':>8} {'Median':>8} {'StdDev':>8} {'Win%':>7} {'Floor':>8} {'Ceiling':>8}")
    print("-" * 75)

    class_summary = []
    for cls in sorted(class_fps.keys()):
        fps = class_fps[cls]
        stats = class_stats[cls]
        if len(fps) < 10:
            continue

        avg_fp = mean(fps)
        med_fp = median(fps)
        std_fp = stdev(fps) if len(fps) > 1 else 0
        win_rate = 100 * stats["wins"] / stats["games"] if stats["games"] > 0 else 0
        floor = min(fps)
        ceiling = max(fps)

        # Calculate percentiles
        sorted_fps = sorted(fps)
        p10 = sorted_fps[int(len(fps) * 0.1)]
        p25 = sorted_fps[int(len(fps) * 0.25)]
        p75 = sorted_fps[int(len(fps) * 0.75)]
        p90 = sorted_fps[int(len(fps) * 0.9)]

        class_summary.append({
            "class": cls,
            "games": len(fps),
            "avg_fp": avg_fp,
            "median_fp": med_fp,
            "std_fp": std_fp,
            "win_rate": win_rate,
            "floor": floor,
            "ceiling": ceiling,
            "p10": p10,
            "p25": p25,
            "p75": p75,
            "p90": p90,
            "avg_elims": mean(stats["elims"]),
            "avg_deps": mean(stats["deps"]),
            "avg_wart": mean(stats["wart"])
        })

        print(f"{cls:<12} {len(fps):>6} {avg_fp:>8.1f} {med_fp:>8.1f} {std_fp:>8.1f} {win_rate:>6.1f}% {floor:>8.1f} {ceiling:>8.1f}")

    # ==========================================
    # ANALYSIS 2: Win Impact
    # ==========================================
    print(f"\n{'='*60}")
    print("ANALYSIS 2: WIN BONUS IMPACT")
    print(f"{'='*60}")

    all_wins_fp = []
    all_losses_fp = []
    all_wins_stat_fp = []  # FP without win bonus
    all_losses_stat_fp = []

    for token_id, games in champion_games.items():
        for g in games:
            stat_fp = (g["elims"] * FP_ELIM) + (g["deps"] * FP_DEP) + (g["wart"] * FP_WART)
            if g["won"]:
                all_wins_fp.append(g["fp"])
                all_wins_stat_fp.append(stat_fp)
            else:
                all_losses_fp.append(g["fp"])
                all_losses_stat_fp.append(stat_fp)

    print(f"\nWins ({len(all_wins_fp)} games):")
    print(f"  Avg Total FP: {mean(all_wins_fp):.1f}")
    print(f"  Avg Stat FP (no win bonus): {mean(all_wins_stat_fp):.1f}")
    print(f"  Win bonus adds: {FP_WIN} pts")

    print(f"\nLosses ({len(all_losses_fp)} games):")
    print(f"  Avg Total FP: {mean(all_losses_fp):.1f}")
    print(f"  Avg Stat FP: {mean(all_losses_stat_fp):.1f}")

    print(f"\nKey Insight:")
    print(f"  Average FP difference (Win vs Loss): {mean(all_wins_fp) - mean(all_losses_fp):.1f} pts")
    print(f"  Stat-only difference: {mean(all_wins_stat_fp) - mean(all_losses_stat_fp):.1f} pts")
    print(f"  This means winners have slightly better stats too!")

    # ==========================================
    # ANALYSIS 3: Consistency vs Upside
    # ==========================================
    print(f"\n{'='*60}")
    print("ANALYSIS 3: CONSISTENCY ANALYSIS (For 50/50)")
    print(f"{'='*60}")
    print("\nFor 50/50 contests, we want HIGH FLOOR (consistent scorers)")
    print("Looking at 10th percentile (floor) vs average:\n")

    # Sort by floor (p10)
    sorted_by_floor = sorted(class_summary, key=lambda x: x["p10"], reverse=True)
    print(f"{'Class':<12} {'P10 Floor':>10} {'P25':>8} {'Median':>8} {'P75':>8} {'P90':>8}")
    print("-" * 58)
    for cs in sorted_by_floor:
        print(f"{cs['class']:<12} {cs['p10']:>10.1f} {cs['p25']:>8.1f} {cs['median_fp']:>8.1f} {cs['p75']:>8.1f} {cs['p90']:>8.1f}")

    # ==========================================
    # ANALYSIS 4: Stat Contribution Breakdown
    # ==========================================
    print(f"\n{'='*60}")
    print("ANALYSIS 4: STAT CONTRIBUTION BY CLASS")
    print(f"{'='*60}")
    print(f"\n{'Class':<12} {'Avg Elims':>10} {'Elim Pts':>9} {'Avg Deps':>9} {'Dep Pts':>8} {'Avg Wart':>9} {'Wart Pts':>9}")
    print("-" * 77)

    for cs in sorted(class_summary, key=lambda x: x["avg_fp"], reverse=True):
        elim_pts = cs["avg_elims"] * FP_ELIM
        dep_pts = cs["avg_deps"] * FP_DEP
        wart_pts = cs["avg_wart"] * FP_WART
        print(f"{cs['class']:<12} {cs['avg_elims']:>10.2f} {elim_pts:>9.1f} {cs['avg_deps']:>9.2f} {dep_pts:>8.1f} {cs['avg_wart']:>9.1f} {wart_pts:>9.1f}")

    # ==========================================
    # ANALYSIS 5: Top Individual Performers
    # ==========================================
    print(f"\n{'='*60}")
    print("ANALYSIS 5: TOP CONSISTENT PERFORMERS (Min 5 games)")
    print(f"{'='*60}")

    player_summary = []
    for token_id, games in champion_games.items():
        if len(games) < 5:
            continue

        fps = [g["fp"] for g in games]
        wins = sum(1 for g in games if g["won"])
        sorted_fps = sorted(fps)

        player_summary.append({
            "token_id": token_id,
            "name": games[0]["name"],
            "class": games[0]["class"],
            "games": len(games),
            "avg_fp": mean(fps),
            "median_fp": median(fps),
            "std_fp": stdev(fps) if len(fps) > 1 else 0,
            "floor": min(fps),
            "p10": sorted_fps[int(len(fps) * 0.1)] if len(fps) >= 10 else min(fps),
            "win_rate": 100 * wins / len(games)
        })

    # Sort by floor (consistency)
    print("\nTop 15 by Floor (P10) - Best for 50/50:")
    print(f"{'Name':<20} {'Class':<10} {'Games':>6} {'Avg FP':>8} {'Floor':>7} {'StdDev':>7} {'Win%':>6}")
    print("-" * 72)
    for p in sorted(player_summary, key=lambda x: x["p10"], reverse=True)[:15]:
        print(f"{p['name'][:20]:<20} {p['class']:<10} {p['games']:>6} {p['avg_fp']:>8.1f} {p['p10']:>7.1f} {p['std_fp']:>7.1f} {p['win_rate']:>5.1f}%")

    # Sort by average FP
    print("\nTop 15 by Average FP - Highest upside:")
    print(f"{'Name':<20} {'Class':<10} {'Games':>6} {'Avg FP':>8} {'Floor':>7} {'StdDev':>7} {'Win%':>6}")
    print("-" * 72)
    for p in sorted(player_summary, key=lambda x: x["avg_fp"], reverse=True)[:15]:
        print(f"{p['name'][:20]:<20} {p['class']:<10} {p['games']:>6} {p['avg_fp']:>8.1f} {p['p10']:>7.1f} {p['std_fp']:>7.1f} {p['win_rate']:>5.1f}%")

    # ==========================================
    # ANALYSIS 6: Optimal Lineup Composition
    # ==========================================
    print(f"\n{'='*60}")
    print("ANALYSIS 6: LINEUP COMPOSITION RECOMMENDATIONS")
    print(f"{'='*60}")

    # Calculate expected 4-moki lineup FP by class mix
    print("\nSimulated 4-Champion Lineup Expected FP (using class averages):\n")

    # Get class averages sorted by floor
    class_data = {cs["class"]: cs for cs in class_summary if cs["games"] >= 50}

    compositions = [
        ("4x High Floor", ["Defender", "Defender", "Grinder", "Grinder"]),
        ("4x High Avg", ["Striker", "Striker", "Bruiser", "Bruiser"]),
        ("Mixed Safe", ["Defender", "Grinder", "Striker", "Bruiser"]),
        ("Elim Heavy", ["Striker", "Striker", "Striker", "Bruiser"]),
        ("Deposit Heavy", ["Grinder", "Grinder", "Center", "Defender"]),
    ]

    for name, classes in compositions:
        valid_classes = [c for c in classes if c in class_data]
        if len(valid_classes) < 4:
            continue

        total_avg = sum(class_data[c]["avg_fp"] for c in valid_classes)
        total_floor = sum(class_data[c]["p10"] for c in valid_classes)
        total_median = sum(class_data[c]["median_fp"] for c in valid_classes)

        print(f"{name}:")
        print(f"  Classes: {', '.join(valid_classes)}")
        print(f"  Expected Avg: {total_avg:.0f} | Median: {total_median:.0f} | Floor (P10): {total_floor:.0f}")
        print()

    # ==========================================
    # FINAL RECOMMENDATIONS
    # ==========================================
    print(f"\n{'='*60}")
    print("STRATEGIC RECOMMENDATIONS FOR 50/50 CONTESTS")
    print(f"{'='*60}")

    print("""
KEY FINDINGS:

1. WIN BONUS IS HUGE (300 pts)
   - Average win: ~{:.0f} FP vs Average loss: ~{:.0f} FP
   - Prioritize champions with HIGH WIN RATES when matchups are favorable

2. CLASS TIER LIST (by Floor/Consistency):
""".format(mean(all_wins_fp), mean(all_losses_fp)))

    for i, cs in enumerate(sorted_by_floor[:5], 1):
        print(f"   {i}. {cs['class']}: Floor={cs['p10']:.0f}, Avg={cs['avg_fp']:.0f}, WinRate={cs['win_rate']:.1f}%")

    print("""
3. 50/50 STRATEGY:
   - Prioritize WIN PROBABILITY over raw stat production
   - Use Matchup Score (MS) to select favorable matchups
   - MS 60+ = ~65%+ win rate, MS 70+ = ~70%+ win rate
   - The 300 pt win bonus is worth ~4 eliminations!

4. LINEUP CONSTRUCTION:
   - Pick 4 champions with MS 55+ if possible
   - Higher win rate classes provide more consistent floors
   - Avoid low MS matchups (<45) even if champion has good stats

5. FLOOR vs CEILING:
   - For 50/50: Maximize FLOOR (10th percentile FP)
   - Avoid high-variance plays
   - A consistent 350 FP > volatile 200-500 FP range
""")

    return class_summary, player_summary


if __name__ == "__main__":
    asyncio.run(analyze())
