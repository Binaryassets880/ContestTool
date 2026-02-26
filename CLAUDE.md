# Grand Arena Contest Tool

## Project Overview
A web tool for analyzing Moki champion matchups in the Grand Arena fantasy contest game. Users pick 4 champions + a scheme card, aiming for ~60% lineup win rate to place in contests.

## Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Static HTML + Tabulator.js (sortable/filterable tables)
- **Database**: SQLite (`grandarena.db`)
- **Styling**: Custom CSS with dark theme (#1a1a2e background, #00d4ff accent)

## Project Structure
```
ContestTool/
├── grandarena.db          # SQLite database (matches, players, performances)
├── champions.json         # Champion metadata with traits
├── schemes.json           # Scheme card definitions
├── requirements.txt       # fastapi, uvicorn, pydantic
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI routes
│   ├── database.py        # DB queries + MS calculation
│   └── static/
│       ├── index.html     # Main SPA with 3 tabs
│       ├── styles.css     # Dark theme styling
│       └── app.js         # Tabulator tables + API calls
```

## Database Schema

### matches
- `match_id` (TEXT PK) - MongoDB ObjectID format
- `game_type` (TEXT) - "mokiMayhem"
- `match_date` (TEXT) - "YYYY-MM-DD"
- `state` (TEXT) - "scheduled" or "scored"
- `team_won` (INT) - 1 or 2
- `win_type` (TEXT) - "eliminations", "gacha", "deposits"

### match_players
- `match_id` (TEXT FK)
- `token_id` (INT) - Moki NFT ID
- `team` (INT) - 1 or 2
- `name` (TEXT)
- `class` (TEXT) - Defender, Striker, Sprinter, Bruiser, etc.
- `is_champion` (INT) - 1 for champion, 0 for supporter

### performances
- `match_id` (TEXT FK)
- `token_id` (INT)
- `match_date` (TEXT)
- `eliminations` (REAL)
- `deposits` (REAL)
- `wart_distance` (REAL)

## Matchup Score (MS) Formula

Located in `app/database.py:calc_matchup_score()`

```python
score = base_win_rate  # Champion's historical win %

# Class matchup adjustment (capped ±10 pts)
class_adj = (class_matchup_winrate - 50) * 0.4
score += max(-10, min(10, class_adj))

# Elim differential (capped ±15 pts)
elim_diff = my_supporter_avg_elims - opp_supporter_avg_elims
score += max(-15, min(15, elim_diff * 10))

# Defender penalty
if my_class == "Defender" and my_supporter_avg_deps >= 1.5:
    score -= 3

return max(0, min(100, score))
```

**MS Interpretation (from backtesting):**
- MS 80+: ~75% win rate
- MS 70-79: ~76% win rate
- MS 60-69: ~69% win rate
- MS 50-59: ~61% win rate
- MS 40-49: ~57% win rate
- MS <40: ~51% win rate

## API Endpoints

### GET /api/upcoming
Returns champions with aggregated MS for scheduled games.

### GET /api/champions/{token_id}/matchups
Returns detailed per-game matchup breakdown with supporter info.

### GET /api/analysis?limit=2000
Returns historical games with **point-in-time** MS calculations for backtesting.
- Uses champion win rate from games BEFORE each match
- Uses supporter career stats from performances BEFORE each match
- This prevents lookahead bias in backtesting

### GET /api/schemes
Returns champions with matching scheme traits and MS data.

## Scheme Trait Matching

Schemes give bonus points when champions have specific traits. Defined in `SCHEME_TRAITS` dict in database.py.

Examples:
- "Costume Party": Onesie trait or specific head traits
- "Midnight Strike": Shadow trait
- "Golden Shower": Gold trait (excluding Gold Can, Gold Katana)
- "Call to Arms": Ronin or Samurai trait

## Key Implementation Details

### Point-in-Time Backtesting
The analysis tab calculates MS using only data available BEFORE each game was played. This required subqueries to filter by `match_date < ?` for:
1. Champion win rates
2. Supporter career eliminations/deposits

### Match ID Structure
MongoDB ObjectID format: first 8 hex chars = Unix timestamp (when record created).
Games on same day have sequential IDs - position determines order within day.

### Contest Time Blocks
- 9AM UTC (4AM EST)
- 5PM UTC (12PM EST)
- 1AM UTC (8PM EST)

## Running the App

```bash
cd ContestTool
pip install -r requirements.txt
uvicorn app.main:app --reload
# Open http://localhost:8000
```

## Frontend Features

### Upcoming Tab
- Table of champions sorted by expected wins
- Click row to expand matchup details with supporter stats
- Filter by class, search by name

### Schemes Tab
- Filter champions by scheme card compatibility
- Shows which trait-based schemes each champion qualifies for
- Click to see upcoming matchups

### Analysis Tab
- Historical game results with MS
- Bucket stats showing win rate by MS range
- Filter by result (W/L) and minimum MS

## Future/Hosting Plans
Considering GitHub Actions + GitHub Pages architecture:
- Actions runs hourly to pull match data
- Exports JSON files to Pages
- Vercel app fetches JSON over HTTPS
- Keep 7-14 day rolling window of match data

## Classes
Defender, Striker, Sprinter, Bruiser, Center, Grinder, Forward, Flanker, Support, Anchor
