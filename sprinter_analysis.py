import sqlite3
conn = sqlite3.connect('grandarena.db')
cursor = conn.cursor()

print('=== DEFENDER vs SPRINTER DEEP DIVE ===')
print()

# What is the actual win rate?
cursor.execute('''
    SELECT
        COUNT(*) as games,
        SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) as def_wins
    FROM matches m
    JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1 AND mp1.class = 'Defender'
    JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp2.class = 'Sprinter' AND mp1.team != mp2.team
    WHERE m.state = 'scored'
''')
row = cursor.fetchone()
print(f'Defender vs Sprinter: {row[0]} games, Defender wins {row[1]} ({100*row[1]/row[0]:.1f}%)')

# Win type analysis
cursor.execute('''
    SELECT m.win_type,
        COUNT(*) as games,
        SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) as def_wins
    FROM matches m
    JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1 AND mp1.class = 'Defender'
    JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp2.class = 'Sprinter' AND mp1.team != mp2.team
    WHERE m.state = 'scored'
    GROUP BY m.win_type
''')
print()
print('Win Type     | Games | Def Wins | Def Win%')
print('-' * 50)
for row in cursor.fetchall():
    print(f'{row[0]:<13} {row[1]:<6} {row[2]:<9} {100*row[2]/row[1]:.1f}%')

# Get career stats
cursor.execute('SELECT token_id, AVG(eliminations) FROM performances GROUP BY token_id')
career = {r[0]: r[1] for r in cursor.fetchall()}

# What stats predict wins vs Sprinters?
print()
print('=== ELIM DIFFERENTIAL vs SPRINTERS ===')

cursor.execute('''
    SELECT mp1.match_id, mp1.team, m.team_won
    FROM matches m
    JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1 AND mp1.class = 'Defender'
    JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp2.class = 'Sprinter' AND mp1.team != mp2.team
    WHERE m.state = 'scored'
''')

buckets = {'+0.5+': [0, 0], '0 to +0.5': [0, 0], '-0.5 to 0': [0, 0], '-0.5-': [0, 0]}

for row in cursor.fetchall():
    match_id, def_team, team_won = row
    won = 1 if team_won == def_team else 0

    # Get defender supporters
    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, def_team))
    def_supps = [r[0] for r in cursor.fetchall()]
    def_elims = sum(career.get(t, 1.0) for t in def_supps) / len(def_supps) if def_supps else 1.0

    # Get sprinter team
    opp_team = 2 if def_team == 1 else 1
    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = ? AND is_champion = 0', (match_id, opp_team))
    spr_supps = [r[0] for r in cursor.fetchall()]
    spr_elims = sum(career.get(t, 1.0) for t in spr_supps) / len(spr_supps) if spr_supps else 1.0

    diff = def_elims - spr_elims
    if diff >= 0.5:
        bucket = '+0.5+'
    elif diff >= 0:
        bucket = '0 to +0.5'
    elif diff >= -0.5:
        bucket = '-0.5 to 0'
    else:
        bucket = '-0.5-'

    buckets[bucket][0] += won
    buckets[bucket][1] += 1

print()
print('Elim Diff | Games | Def Wins | Def Win%')
print('-' * 45)
for bucket in ['+0.5+', '0 to +0.5', '-0.5 to 0', '-0.5-']:
    w, t = buckets[bucket]
    if t > 0:
        print(f'{bucket:<10} {t:<6} {w:<9} {100*w/t:.1f}%')

print()
print('=== KEY INSIGHT: Sprinters are fast wart riders ===')
print('Sprinters likely steal wart wins from Defenders, making elim advantage less predictive')

conn.close()
