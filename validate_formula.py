"""
Validate the new matchup scoring formula against actual game results.
This tests how well the formula predicts wins.
"""
import sqlite3
conn = sqlite3.connect('grandarena.db')
cursor = conn.cursor()

# Get career stats
cursor.execute('SELECT token_id, AVG(eliminations) as career_elims, AVG(deposits) as career_deps FROM performances GROUP BY token_id')
career_stats = {row[0]: {'elims': row[1], 'deps': row[2]} for row in cursor.fetchall()}

# Get class matchup win rates
cursor.execute('''
    SELECT mp1.class as your_class, mp2.class as opp_class,
        ROUND(100.0 * SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
    FROM matches m
    JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1
    JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp1.team != mp2.team
    WHERE m.state = 'scored'
    GROUP BY mp1.class, mp2.class HAVING COUNT(*) >= 10
''')
class_matchups = {}
for row in cursor.fetchall():
    class_matchups[(row[0], row[1])] = row[2]

# Get champion win rates
cursor.execute('''
    SELECT mp.token_id,
        ROUND(100.0 * SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
    FROM matches m
    JOIN match_players mp ON m.match_id = mp.match_id
    WHERE mp.is_champion = 1 AND m.state = 'scored'
    GROUP BY mp.token_id
''')
champ_winrates = {row[0]: row[1] for row in cursor.fetchall()}

def calc_matchup_score(base_wr, class_matchup, own_elims, own_deps, opp_elims, opp_deps, my_class):
    """New scoring formula"""
    score = base_wr
    score += (class_matchup - 50) * 0.5  # Class matchup adjustment

    # Elim differential - key predictor (20 points per 1.0 diff)
    elim_diff = own_elims - opp_elims
    score += elim_diff * 20

    # Deposits penalty for Defenders with gacha-focused teams
    if my_class == "Defender" and own_deps >= 1.5:
        score -= 5

    return max(0, min(100, score))

# Get recent scored games for validation
cursor.execute('''
    SELECT m.match_id, m.team_won,
        mp1.token_id as t1_champ, mp1.class as t1_class, mp1.team as t1_team,
        mp2.token_id as t2_champ, mp2.class as t2_class, mp2.team as t2_team
    FROM matches m
    JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1 AND mp1.team = 1
    JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp2.team = 2
    WHERE m.state = 'scored'
    ORDER BY m.match_date DESC
    LIMIT 500
''')

games = cursor.fetchall()
predictions = []

for game in games:
    match_id, team_won, t1_champ, t1_class, t1_team, t2_champ, t2_class, t2_team = game

    # Get team 1 supporters
    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = 1 AND is_champion = 0', (match_id,))
    t1_supps = [r[0] for r in cursor.fetchall()]
    t1_elims = sum(career_stats.get(t, {}).get('elims', 1.0) for t in t1_supps) / len(t1_supps) if t1_supps else 1.0
    t1_deps = sum(career_stats.get(t, {}).get('deps', 1.5) for t in t1_supps) / len(t1_supps) if t1_supps else 1.5

    # Get team 2 supporters
    cursor.execute('SELECT token_id FROM match_players WHERE match_id = ? AND team = 2 AND is_champion = 0', (match_id,))
    t2_supps = [r[0] for r in cursor.fetchall()]
    t2_elims = sum(career_stats.get(t, {}).get('elims', 1.0) for t in t2_supps) / len(t2_supps) if t2_supps else 1.0
    t2_deps = sum(career_stats.get(t, {}).get('deps', 1.5) for t in t2_supps) / len(t2_supps) if t2_supps else 1.5

    # Calculate scores
    t1_base_wr = champ_winrates.get(t1_champ, 50.0)
    t2_base_wr = champ_winrates.get(t2_champ, 50.0)
    t1_class_matchup = class_matchups.get((t1_class, t2_class), 50.0)
    t2_class_matchup = class_matchups.get((t2_class, t1_class), 50.0)

    t1_score = calc_matchup_score(t1_base_wr, t1_class_matchup, t1_elims, t1_deps, t2_elims, t2_deps, t1_class)
    t2_score = calc_matchup_score(t2_base_wr, t2_class_matchup, t2_elims, t2_deps, t1_elims, t1_deps, t2_class)

    t1_won = team_won == 1
    t1_predicted_fav = t1_score > t2_score
    correct = t1_won == t1_predicted_fav

    predictions.append({
        'match_id': match_id,
        't1_score': t1_score,
        't2_score': t2_score,
        't1_won': t1_won,
        't1_predicted_fav': t1_predicted_fav,
        'correct': correct,
        'score_diff': abs(t1_score - t2_score),
        't1_class': t1_class,
        't2_class': t2_class
    })

# Analyze prediction accuracy
total = len(predictions)
correct = sum(1 for p in predictions if p['correct'])
print(f'=== FORMULA VALIDATION (Last {total} Games) ===')
print()
print(f'Overall Accuracy: {correct}/{total} ({100*correct/total:.1f}%)')
print()

# By confidence level (score difference)
print('=== ACCURACY BY CONFIDENCE LEVEL ===')
print()
buckets = [
    ('High confidence (>20 pts)', lambda p: p['score_diff'] > 20),
    ('Medium confidence (10-20 pts)', lambda p: 10 < p['score_diff'] <= 20),
    ('Low confidence (5-10 pts)', lambda p: 5 < p['score_diff'] <= 10),
    ('Toss-up (<5 pts)', lambda p: p['score_diff'] <= 5),
]

for name, filter_fn in buckets:
    filtered = [p for p in predictions if filter_fn(p)]
    if filtered:
        acc = sum(1 for p in filtered if p['correct']) / len(filtered)
        print(f'{name}: {len(filtered)} games, {100*acc:.1f}% accuracy')

# By champion class
print()
print('=== ACCURACY BY DEFENDER VS OPPONENT CLASS ===')
print()

for opp_class in ['Striker', 'Bruiser', 'Defender', 'Sprinter', 'Center']:
    # Games where a Defender faces this class
    filtered = [p for p in predictions if
                (p['t1_class'] == 'Defender' and p['t2_class'] == opp_class) or
                (p['t2_class'] == 'Defender' and p['t1_class'] == opp_class)]
    if filtered:
        acc = sum(1 for p in filtered if p['correct']) / len(filtered)
        print(f'Defender vs {opp_class}: {len(filtered)} games, {100*acc:.1f}% accuracy')

conn.close()
