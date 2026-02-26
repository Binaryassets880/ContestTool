import sqlite3
conn = sqlite3.connect('grandarena.db')
cursor = conn.cursor()

# Get career stats for all players
cursor.execute('SELECT token_id, AVG(eliminations) as career_elims, AVG(deposits) as career_deps FROM performances GROUP BY token_id')
career_stats = {row[0]: {'elims': row[1], 'deps': row[2]} for row in cursor.fetchall()}

print('=== WIN TYPE ANALYSIS FOR DEFENDERS ===')
print()

cursor.execute('''
    SELECT m.win_type, COUNT(*) as games,
        SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) as wins
    FROM matches m
    JOIN match_players mp ON m.match_id = mp.match_id
    WHERE mp.is_champion = 1 AND mp.class = 'Defender' AND m.state = 'scored'
    GROUP BY m.win_type
''')

print('Win Type     | Total Games | Def Wins | Def Win%')
print('-' * 55)
for row in cursor.fetchall():
    wt, games, wins = row
    print(f'{wt or "N/A":<13} {games:<12} {wins:<9} {100*wins/games:.1f}%')

print()
print('=== WHEN ELIM ADVANTAGE FAILS: WHAT HAPPENS? ===')
print()

# Analyze games where Defender had elim advantage but lost
cursor.execute('''
    SELECT mp.match_id, mp.team, m.team_won, m.win_type
    FROM matches m
    JOIN match_players mp ON m.match_id = mp.match_id
    WHERE mp.is_champion = 1 AND mp.class = 'Defender' AND m.state = 'scored'
''')

games = cursor.fetchall()
upset_win_types = {}  # When Defender has +0.5 elim advantage but loses
expected_win_types = {}  # When Defender has +0.5 elim advantage and wins

for match_id, my_team, team_won, win_type in games:
    won = team_won == my_team

    # Get my supporters
    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, my_team))
    my_supps = [r[0] for r in cursor.fetchall()]
    my_avg = sum(career_stats.get(t, {}).get('elims', 0) for t in my_supps) / len(my_supps) if my_supps else 0

    # Get opp team
    cursor.execute('SELECT team FROM match_players WHERE match_id = ? AND is_champion = 1 AND team != ?', (match_id, my_team))
    opp_result = cursor.fetchone()
    if not opp_result:
        continue
    opp_team = opp_result[0]

    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, opp_team))
    opp_supps = [r[0] for r in cursor.fetchall()]
    opp_avg = sum(career_stats.get(t, {}).get('elims', 0) for t in opp_supps) / len(opp_supps) if opp_supps else 0

    diff = my_avg - opp_avg

    # Focus on when Defender has advantage (+0.5 or more)
    if diff >= 0.5:
        if not won:
            if win_type not in upset_win_types:
                upset_win_types[win_type] = 0
            upset_win_types[win_type] += 1
        else:
            if win_type not in expected_win_types:
                expected_win_types[win_type] = 0
            expected_win_types[win_type] += 1

print('When Defender has +0.5 elim advantage:')
print()
print('WINS by type:')
for wt, cnt in sorted(expected_win_types.items(), key=lambda x: -x[1]):
    print(f'  {wt or "N/A"}: {cnt}')

print()
print('LOSSES by type (upsets):')
for wt, cnt in sorted(upset_win_types.items(), key=lambda x: -x[1]):
    print(f'  {wt or "N/A"}: {cnt}')

total_with_adv = sum(expected_win_types.values()) + sum(upset_win_types.values())
losses = sum(upset_win_types.values())
print(f'\nTotal with +0.5 advantage: {total_with_adv}, Losses: {losses} ({100*losses/total_with_adv:.1f}%)')

print()
print('=== GACHA DEPOSITS: DOES OWN TEAM DEPOSITS MATTER? ===')
print()

# Analyze gacha deposit advantage
buckets = {}

for match_id, my_team, team_won, win_type in games:
    won = team_won == my_team

    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, my_team))
    my_supps = [r[0] for r in cursor.fetchall()]
    my_deps = sum(career_stats.get(t, {}).get('deps', 0) for t in my_supps) / len(my_supps) if my_supps else 0

    cursor.execute('SELECT team FROM match_players WHERE match_id = ? AND is_champion = 1 AND team != ?', (match_id, my_team))
    opp_result = cursor.fetchone()
    if not opp_result:
        continue
    opp_team = opp_result[0]

    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, opp_team))
    opp_supps = [r[0] for r in cursor.fetchall()]
    opp_deps = sum(career_stats.get(t, {}).get('deps', 0) for t in opp_supps) / len(opp_supps) if opp_supps else 0

    # Categorize
    my_high = my_deps >= 1.5
    opp_high = opp_deps >= 1.5
    key = (my_high, opp_high)
    if key not in buckets:
        buckets[key] = [0, 0]
    buckets[key][1] += 1
    if won:
        buckets[key][0] += 1

print('My Deps | Opp Deps | Games | Wins | Win%')
print('-' * 50)
labels = {(True, True): 'High/High', (True, False): 'High/Low', (False, True): 'Low/High', (False, False): 'Low/Low'}
for key in [(True, False), (False, False), (True, True), (False, True)]:
    if key in buckets:
        wins, total = buckets[key]
        print(f'{labels[key]:<17} {total:<6} {wins:<5} {100*wins/total:.1f}%')

print()
print('=== OPPONENT CLASS + ELIM ADVANTAGE INTERACTION ===')
print()

# Check if opponent class matters when you have elim advantage
class_with_adv = {}

for match_id, my_team, team_won, win_type in games:
    won = team_won == my_team

    # Get opponent class
    cursor.execute('SELECT class, team FROM match_players WHERE match_id = ? AND is_champion = 1 AND team != ?', (match_id, my_team))
    opp = cursor.fetchone()
    if not opp:
        continue
    opp_class, opp_team = opp

    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, my_team))
    my_supps = [r[0] for r in cursor.fetchall()]
    my_avg = sum(career_stats.get(t, {}).get('elims', 0) for t in my_supps) / len(my_supps) if my_supps else 0

    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, opp_team))
    opp_supps = [r[0] for r in cursor.fetchall()]
    opp_avg = sum(career_stats.get(t, {}).get('elims', 0) for t in opp_supps) / len(opp_supps) if opp_supps else 0

    diff = my_avg - opp_avg

    if diff >= 0.5:  # Has elim advantage
        key = (opp_class, 'advantage')
    elif diff <= -0.5:  # Has elim disadvantage
        key = (opp_class, 'disadvantage')
    else:
        key = (opp_class, 'even')

    if key not in class_with_adv:
        class_with_adv[key] = [0, 0]
    class_with_adv[key][1] += 1
    if won:
        class_with_adv[key][0] += 1

print('vs Class     | Situation     | Games | Win%')
print('-' * 55)
for opp_class in ['Striker', 'Bruiser', 'Defender', 'Sprinter', 'Center']:
    for sit in ['advantage', 'even', 'disadvantage']:
        key = (opp_class, sit)
        if key in class_with_adv:
            wins, total = class_with_adv[key]
            print(f'{opp_class:<13} {sit:<14} {total:<6} {100*wins/total:.1f}%')
    print()

conn.close()
