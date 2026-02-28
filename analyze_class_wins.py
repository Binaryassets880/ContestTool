"""
Class-Specific Win Factor Analysis

Goal: Determine what factors predict wins for EACH class separately.
This will inform a new class-specific Matchup Score formula.
"""

import asyncio
from collections import defaultdict
from statistics import mean, stdev

async def analyze():
    from app.feed import get_feed

    feed = await get_feed()
    store = feed.store

    print(f"\n{'='*70}")
    print("CLASS-SPECIFIC WIN FACTOR ANALYSIS")
    print(f"{'='*70}")
    print(f"Total scored matches: {len(store.scored_matches)}")

    # Collect data per class
    # Structure: {class: [{won, win_type, own_elims, opp_elims, own_deps, opp_deps, ...}, ...]}
    class_games = defaultdict(list)

    # Also track win_type distribution
    win_type_by_class = defaultdict(lambda: defaultdict(int))

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match or not match.team_won:
            continue

        # Get champions and their teams
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

        # Get performance data
        perf_map = {p["token_id"]: p for p in match.performances if p.get("token_id")}

        # Analyze from each champion's perspective
        for champ in champions:
            token_id = champ.get("token_id")
            champ_class = champ.get("class", "Unknown")
            team = champ.get("team")
            won = match.team_won == team

            # Find opponent
            opp = [c for c in champions if c["team"] != team][0]
            opp_class = opp.get("class", "Unknown")
            opp_team = opp.get("team")

            # Get own champion performance
            my_perf = perf_map.get(token_id, {})
            my_elims = my_perf.get("eliminations", 0) or 0
            my_deps = my_perf.get("deposits", 0) or 0
            my_wart = my_perf.get("wart_distance", 0) or 0

            # Get opponent champion performance
            opp_perf = perf_map.get(opp.get("token_id"), {})
            opp_elims = opp_perf.get("eliminations", 0) or 0
            opp_deps = opp_perf.get("deposits", 0) or 0

            # Get supporter stats (from career averages)
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

            class_games[champ_class].append({
                "won": won,
                "win_type": match.win_type,
                "opp_class": opp_class,
                # Champion's own stats (actual game performance)
                "my_elims": my_elims,
                "my_deps": my_deps,
                "my_wart": my_wart,
                # Supporter averages
                "own_supp_elims": own_avg_elims,
                "own_supp_deps": own_avg_deps,
                "opp_supp_elims": opp_avg_elims,
                "opp_supp_deps": opp_avg_deps,
                # Differentials
                "elim_diff": own_avg_elims - opp_avg_elims,
                "dep_diff": own_avg_deps - opp_avg_deps,
            })

            # Track win type when this class WINS
            if won:
                win_type_by_class[champ_class][match.win_type] += 1

    # ==========================================
    # ANALYSIS 1: How Each Class Wins
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 1: HOW EACH CLASS WINS (Win Type Distribution)")
    print(f"{'='*70}")
    print("\nWhen this class WINS, what's the win_type?\n")

    for cls in sorted(win_type_by_class.keys()):
        wins = win_type_by_class[cls]
        total = sum(wins.values())
        print(f"\n{cls} ({total} wins):")
        for wt in ["eliminations", "gacha", "deposits"]:
            count = wins.get(wt, 0)
            pct = 100 * count / total if total > 0 else 0
            bar = "#" * int(pct / 2)
            print(f"  {wt:12}: {count:4} ({pct:5.1f}%) {bar}")

    # ==========================================
    # ANALYSIS 2: Supporter Factor Correlation
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 2: SUPPORTER FACTOR CORRELATION WITH WINS")
    print(f"{'='*70}")
    print("\nDoes having better supporter elims/deps correlate with winning?\n")

    for cls in sorted(class_games.keys()):
        games = class_games[cls]
        if len(games) < 50:
            continue

        # Split by outcome
        wins = [g for g in games if g["won"]]
        losses = [g for g in games if not g["won"]]

        if not wins or not losses:
            continue

        win_rate = 100 * len(wins) / len(games)

        # Calculate averages for wins vs losses
        win_elim_diff = mean([g["elim_diff"] for g in wins])
        loss_elim_diff = mean([g["elim_diff"] for g in losses])

        win_dep_diff = mean([g["dep_diff"] for g in wins])
        loss_dep_diff = mean([g["dep_diff"] for g in losses])

        print(f"\n{cls} (Win Rate: {win_rate:.1f}%, {len(games)} games)")
        print(f"  Supporter Elim Diff:  Win avg={win_elim_diff:+.3f}  Loss avg={loss_elim_diff:+.3f}  Delta={win_elim_diff-loss_elim_diff:+.3f}")
        print(f"  Supporter Dep Diff:   Win avg={win_dep_diff:+.3f}  Loss avg={loss_dep_diff:+.3f}  Delta={win_dep_diff-loss_dep_diff:+.3f}")

        # Determine which factor matters more for this class
        elim_impact = abs(win_elim_diff - loss_elim_diff)
        dep_impact = abs(win_dep_diff - loss_dep_diff)

        if elim_impact > dep_impact * 1.5:
            print(f"  -> ELIM-DEPENDENT: Elim diff impacts wins {elim_impact/dep_impact:.1f}x more")
        elif dep_impact > elim_impact * 1.5:
            print(f"  -> DEP-DEPENDENT: Dep diff impacts wins {dep_impact/elim_impact:.1f}x more")
        else:
            print(f"  -> BALANCED: Both factors matter roughly equally")

    # ==========================================
    # ANALYSIS 3: Win Rate by Elim Differential Bucket (Per Class)
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 3: WIN RATE BY SUPPORTER ELIM DIFFERENTIAL (Per Class)")
    print(f"{'='*70}")
    print("\nDoes positive elim diff = higher win rate? (Varies by class)\n")

    elim_buckets = [
        ("Very Low (-inf to -0.3)", -999, -0.3),
        ("Low (-0.3 to -0.1)", -0.3, -0.1),
        ("Even (-0.1 to +0.1)", -0.1, 0.1),
        ("High (+0.1 to +0.3)", 0.1, 0.3),
        ("Very High (+0.3 to +inf)", 0.3, 999),
    ]

    for cls in sorted(class_games.keys()):
        games = class_games[cls]
        if len(games) < 100:
            continue

        print(f"\n{cls}:")
        for bucket_name, low, high in elim_buckets:
            bucket_games = [g for g in games if low <= g["elim_diff"] < high]
            if len(bucket_games) < 10:
                continue
            wins = sum(1 for g in bucket_games if g["won"])
            wr = 100 * wins / len(bucket_games)
            bar = "#" * int(wr / 2)
            print(f"  {bucket_name:25}: {wr:5.1f}% ({len(bucket_games):4} games) {bar}")

    # ==========================================
    # ANALYSIS 4: Win Rate by Dep Differential Bucket (Per Class)
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 4: WIN RATE BY SUPPORTER DEP DIFFERENTIAL (Per Class)")
    print(f"{'='*70}")
    print("\nDoes positive dep diff = higher win rate? (Varies by class)\n")

    dep_buckets = [
        ("Very Low (-inf to -0.3)", -999, -0.3),
        ("Low (-0.3 to -0.1)", -0.3, -0.1),
        ("Even (-0.1 to +0.1)", -0.1, 0.1),
        ("High (+0.1 to +0.3)", 0.1, 0.3),
        ("Very High (+0.3 to +inf)", 0.3, 999),
    ]

    for cls in sorted(class_games.keys()):
        games = class_games[cls]
        if len(games) < 100:
            continue

        print(f"\n{cls}:")
        for bucket_name, low, high in dep_buckets:
            bucket_games = [g for g in games if low <= g["dep_diff"] < high]
            if len(bucket_games) < 10:
                continue
            wins = sum(1 for g in bucket_games if g["won"])
            wr = 100 * wins / len(bucket_games)
            bar = "#" * int(wr / 2)
            print(f"  {bucket_name:25}: {wr:5.1f}% ({len(bucket_games):4} games) {bar}")

    # ==========================================
    # ANALYSIS 5: Class vs Class Matchup Matrix
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 5: CLASS VS CLASS WIN RATES")
    print(f"{'='*70}")
    print("\nRows = Your Class, Columns = Opponent Class")
    print("Value = Your Win Rate against that class\n")

    # Build matchup data
    matchups = defaultdict(lambda: {"wins": 0, "games": 0})
    for cls, games in class_games.items():
        for g in games:
            opp = g["opp_class"]
            matchups[(cls, opp)]["games"] += 1
            if g["won"]:
                matchups[(cls, opp)]["wins"] += 1

    # Get all classes
    all_classes = sorted(set(c for c, _ in matchups.keys()))

    # Print header
    print(f"{'':12}", end="")
    for opp in all_classes:
        print(f" {opp[:6]:>6}", end="")
    print()

    # Print matrix
    for cls in all_classes:
        print(f"{cls[:12]:12}", end="")
        for opp in all_classes:
            data = matchups.get((cls, opp), {"wins": 0, "games": 0})
            if data["games"] >= 10:
                wr = 100 * data["wins"] / data["games"]
                print(f" {wr:5.0f}%", end="")
            else:
                print(f"    --", end="")
        print()

    # ==========================================
    # ANALYSIS 6: Optimal Formula Coefficients
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 6: RECOMMENDED CLASS-SPECIFIC COEFFICIENTS")
    print(f"{'='*70}")

    print("""
Based on the analysis above, here's a proposed class-specific MS formula:

MS = base_win_rate + class_matchup_adj + supporter_adj

Where supporter_adj uses CLASS-SPECIFIC weights:
""")

    class_recommendations = {}
    for cls in sorted(class_games.keys()):
        games = class_games[cls]
        if len(games) < 100:
            continue

        wins = [g for g in games if g["won"]]
        losses = [g for g in games if not g["won"]]

        if not wins or not losses:
            continue

        # Calculate impact scores
        win_elim_diff = mean([g["elim_diff"] for g in wins])
        loss_elim_diff = mean([g["elim_diff"] for g in losses])
        elim_impact = win_elim_diff - loss_elim_diff

        win_dep_diff = mean([g["dep_diff"] for g in wins])
        loss_dep_diff = mean([g["dep_diff"] for g in losses])
        dep_impact = win_dep_diff - loss_dep_diff

        # Normalize to get relative weights
        total = abs(elim_impact) + abs(dep_impact)
        if total > 0:
            elim_weight = elim_impact / total
            dep_weight = dep_impact / total
        else:
            elim_weight = 0.5
            dep_weight = 0.5

        # Determine primary win condition from win_type
        wins_dict = win_type_by_class[cls]
        total_wins = sum(wins_dict.values())
        elim_wins = wins_dict.get("eliminations", 0) / total_wins if total_wins else 0
        gacha_wins = wins_dict.get("gacha", 0) / total_wins if total_wins else 0
        dep_wins = wins_dict.get("deposits", 0) / total_wins if total_wins else 0

        class_recommendations[cls] = {
            "elim_weight": round(elim_weight, 2),
            "dep_weight": round(dep_weight, 2),
            "primary_win_type": max([("elims", elim_wins), ("gacha", gacha_wins), ("deps", dep_wins)], key=lambda x: x[1])[0],
            "base_wr": round(100 * len(wins) / len(games), 1),
        }

        print(f"\n{cls} (base WR: {class_recommendations[cls]['base_wr']}%):")
        print(f"  Primary win type: {class_recommendations[cls]['primary_win_type']} ({max(elim_wins, gacha_wins, dep_wins)*100:.0f}% of wins)")
        print(f"  Elim diff weight: {elim_weight:+.2f}")
        print(f"  Dep diff weight:  {dep_weight:+.2f}")

    print(f"\n{'='*70}")
    print("SUMMARY: CLASS ARCHETYPES")
    print(f"{'='*70}")

    print("""
Based on analysis, classes fall into these archetypes:

1. ELIMINATION-FOCUSED (need offensive supporters)
   - Benefit most from high own_supp_elims
   - Want supporters who kill opponents

2. DEPOSIT-FOCUSED (need gacha supporters)
   - Benefit most from high own_supp_deps
   - Want supporters who deposit quickly

3. SURVIVAL-FOCUSED (need defensive supporters)
   - Need to NOT get eliminated
   - Benefit from LOW opp_supp_elims (weak opponent killers)

4. BALANCED
   - Both factors matter similarly
""")

    return class_recommendations


if __name__ == "__main__":
    asyncio.run(analyze())
