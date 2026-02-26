import sqlite3
from pathlib import Path
from typing import Optional
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "grandarena.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def calc_matchup_score(
    base_wr: float,
    class_matchup: float,
    own_elims: float,
    own_deps: float,
    opp_elims: float,
    opp_deps: float,
    my_class: str = "Defender",
) -> float:
    """
    Calculate matchup score based on predictive factors.

    V2 - More conservative after real-world testing showed overconfidence.

    Key insight: Aggregate statistics don't translate directly to individual games.
    The formula now uses smaller coefficients and caps the impact of any single factor.
    """
    score = base_wr

    # Class matchup adjustment - capped at +/- 10 points
    class_adj = (class_matchup - 50) * 0.4
    class_adj = max(-10, min(10, class_adj))
    score += class_adj

    # Elim differential - reduced from 20 to 10 pts per 1.0 diff
    # Also capped at +/- 15 points to prevent extreme scores
    elim_diff = own_elims - opp_elims
    elim_adj = elim_diff * 10
    elim_adj = max(-15, min(15, elim_adj))
    score += elim_adj

    # Deposits penalty for Defenders (kept small)
    if my_class == "Defender" and own_deps >= 1.5:
        score -= 3

    # Clamp to 0-100 range
    return max(0, min(100, score))


def get_edge_label(score: float) -> str:
    if score >= 60:
        return "Favorable"
    elif score >= 40:
        return "Even"
    else:
        return "Tough"


def get_upcoming_summary() -> list[dict]:
    """Get all champions with their aggregated matchup scores for upcoming games."""
    conn = get_connection()
    cursor = conn.cursor()

    # Build temp tables for career stats and class matchups
    cursor.execute('''
        CREATE TEMP TABLE career_stats AS
        SELECT token_id, AVG(eliminations) as career_elims, AVG(deposits) as career_deps
        FROM performances GROUP BY token_id
    ''')

    cursor.execute('''
        CREATE TEMP TABLE class_matchups AS
        SELECT mp1.class as your_class, mp2.class as opp_class,
            ROUND(100.0 * SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM matches m
        JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1
        JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp1.team != mp2.team
        WHERE m.state = 'scored'
        GROUP BY mp1.class, mp2.class HAVING COUNT(*) >= 10
    ''')

    cursor.execute('''
        CREATE TEMP TABLE champ_winrates AS
        SELECT mp.token_id, mp.name, mp.class,
            ROUND(100.0 * SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM matches m
        JOIN match_players mp ON m.match_id = mp.match_id
        WHERE mp.is_champion = 1 AND m.state = 'scored'
        GROUP BY mp.token_id
    ''')

    # Get all scheduled matchups
    cursor.execute('''
        WITH scheduled_champs AS (
            SELECT m.match_id, m.match_date, mp.team, mp.token_id, mp.name, mp.class
            FROM matches m JOIN match_players mp ON m.match_id = mp.match_id
            WHERE m.state = 'scheduled' AND mp.is_champion = 1
        ),
        team_supporter_stats AS (
            SELECT mp.match_id, mp.team,
                AVG(COALESCE(cs.career_elims, 1.0)) as avg_supp_elims,
                AVG(COALESCE(cs.career_deps, 1.5)) as avg_supp_deps
            FROM match_players mp
            LEFT JOIN career_stats cs ON mp.token_id = cs.token_id
            WHERE mp.is_champion = 0
            GROUP BY mp.match_id, mp.team
        )
        SELECT sc1.token_id, sc1.name, sc1.class, COALESCE(cw1.win_pct, 50.0) as base_wr,
            tss1.avg_supp_elims, tss1.avg_supp_deps,
            sc2.name as opp_name, sc2.class as opp_class, COALESCE(cw2.win_pct, 50.0) as opp_wr,
            tss2.avg_supp_elims as opp_supp_elims, tss2.avg_supp_deps as opp_supp_deps,
            COALESCE(cm.win_pct, 50.0) as class_matchup
        FROM scheduled_champs sc1
        JOIN scheduled_champs sc2 ON sc1.match_id = sc2.match_id AND sc1.team = 1 AND sc2.team = 2
        LEFT JOIN champ_winrates cw1 ON sc1.token_id = cw1.token_id
        LEFT JOIN champ_winrates cw2 ON sc2.token_id = cw2.token_id
        LEFT JOIN team_supporter_stats tss1 ON sc1.match_id = tss1.match_id AND sc1.team = tss1.team
        LEFT JOIN team_supporter_stats tss2 ON sc2.match_id = tss2.match_id AND sc2.team = tss2.team
        LEFT JOIN class_matchups cm ON sc1.class = cm.your_class AND sc2.class = cm.opp_class
    ''')

    rows = cursor.fetchall()

    # Aggregate scores by champion
    champ_scores: dict[tuple, list[float]] = defaultdict(list)
    champ_info: dict[int, dict] = {}

    for row in rows:
        token_id = row['token_id']
        base_wr = row['base_wr']

        score = calc_matchup_score(
            base_wr,
            row['class_matchup'],
            row['avg_supp_elims'] or 1.0,
            row['avg_supp_deps'] or 1.5,
            row['opp_supp_elims'] or 1.0,
            row['opp_supp_deps'] or 1.5,
            my_class=row['class']
        )
        champ_scores[token_id].append(score)

        if token_id not in champ_info:
            champ_info[token_id] = {
                'token_id': token_id,
                'name': row['name'],
                'class': row['class'],
                'base_win_rate': base_wr
            }

        # Also process the reverse matchup (team 2's perspective)
        # We need to query team 2 champions separately, so let's skip for now
        # and handle it in a second pass

    # Second query for team 2 champions
    cursor.execute('''
        WITH scheduled_champs AS (
            SELECT m.match_id, m.match_date, mp.team, mp.token_id, mp.name, mp.class
            FROM matches m JOIN match_players mp ON m.match_id = mp.match_id
            WHERE m.state = 'scheduled' AND mp.is_champion = 1
        ),
        team_supporter_stats AS (
            SELECT mp.match_id, mp.team,
                AVG(COALESCE(cs.career_elims, 1.0)) as avg_supp_elims,
                AVG(COALESCE(cs.career_deps, 1.5)) as avg_supp_deps
            FROM match_players mp
            LEFT JOIN career_stats cs ON mp.token_id = cs.token_id
            WHERE mp.is_champion = 0
            GROUP BY mp.match_id, mp.team
        )
        SELECT sc2.token_id, sc2.name, sc2.class, COALESCE(cw2.win_pct, 50.0) as base_wr,
            tss2.avg_supp_elims, tss2.avg_supp_deps,
            sc1.name as opp_name, sc1.class as opp_class, COALESCE(cw1.win_pct, 50.0) as opp_wr,
            tss1.avg_supp_elims as opp_supp_elims, tss1.avg_supp_deps as opp_supp_deps,
            COALESCE(cm.win_pct, 50.0) as class_matchup
        FROM scheduled_champs sc1
        JOIN scheduled_champs sc2 ON sc1.match_id = sc2.match_id AND sc1.team = 1 AND sc2.team = 2
        LEFT JOIN champ_winrates cw1 ON sc1.token_id = cw1.token_id
        LEFT JOIN champ_winrates cw2 ON sc2.token_id = cw2.token_id
        LEFT JOIN team_supporter_stats tss1 ON sc1.match_id = tss1.match_id AND sc1.team = tss1.team
        LEFT JOIN team_supporter_stats tss2 ON sc2.match_id = tss2.match_id AND sc2.team = tss2.team
        LEFT JOIN class_matchups cm ON sc2.class = cm.your_class AND sc1.class = cm.opp_class
    ''')

    for row in cursor.fetchall():
        token_id = row['token_id']
        base_wr = row['base_wr']

        score = calc_matchup_score(
            base_wr,
            row['class_matchup'],
            row['avg_supp_elims'] or 1.0,
            row['avg_supp_deps'] or 1.5,
            row['opp_supp_elims'] or 1.0,
            row['opp_supp_deps'] or 1.5,
            my_class=row['class']
        )
        champ_scores[token_id].append(score)

        if token_id not in champ_info:
            champ_info[token_id] = {
                'token_id': token_id,
                'name': row['name'],
                'class': row['class'],
                'base_win_rate': base_wr
            }

    conn.close()

    # Build final results
    results = []
    for token_id, scores in champ_scores.items():
        info = champ_info[token_id]
        # Expected wins = sum of win probabilities (score/100 for each game)
        expected_wins = sum(s / 100 for s in scores)
        results.append({
            **info,
            'games': len(scores),
            'avg_score': round(sum(scores) / len(scores), 1),
            'expected_wins': round(expected_wins, 1),
            'favorable': sum(1 for s in scores if s >= 60),
            'unfavorable': sum(1 for s in scores if s < 40)
        })

    return sorted(results, key=lambda x: x['expected_wins'], reverse=True)


def get_champion_matchups(token_id: int) -> Optional[dict]:
    """Get detailed matchup breakdown for a specific champion."""
    conn = get_connection()
    cursor = conn.cursor()

    # Build temp tables
    cursor.execute('''
        CREATE TEMP TABLE career_stats AS
        SELECT token_id,
            AVG(eliminations) as career_elims,
            AVG(deposits) as career_deps,
            AVG(wart_distance) as career_wart
        FROM performances GROUP BY token_id
    ''')

    cursor.execute('''
        CREATE TEMP TABLE class_matchups AS
        SELECT mp1.class as your_class, mp2.class as opp_class,
            ROUND(100.0 * SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM matches m
        JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1
        JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp1.team != mp2.team
        WHERE m.state = 'scored'
        GROUP BY mp1.class, mp2.class HAVING COUNT(*) >= 10
    ''')

    cursor.execute('''
        CREATE TEMP TABLE champ_winrates AS
        SELECT mp.token_id, mp.name, mp.class,
            ROUND(100.0 * SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM matches m
        JOIN match_players mp ON m.match_id = mp.match_id
        WHERE mp.is_champion = 1 AND m.state = 'scored'
        GROUP BY mp.token_id
    ''')

    # Get champion info
    cursor.execute('''
        SELECT token_id, name, class, win_pct
        FROM champ_winrates WHERE token_id = ?
    ''', (token_id,))

    champ_row = cursor.fetchone()
    if not champ_row:
        conn.close()
        return None

    champion = {
        'token_id': champ_row['token_id'],
        'name': champ_row['name'],
        'class': champ_row['class'],
        'base_win_rate': champ_row['win_pct']
    }

    # Get detailed matchups
    cursor.execute('''
        WITH my_matches AS (
            SELECT m.match_id, m.match_date, mp.team
            FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE m.state = 'scheduled' AND mp.is_champion = 1 AND mp.token_id = ?
        ),
        opponent_info AS (
            SELECT mm.match_id, mm.match_date, mm.team as my_team,
                mp.token_id as opp_token, mp.name as opp_name, mp.class as opp_class, mp.team as opp_team
            FROM my_matches mm
            JOIN match_players mp ON mm.match_id = mp.match_id AND mp.is_champion = 1 AND mp.team != mm.team
        ),
        my_supporters AS (
            SELECT mm.match_id,
                mp.token_id as supp_token,
                mp.name as supp_name, mp.class as supp_class,
                COALESCE(cs.career_elims, 1.0) as career_elims,
                COALESCE(cs.career_deps, 1.5) as career_deps,
                COALESCE(cs.career_wart, 0.0) as career_wart
            FROM my_matches mm
            JOIN match_players mp ON mm.match_id = mp.match_id AND mp.team = mm.team AND mp.is_champion = 0
            LEFT JOIN career_stats cs ON mp.token_id = cs.token_id
        ),
        opp_supporters AS (
            SELECT oi.match_id,
                mp.token_id as supp_token,
                mp.name as supp_name, mp.class as supp_class,
                COALESCE(cs.career_elims, 1.0) as career_elims,
                COALESCE(cs.career_deps, 1.5) as career_deps,
                COALESCE(cs.career_wart, 0.0) as career_wart
            FROM opponent_info oi
            JOIN match_players mp ON oi.match_id = mp.match_id AND mp.team = oi.opp_team AND mp.is_champion = 0
            LEFT JOIN career_stats cs ON mp.token_id = cs.token_id
        ),
        my_supp_agg AS (
            SELECT match_id, AVG(career_elims) as avg_elims, AVG(career_deps) as avg_deps
            FROM my_supporters GROUP BY match_id
        ),
        opp_supp_agg AS (
            SELECT match_id, AVG(career_elims) as avg_elims, AVG(career_deps) as avg_deps
            FROM opp_supporters GROUP BY match_id
        )
        SELECT
            oi.match_id, oi.match_date, oi.opp_name, oi.opp_class,
            COALESCE(cw.win_pct, 50.0) as opp_win_rate,
            msa.avg_elims as my_avg_elims, msa.avg_deps as my_avg_deps,
            osa.avg_elims as opp_avg_elims, osa.avg_deps as opp_avg_deps,
            COALESCE(cm.win_pct, 50.0) as class_matchup
        FROM opponent_info oi
        LEFT JOIN champ_winrates cw ON oi.opp_token = cw.token_id
        LEFT JOIN my_supp_agg msa ON oi.match_id = msa.match_id
        LEFT JOIN opp_supp_agg osa ON oi.match_id = osa.match_id
        LEFT JOIN class_matchups cm ON ? = cm.your_class AND oi.opp_class = cm.opp_class
        ORDER BY oi.match_date
    ''', (token_id, champion['class']))

    matchup_rows = cursor.fetchall()

    # Get supporter details for each match
    matchups = []
    for row in matchup_rows:
        match_id = row['match_id']

        # Get my supporters
        cursor.execute('''
            SELECT mp.token_id, mp.name, mp.class,
                COALESCE(cs.career_elims, 1.0) as career_elims,
                COALESCE(cs.career_deps, 1.5) as career_deps,
                COALESCE(cs.career_wart, 0.0) as career_wart
            FROM match_players mp
            LEFT JOIN career_stats cs ON mp.token_id = cs.token_id
            WHERE mp.match_id = ? AND mp.is_champion = 0
            AND mp.team = (SELECT team FROM match_players WHERE match_id = ? AND token_id = ?)
        ''', (match_id, match_id, token_id))
        my_supporters = [dict(r) for r in cursor.fetchall()]

        # Get opponent supporters
        cursor.execute('''
            SELECT mp.token_id, mp.name, mp.class,
                COALESCE(cs.career_elims, 1.0) as career_elims,
                COALESCE(cs.career_deps, 1.5) as career_deps,
                COALESCE(cs.career_wart, 0.0) as career_wart
            FROM match_players mp
            LEFT JOIN career_stats cs ON mp.token_id = cs.token_id
            WHERE mp.match_id = ? AND mp.is_champion = 0
            AND mp.team != (SELECT team FROM match_players WHERE match_id = ? AND token_id = ?)
        ''', (match_id, match_id, token_id))
        opp_supporters = [dict(r) for r in cursor.fetchall()]

        score = calc_matchup_score(
            champion['base_win_rate'],
            row['class_matchup'],
            row['my_avg_elims'] or 1.0,
            row['my_avg_deps'] or 1.5,
            row['opp_avg_elims'] or 1.0,
            row['opp_avg_deps'] or 1.5,
            my_class=champion['class']
        )

        matchups.append({
            'date': row['match_date'],
            'opponent': row['opp_name'],
            'opponent_class': row['opp_class'],
            'opponent_win_rate': row['opp_win_rate'],
            'my_supporters': my_supporters,
            'opp_supporters': opp_supporters,
            'my_avg_elims': round(row['my_avg_elims'] or 1.0, 2),
            'my_avg_deps': round(row['my_avg_deps'] or 1.5, 2),
            'opp_avg_elims': round(row['opp_avg_elims'] or 1.0, 2),
            'opp_avg_deps': round(row['opp_avg_deps'] or 1.5, 2),
            'score': round(score, 1),
            'edge': get_edge_label(score)
        })

    conn.close()

    return {
        'champion': champion,
        'matchups': matchups
    }


def get_historical_analysis(limit: int = 1000) -> dict:
    """
    Analyze historical games with calculated matchup scores.
    Uses POINT-IN-TIME data: for each game, calculates MS using only
    data that was available BEFORE that game was played.
    Returns games and win rate statistics by MS bucket.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Class matchups can use all data (relatively stable over time)
    cursor.execute('''
        CREATE TEMP TABLE class_matchups AS
        SELECT mp1.class as your_class, mp2.class as opp_class,
            ROUND(100.0 * SUM(CASE WHEN m.team_won = mp1.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
        FROM matches m
        JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1
        JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp1.team != mp2.team
        WHERE m.state = 'scored'
        GROUP BY mp1.class, mp2.class HAVING COUNT(*) >= 10
    ''')

    # Get historical games with basic info
    cursor.execute('''
        SELECT m.match_id, m.match_date, m.team_won, m.win_type,
            mp1.token_id as t1_id, mp1.name as t1_name, mp1.class as t1_class, mp1.team as t1_team,
            mp2.token_id as t2_id, mp2.name as t2_name, mp2.class as t2_class, mp2.team as t2_team,
            COALESCE(cm.win_pct, 50.0) as t1_class_matchup
        FROM matches m
        JOIN match_players mp1 ON m.match_id = mp1.match_id AND mp1.is_champion = 1 AND mp1.team = 1
        JOIN match_players mp2 ON m.match_id = mp2.match_id AND mp2.is_champion = 1 AND mp2.team = 2
        LEFT JOIN class_matchups cm ON mp1.class = cm.your_class AND mp2.class = cm.opp_class
        WHERE m.state = 'scored'
        ORDER BY m.match_date DESC
        LIMIT ?
    ''', (limit,))

    match_rows = cursor.fetchall()

    games = []
    ms_buckets = {
        '80+': {'wins': 0, 'total': 0},
        '70-79': {'wins': 0, 'total': 0},
        '60-69': {'wins': 0, 'total': 0},
        '50-59': {'wins': 0, 'total': 0},
        '40-49': {'wins': 0, 'total': 0},
        '<40': {'wins': 0, 'total': 0},
    }

    for row in match_rows:
        match_id = row['match_id']
        match_date = row['match_date']

        # Get champion's POINT-IN-TIME win rate (games before this match)
        cursor.execute('''
            SELECT ROUND(100.0 * SUM(CASE WHEN m.team_won = mp.team THEN 1 ELSE 0 END) / COUNT(*), 1) as win_pct
            FROM matches m
            JOIN match_players mp ON m.match_id = mp.match_id
            WHERE mp.token_id = ? AND mp.is_champion = 1 AND m.state = 'scored' AND m.match_date < ?
        ''', (row['t1_id'], match_date))
        t1_wr_row = cursor.fetchone()
        t1_wr = t1_wr_row['win_pct'] if t1_wr_row and t1_wr_row['win_pct'] else 50.0

        # Get team 1 supporters' POINT-IN-TIME career stats (performances before this match)
        cursor.execute('''
            SELECT AVG(COALESCE(
                (SELECT AVG(p.eliminations) FROM performances p WHERE p.token_id = mp.token_id AND p.match_date < ?),
                1.0
            )) as avg_elims,
            AVG(COALESCE(
                (SELECT AVG(p.deposits) FROM performances p WHERE p.token_id = mp.token_id AND p.match_date < ?),
                1.5
            )) as avg_deps
            FROM match_players mp
            WHERE mp.match_id = ? AND mp.team = 1 AND mp.is_champion = 0
        ''', (match_date, match_date, match_id))
        t1_supps = cursor.fetchone()

        # Get team 2 supporters' POINT-IN-TIME career stats
        cursor.execute('''
            SELECT AVG(COALESCE(
                (SELECT AVG(p.eliminations) FROM performances p WHERE p.token_id = mp.token_id AND p.match_date < ?),
                1.0
            )) as avg_elims,
            AVG(COALESCE(
                (SELECT AVG(p.deposits) FROM performances p WHERE p.token_id = mp.token_id AND p.match_date < ?),
                1.5
            )) as avg_deps
            FROM match_players mp
            WHERE mp.match_id = ? AND mp.team = 2 AND mp.is_champion = 0
        ''', (match_date, match_date, match_id))
        t2_supps = cursor.fetchone()

        # Calculate matchup score for team 1
        t1_score = calc_matchup_score(
            t1_wr,
            row['t1_class_matchup'],
            t1_supps['avg_elims'] or 1.0,
            t1_supps['avg_deps'] or 1.5,
            t2_supps['avg_elims'] or 1.0,
            t2_supps['avg_deps'] or 1.5,
            my_class=row['t1_class']
        )

        t1_won = row['team_won'] == 1

        # Track by bucket
        if t1_score >= 80:
            bucket = '80+'
        elif t1_score >= 70:
            bucket = '70-79'
        elif t1_score >= 60:
            bucket = '60-69'
        elif t1_score >= 50:
            bucket = '50-59'
        elif t1_score >= 40:
            bucket = '40-49'
        else:
            bucket = '<40'

        ms_buckets[bucket]['total'] += 1
        if t1_won:
            ms_buckets[bucket]['wins'] += 1

        games.append({
            'match_id': match_id,
            'date': row['match_date'],
            'champion': row['t1_name'],
            'champion_class': row['t1_class'],
            'opponent': row['t2_name'],
            'opponent_class': row['t2_class'],
            'matchup_score': round(t1_score, 1),
            'result': 'W' if t1_won else 'L',
            'win_type': row['win_type']
        })

    conn.close()

    # Calculate win rates for each bucket
    bucket_stats = []
    for bucket_name in ['80+', '70-79', '60-69', '50-59', '40-49', '<40']:
        bucket = ms_buckets[bucket_name]
        if bucket['total'] > 0:
            win_rate = round(100 * bucket['wins'] / bucket['total'], 1)
        else:
            win_rate = 0
        bucket_stats.append({
            'range': bucket_name,
            'games': bucket['total'],
            'wins': bucket['wins'],
            'win_rate': win_rate
        })

    return {
        'games': games,
        'bucket_stats': bucket_stats
    }


# Scheme trait requirements mapping
SCHEME_TRAITS = {
    "Costume Party": {
        "contains": ["Onesie"],
        "exact": ["Lemon Head", "Kappa Head", "Tomato Head", "Bear Head", "Frog Head", "Blob Head"]
    },
    "Shapeshifting": {
        "contains": ["Tongue Out"],
        "exact": ["Tanuki Mask", "Kitsune Mask", "Cat Mask"]
    },
    "Midnight Strike": {
        "contains": ["Shadow"]
    },
    "Dress to Impress": {
        "contains": ["Kimono"]
    },
    "Housekeeping": {
        "contains": ["Apron"],
        "exact": ["Garbage Can", "Gold Can", "Toilet Paper"]
    },
    "Dungaree Duel": {
        "exact": ["Pink Overalls", "Blue Overalls", "Green Overalls"]
    },
    "Tear Jerking": {
        "contains": ["Crying"]
    },
    "Golden Shower": {
        "contains": ["Gold"],
        "exclude": ["Gold Can", "Gold Katana"]  # Only fur, not items
    },
    "Rainbow Riot": {
        "contains": ["Rainbow"]
    },
    "Divine Intervention": {
        "contains": ["Spirit"]
    },
    "Whale Watching": {
        "exact": ["1 of 1"]
    },
    "Call to Arms": {
        "exact": ["Ronin", "Samurai"]
    },
    "Malicious Intent": {
        "contains": ["Devious"],
        "exact": ["Oni Mask", "Tengu Mask", "Skull Mask"]
    }
}


def champion_matches_scheme(traits: list[str], scheme_name: str) -> bool:
    """Check if a champion's traits match a scheme's requirements."""
    if scheme_name not in SCHEME_TRAITS:
        return False

    rules = SCHEME_TRAITS[scheme_name]
    traits_lower = [t.lower() for t in traits]
    traits_str = " ".join(traits_lower)

    # Check "contains" rules (partial match)
    if "contains" in rules:
        for pattern in rules["contains"]:
            if pattern.lower() in traits_str:
                # Check exclusions
                if "exclude" in rules:
                    excluded = False
                    for excl in rules["exclude"]:
                        if excl.lower() in traits_str:
                            excluded = True
                            break
                    if not excluded:
                        return True
                else:
                    return True

    # Check "exact" rules (exact trait match)
    if "exact" in rules:
        for exact_trait in rules["exact"]:
            if exact_trait.lower() in traits_lower:
                return True

    return False


def get_schemes_data() -> dict:
    """Get champions with their matching schemes and avg MS."""
    import json

    # Load champions data
    champions_path = Path(__file__).parent.parent / "champions.json"
    with open(champions_path, 'r') as f:
        champions = json.load(f)

    # Build champion traits lookup
    champion_traits = {c['id']: c['traits'] for c in champions}
    champion_names = {c['id']: c['name'] for c in champions}

    # Get upcoming summary for MS data
    upcoming = get_upcoming_summary()
    upcoming_by_id = {c['token_id']: c for c in upcoming}

    # Build results
    results = []
    scheme_names = list(SCHEME_TRAITS.keys())

    for champ in champions:
        token_id = champ['id']
        traits = champ['traits']

        # Find matching schemes
        matching_schemes = []
        for scheme_name in scheme_names:
            if champion_matches_scheme(traits, scheme_name):
                matching_schemes.append(scheme_name)

        # Get MS data if available
        upcoming_data = upcoming_by_id.get(token_id)

        if upcoming_data:
            results.append({
                'token_id': token_id,
                'name': champ['name'],
                'class': upcoming_data['class'],
                'matching_schemes': matching_schemes,
                'games': upcoming_data['games'],
                'avg_score': upcoming_data['avg_score'],
                'expected_wins': upcoming_data['expected_wins'],
                'has_upcoming': True
            })
        else:
            # Champion has no upcoming games
            champ_class = traits[0] if traits else 'Unknown'
            results.append({
                'token_id': token_id,
                'name': champ['name'],
                'class': champ_class,
                'matching_schemes': matching_schemes,
                'games': 0,
                'avg_score': 0,
                'expected_wins': 0,
                'has_upcoming': False
            })

    # Sort by avg_score descending (best matchups first)
    results.sort(key=lambda x: (x['has_upcoming'], x['avg_score']), reverse=True)

    return {
        'champions': results,
        'schemes': scheme_names
    }
