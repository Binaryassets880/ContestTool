import sqlite3

conn = sqlite3.connect(r'c:\dev\GitHub\ContestTool\grandarena.db')
cursor = conn.cursor()

print('=== DEFENDER WIN RATE BY OWN vs OPPONENT SUPPORTER CAREER ELIMS ===')
print()

cursor.execute('''
    WITH career_stats AS (
        SELECT token_id, AVG(eliminations) as career_elims
        FROM performances GROUP BY token_id
    ),
    defender_games AS (
        SELECT m.match_id, mp.team,
            CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END as won
        FROM matches m
        JOIN match_players mp ON m.match_id = mp.match_id
        WHERE mp.is_champion = 1 AND mp.class = 'Defender' AND m.state = 'scored'
    ),
    team_career_elims AS (
        SELECT mp.match_id, mp.team, AVG(cs.career_elims) as team_career_elims
        FROM match_players mp
        JOIN career_stats cs ON mp.token_id = cs.token_id
        WHERE mp.is_champion = 0
        GROUP BY mp.match_id, mp.team
    )
    SELECT
        CASE WHEN own.team_career_elims >= 1.5 THEN 'High' ELSE 'Low' END as own_elims,
        CASE WHEN opp.team_career_elims >= 1.5 THEN 'High' ELSE 'Low' END as opp_elims,
        COUNT(*) as games,
        SUM(dg.won) as wins,
        ROUND(100.0 * SUM(dg.won) / COUNT(*), 1) as win_pct
    FROM defender_games dg
    JOIN team_career_elims own ON dg.match_id = own.match_id AND dg.team = own.team
    JOIN team_career_elims opp ON dg.match_id = opp.match_id AND dg.team != opp.team
    GROUP BY own_elims, opp_elims
    ORDER BY win_pct DESC
''')

print('Own Elims | Opp Elims | Games | Wins | Win%')
print('-' * 50)
for row in cursor.fetchall():
    print(f'{row[0]:<10} {row[1]:<10} {row[2]:<6} {row[3]:<5} {row[4]}%')

print()
print('=== WHAT ABOUT OPPONENT WART DISTANCE? ===')
print()

cursor.execute('''
    WITH career_stats AS (
        SELECT token_id, AVG(wart_distance) as career_wart
        FROM performances GROUP BY token_id
    ),
    defender_games AS (
        SELECT m.match_id, mp.team,
            CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END as won
        FROM matches m
        JOIN match_players mp ON m.match_id = mp.match_id
        WHERE mp.is_champion = 1 AND mp.class = 'Defender' AND m.state = 'scored'
    ),
    team_career_wart AS (
        SELECT mp.match_id, mp.team, AVG(cs.career_wart) as team_career_wart
        FROM match_players mp
        JOIN career_stats cs ON mp.token_id = cs.token_id
        WHERE mp.is_champion = 0
        GROUP BY mp.match_id, mp.team
    )
    SELECT
        CASE WHEN own.team_career_wart >= 50 THEN 'High' ELSE 'Low' END as own_wart,
        CASE WHEN opp.team_career_wart >= 50 THEN 'High' ELSE 'Low' END as opp_wart,
        COUNT(*) as games,
        SUM(dg.won) as wins,
        ROUND(100.0 * SUM(dg.won) / COUNT(*), 1) as win_pct
    FROM defender_games dg
    JOIN team_career_wart own ON dg.match_id = own.match_id AND dg.team = own.team
    JOIN team_career_wart opp ON dg.match_id = opp.match_id AND dg.team != opp.team
    GROUP BY own_wart, opp_wart
    ORDER BY win_pct DESC
''')

print('Own Wart  | Opp Wart  | Games | Wins | Win%')
print('-' * 50)
for row in cursor.fetchall():
    print(f'{row[0]:<10} {row[1]:<10} {row[2]:<6} {row[3]:<5} {row[4]}%')

print()
print('=== HIGH WR CHAMPIONS (60%+) vs LOW WR (<40%) - WHAT IS DIFFERENT? ===')
print()

cursor.execute('''
    WITH champ_wr AS (
        SELECT mp.token_id, mp.name, mp.class,
            COUNT(*) as games,
            SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM matches m
        JOIN match_players mp ON m.match_id = mp.match_id
        WHERE mp.is_champion = 1 AND m.state = 'scored'
        GROUP BY mp.token_id
        HAVING COUNT(*) >= 20
    ),
    career_stats AS (
        SELECT token_id, AVG(eliminations) as career_elims, AVG(deposits) as career_deps, AVG(wart_distance) as career_wart
        FROM performances GROUP BY token_id
    ),
    champ_supporter_avg AS (
        SELECT mp_champ.token_id as champ_id,
            AVG(cs.career_elims) as avg_supp_elims,
            AVG(cs.career_deps) as avg_supp_deps,
            AVG(cs.career_wart) as avg_supp_wart
        FROM match_players mp_champ
        JOIN match_players mp_supp ON mp_champ.match_id = mp_supp.match_id
            AND mp_champ.team = mp_supp.team AND mp_supp.is_champion = 0
        JOIN career_stats cs ON mp_supp.token_id = cs.token_id
        WHERE mp_champ.is_champion = 1
        GROUP BY mp_champ.token_id
    )
    SELECT
        CASE
            WHEN cw.win_pct >= 60 THEN 'High WR (60%+)'
            WHEN cw.win_pct < 40 THEN 'Low WR (<40%)'
            ELSE 'Medium WR'
        END as wr_group,
        cw.class,
        COUNT(*) as champs,
        ROUND(AVG(csa.avg_supp_elims), 2) as avg_supp_elims,
        ROUND(AVG(csa.avg_supp_deps), 2) as avg_supp_deps,
        ROUND(AVG(csa.avg_supp_wart), 2) as avg_supp_wart
    FROM champ_wr cw
    JOIN champ_supporter_avg csa ON cw.token_id = csa.champ_id
    WHERE cw.win_pct >= 60 OR cw.win_pct < 40
    GROUP BY wr_group, cw.class
    ORDER BY cw.class, wr_group
''')

print('WR Group       | Class     | Champs | Supp Elims | Supp Deps | Supp Wart')
print('-' * 75)
for row in cursor.fetchall():
    print(f'{row[0]:<15} {row[1]:<10} {row[2]:<7} {row[3]:<11} {row[4]:<10} {row[5]}')

print()
print('=== WIN RATE BY OPPONENT CLASS (for Defenders) ===')
print()

cursor.execute('''
    SELECT
        mp2.class as opp_class,
        COUNT(*) as games,
        SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) as wins,
        ROUND(100.0 * SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
    FROM matches m
    JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1 AND mp1.class = 'Defender'
    JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp1.team != mp2.team
    WHERE m.state = 'scored'
    GROUP BY opp_class
    ORDER BY win_pct DESC
''')

print('Opp Class    | Games | Wins | Win%')
print('-' * 45)
for row in cursor.fetchall():
    print(f'{row[0]:<13} {row[1]:<6} {row[2]:<5} {row[3]}%')

conn.close()
