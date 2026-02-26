import sqlite3
conn = sqlite3.connect('grandarena.db')
cursor = conn.cursor()

token_id = 7303  # Straw Barry

print('=== STRAW BARRY RECENT GAMES ===')
print()

# Get career stats for all supporters
cursor.execute('SELECT token_id, AVG(eliminations) as career_elims FROM performances GROUP BY token_id')
career_elims = {row[0]: row[1] for row in cursor.fetchall()}

# Get recent games
cursor.execute('''
    SELECT m.match_id, m.match_date, m.team_won, mp.team,
        CASE WHEN m.team_won = mp.team THEN 'WIN' ELSE 'LOSS' END as result,
        m.win_type
    FROM matches m
    JOIN match_players mp ON m.match_id = mp.match_id
    WHERE mp.token_id = ? AND mp.is_champion = 1 AND m.state = 'scored'
    ORDER BY m.match_date DESC
    LIMIT 20
''', (token_id,))

games = cursor.fetchall()
print('Date       | Result | WinType   | MyElims | OppElims | Opponent')
print('-' * 75)

wins = losses = 0
for g in games:
    match_id, date, team_won, my_team, result, win_type = g
    if result == 'WIN': wins += 1
    else: losses += 1

    # Get opponent
    cursor.execute('''
        SELECT name, class, team FROM match_players
        WHERE match_id = ? AND is_champion = 1 AND team != ?
    ''', (match_id, my_team))
    opp = cursor.fetchone()

    # Get my supporters avg elims
    cursor.execute('''
        SELECT token_id FROM match_players
        WHERE match_id = ? AND team = ? AND is_champion = 0
    ''', (match_id, my_team))
    my_supps = [row[0] for row in cursor.fetchall()]
    my_avg = sum(career_elims.get(t, 0) for t in my_supps) / len(my_supps) if my_supps else 0

    # Get opp supporters avg elims
    cursor.execute('''
        SELECT token_id FROM match_players
        WHERE match_id = ? AND team = ? AND is_champion = 0
    ''', (match_id, opp[2]))
    opp_supps = [row[0] for row in cursor.fetchall()]
    opp_avg = sum(career_elims.get(t, 0) for t in opp_supps) / len(opp_supps) if opp_supps else 0

    print(f'{date[:10]} | {result:<4}  | {win_type or "N/A":<9} | {my_avg:>6.2f}  | {opp_avg:>7.2f}  | {opp[0]} ({opp[1]})')

print()
print(f'Last 20: {wins}-{losses}')

# Overall
cursor.execute('''
    SELECT COUNT(*), SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END)
    FROM matches m JOIN match_players mp ON m.match_id = mp.match_id
    WHERE mp.token_id = ? AND mp.is_champion = 1 AND m.state = 'scored'
''', (token_id,))
total, total_wins = cursor.fetchone()
print(f'Overall: {total_wins}-{total-total_wins} ({100*total_wins/total:.1f}%)')

print()
print('=== WIN RATE BY SUPPORTER ELIM DIFFERENTIAL ===')
print()

# Analyze all Defender games by elim differential
cursor.execute('''
    SELECT mp.match_id, mp.team, m.team_won
    FROM matches m
    JOIN match_players mp ON m.match_id = mp.match_id
    WHERE mp.is_champion = 1 AND mp.class = 'Defender' AND m.state = 'scored'
''')

games = cursor.fetchall()
buckets = {}  # differential bucket -> [wins, total]

for match_id, my_team, team_won in games:
    won = 1 if team_won == my_team else 0

    # Get my supporters
    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, my_team))
    my_supps = [r[0] for r in cursor.fetchall()]
    my_avg = sum(career_elims.get(t, 0) for t in my_supps) / len(my_supps) if my_supps else 0

    # Get opp team
    cursor.execute('SELECT team FROM match_players WHERE match_id = ? AND is_champion = 1 AND team != ?', (match_id, my_team))
    opp_result = cursor.fetchone()
    if not opp_result:
        continue
    opp_team = opp_result[0]

    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, opp_team))
    opp_supps = [r[0] for r in cursor.fetchall()]
    opp_avg = sum(career_elims.get(t, 0) for t in opp_supps) / len(opp_supps) if opp_supps else 0

    diff = my_avg - opp_avg

    # Bucket by differential
    if diff >= 1.0:
        bucket = '+1.0+'
    elif diff >= 0.5:
        bucket = '+0.5 to +1.0'
    elif diff >= 0:
        bucket = '0 to +0.5'
    elif diff >= -0.5:
        bucket = '-0.5 to 0'
    elif diff >= -1.0:
        bucket = '-1.0 to -0.5'
    else:
        bucket = '-1.0-'

    if bucket not in buckets:
        buckets[bucket] = [0, 0]
    buckets[bucket][0] += won
    buckets[bucket][1] += 1

print('Elim Diff     | Games | Wins | Win%')
print('-' * 45)
for bucket in ['+1.0+', '+0.5 to +1.0', '0 to +0.5', '-0.5 to 0', '-1.0 to -0.5', '-1.0-']:
    if bucket in buckets:
        w, t = buckets[bucket]
        print(f'{bucket:<14} {t:<6} {w:<5} {100*w/t:.1f}%')

conn.close()
