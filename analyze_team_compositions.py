"""
Team Composition Analysis

Goal: Analyze how supporter ROLE COMBINATIONS affect win rates.
Key insight: A single gacha depositor alone is a liability,
but two gacha depositors together can be a benefit.
"""

import asyncio
from collections import defaultdict


def get_supporter_role(stats):
    """Categorize a supporter based on career stats."""
    deps = stats.get("career_deps", 1.5)
    elims = stats.get("career_elims", 1.0)

    # Pure specialists
    if deps >= 3.0 and elims < 0.8:
        return "GACHA"      # Pure deposit specialist (3+ avg deps)
    elif deps >= 2.0 and elims < 1.0:
        return "GACHA"      # Strong deposit leaning
    elif elims >= 1.8 and deps < 1.2:
        return "ELIM"       # Pure offensive specialist
    elif elims >= 1.5 and deps < 1.5:
        return "ELIM"       # Strong elim leaning
    # Hybrids
    elif deps >= 2.0:
        return "HYBRID_G"   # Leans gacha but some elims
    elif elims >= 1.2:
        return "HYBRID_E"   # Leans elim but some deps
    else:
        return "BALANCED"   # Moderate all-around


def get_composition_pattern(supporters, store):
    """Get a sorted pattern string like 'ELIM-GACHA' or 'GACHA-GACHA'."""
    roles = []
    for s in supporters:
        token_id = s.get("token_id")
        if token_id:
            stats = store.get_career_stats(token_id)
            roles.append(get_supporter_role(stats))
    return "-".join(sorted(roles)) if roles else "UNKNOWN"


def count_role(roles_list, role):
    """Count occurrences of a role in a list."""
    return sum(1 for r in roles_list if r == role)


async def analyze():
    from app.feed import get_feed

    feed = await get_feed()
    store = feed.store

    print(f"\n{'='*70}")
    print("TEAM COMPOSITION ANALYSIS")
    print(f"{'='*70}")
    print(f"Total scored matches: {len(store.scored_matches)}")

    # Data structures
    # 1. Composition pattern win rates
    composition_stats = defaultdict(lambda: {"wins": 0, "games": 0})

    # 2. Composition vs Composition matchups
    comp_vs_comp = defaultdict(lambda: {"wins": 0, "games": 0})

    # 3. Champion class + composition pattern
    class_comp_stats = defaultdict(lambda: {"wins": 0, "games": 0})

    # 4. Gacha count analysis (1 gacha vs 2 gacha)
    gacha_count_stats = defaultdict(lambda: {"wins": 0, "games": 0})

    # 5. Win type by composition
    win_type_by_comp = defaultdict(lambda: defaultdict(int))

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match or not match.team_won:
            continue

        # Get champions and supporters by team
        champions = {1: None, 2: None}
        supporters = {1: [], 2: []}

        for player in match.players:
            team = player.get("team")
            if not team:
                continue
            if player.get("is_champion"):
                champions[team] = player
            else:
                supporters[team].append(player)

        if not champions[1] or not champions[2]:
            continue

        # Get composition patterns for each team
        comp1 = get_composition_pattern(supporters[1], store)
        comp2 = get_composition_pattern(supporters[2], store)

        class1 = champions[1].get("class", "Unknown")
        class2 = champions[2].get("class", "Unknown")

        # Get supporter roles for counting
        roles1 = [get_supporter_role(store.get_career_stats(s["token_id"]))
                  for s in supporters[1] if s.get("token_id")]
        roles2 = [get_supporter_role(store.get_career_stats(s["token_id"]))
                  for s in supporters[2] if s.get("token_id")]

        # Count gacha supporters
        gacha1 = sum(1 for r in roles1 if r in ("GACHA", "HYBRID_G"))
        gacha2 = sum(1 for r in roles2 if r in ("GACHA", "HYBRID_G"))

        # Analyze from team 1's perspective
        won1 = match.team_won == 1
        win_type = match.win_type or "unknown"

        # 1. Composition pattern stats
        composition_stats[comp1]["games"] += 1
        if won1:
            composition_stats[comp1]["wins"] += 1

        composition_stats[comp2]["games"] += 1
        if not won1:
            composition_stats[comp2]["wins"] += 1

        # 2. Composition vs composition
        key1 = f"{comp1} vs {comp2}"
        comp_vs_comp[key1]["games"] += 1
        if won1:
            comp_vs_comp[key1]["wins"] += 1

        key2 = f"{comp2} vs {comp1}"
        comp_vs_comp[key2]["games"] += 1
        if not won1:
            comp_vs_comp[key2]["wins"] += 1

        # 3. Class + composition
        class_comp1 = f"{class1} + {comp1}"
        class_comp_stats[class_comp1]["games"] += 1
        if won1:
            class_comp_stats[class_comp1]["wins"] += 1

        class_comp2 = f"{class2} + {comp2}"
        class_comp_stats[class_comp2]["games"] += 1
        if not won1:
            class_comp_stats[class_comp2]["wins"] += 1

        # 4. Gacha count analysis
        gacha_key1 = f"{gacha1}_gacha"
        gacha_count_stats[gacha_key1]["games"] += 1
        if won1:
            gacha_count_stats[gacha_key1]["wins"] += 1

        gacha_key2 = f"{gacha2}_gacha"
        gacha_count_stats[gacha_key2]["games"] += 1
        if not won1:
            gacha_count_stats[gacha_key2]["wins"] += 1

        # 5. Win type by composition (winner only)
        if won1:
            win_type_by_comp[comp1][win_type] += 1
        else:
            win_type_by_comp[comp2][win_type] += 1

    # ==========================================
    # ANALYSIS 1: Overall Composition Win Rates
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 1: COMPOSITION PATTERN WIN RATES")
    print(f"{'='*70}")
    print("\nWhich supporter role combinations have the highest win rates?\n")

    sorted_comps = sorted(
        composition_stats.items(),
        key=lambda x: x[1]["games"],
        reverse=True
    )

    print(f"{'Composition':<25} {'Games':>8} {'Wins':>8} {'Win%':>8}")
    print("-" * 55)
    for comp, stats in sorted_comps[:20]:
        if stats["games"] >= 50:
            wr = 100 * stats["wins"] / stats["games"]
            bar = "#" * int(wr / 5)
            print(f"{comp:<25} {stats['games']:>8} {stats['wins']:>8} {wr:>7.1f}% {bar}")

    # ==========================================
    # ANALYSIS 2: Gacha Count Win Rates
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 2: GACHA SUPPORTER COUNT WIN RATES")
    print(f"{'='*70}")
    print("\nDoes having 2 gacha supporters beat having 1?\n")

    for key in ["0_gacha", "1_gacha", "2_gacha"]:
        stats = gacha_count_stats[key]
        if stats["games"] >= 50:
            wr = 100 * stats["wins"] / stats["games"]
            bar = "#" * int(wr / 2)
            print(f"{key}: {wr:5.1f}% win rate ({stats['games']} games) {bar}")

    # ==========================================
    # ANALYSIS 3: 1 Gacha vs 2 Gacha Matchups
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 3: GACHA MATCHUP OUTCOMES")
    print(f"{'='*70}")
    print("\nWhen 1-gacha team faces 2-gacha team, who wins?\n")

    # Find these specific matchups
    one_vs_two = {"wins": 0, "games": 0}
    two_vs_one = {"wins": 0, "games": 0}

    for match_id in store.scored_matches:
        match = store.matches.get(match_id)
        if not match or not match.team_won:
            continue

        supporters = {1: [], 2: []}
        for player in match.players:
            team = player.get("team")
            if team and not player.get("is_champion"):
                supporters[team].append(player)

        roles1 = [get_supporter_role(store.get_career_stats(s["token_id"]))
                  for s in supporters[1] if s.get("token_id")]
        roles2 = [get_supporter_role(store.get_career_stats(s["token_id"]))
                  for s in supporters[2] if s.get("token_id")]

        gacha1 = sum(1 for r in roles1 if r in ("GACHA", "HYBRID_G"))
        gacha2 = sum(1 for r in roles2 if r in ("GACHA", "HYBRID_G"))

        won1 = match.team_won == 1

        if gacha1 == 1 and gacha2 == 2:
            one_vs_two["games"] += 1
            if won1:
                one_vs_two["wins"] += 1
        elif gacha1 == 2 and gacha2 == 1:
            two_vs_one["games"] += 1
            if won1:
                two_vs_one["wins"] += 1

    if one_vs_two["games"] >= 20:
        wr = 100 * one_vs_two["wins"] / one_vs_two["games"]
        print(f"1 Gacha vs 2 Gacha: {wr:5.1f}% win rate for 1-gacha team ({one_vs_two['games']} games)")
    if two_vs_one["games"] >= 20:
        wr = 100 * two_vs_one["wins"] / two_vs_one["games"]
        print(f"2 Gacha vs 1 Gacha: {wr:5.1f}% win rate for 2-gacha team ({two_vs_one['games']} games)")

    # ==========================================
    # ANALYSIS 4: Win Type by Composition
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 4: HOW EACH COMPOSITION WINS")
    print(f"{'='*70}")
    print("\nDo gacha-heavy compositions actually win via gacha?\n")

    for comp, win_types in sorted(win_type_by_comp.items(), key=lambda x: sum(x[1].values()), reverse=True)[:10]:
        total = sum(win_types.values())
        if total >= 50:
            gacha_pct = 100 * win_types.get("gacha", 0) / total
            elim_pct = 100 * win_types.get("eliminations", 0) / total
            dep_pct = 100 * win_types.get("deposits", 0) / total
            print(f"{comp:<25}: Elim {elim_pct:4.0f}% | Gacha {gacha_pct:4.0f}% | Dep {dep_pct:4.0f}% ({total} wins)")

    # ==========================================
    # ANALYSIS 5: Champion Class + Composition
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 5: BEST COMPOSITIONS BY CHAMPION CLASS")
    print(f"{'='*70}")
    print("\nWhich compositions work best with each champion class?\n")

    # Group by class
    by_class = defaultdict(list)
    for class_comp, stats in class_comp_stats.items():
        if stats["games"] >= 30:
            parts = class_comp.split(" + ", 1)
            if len(parts) == 2:
                champ_class, comp = parts
                wr = 100 * stats["wins"] / stats["games"]
                by_class[champ_class].append((comp, wr, stats["games"]))

    for champ_class in ["Defender", "Striker", "Bruiser", "Center", "Sprinter", "Grinder"]:
        if champ_class in by_class:
            print(f"\n{champ_class}:")
            sorted_comps = sorted(by_class[champ_class], key=lambda x: x[1], reverse=True)
            for comp, wr, games in sorted_comps[:5]:
                bar = "#" * int(wr / 5)
                print(f"  {comp:<22}: {wr:5.1f}% ({games} games) {bar}")

    # ==========================================
    # ANALYSIS 6: Composition vs Composition Matrix
    # ==========================================
    print(f"\n{'='*70}")
    print("ANALYSIS 6: TOP COMPOSITION MATCHUPS")
    print(f"{'='*70}")
    print("\nMost significant composition matchups:\n")

    # Find matchups with significant sample and non-50% win rates
    significant_matchups = []
    for key, stats in comp_vs_comp.items():
        if stats["games"] >= 30:
            wr = 100 * stats["wins"] / stats["games"]
            if abs(wr - 50) >= 5:  # At least 5% deviation from 50%
                significant_matchups.append((key, wr, stats["games"]))

    significant_matchups.sort(key=lambda x: abs(x[1] - 50), reverse=True)
    for matchup, wr, games in significant_matchups[:15]:
        indicator = "FAVORED" if wr > 55 else "UNFAVORED" if wr < 45 else ""
        print(f"{matchup:<45}: {wr:5.1f}% ({games} games) {indicator}")

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print("""
Key findings to look for:
1. Does 0-gacha beat 1-gacha? (lone gacha = liability)
2. Does 2-gacha beat 1-gacha? (paired gacha = benefit)
3. Which class + composition combos have highest win rates?
4. Do gacha-heavy compositions actually win via gacha?
""")


if __name__ == "__main__":
    asyncio.run(analyze())
