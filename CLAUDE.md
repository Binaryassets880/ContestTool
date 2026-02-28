# Grand Arena Contest Tool

## Project Overview
A web tool for analyzing Moki champion matchups in the Grand Arena fantasy contest game. Users pick 4 champions + a scheme card, aiming for ~60% lineup win rate to place in contests.

## Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Static HTML + Tabulator.js (sortable/filterable tables)
- **Data Source**: Remote GitHub Pages JSON/GZIP feed (replaces local SQLite)
- **Caching**: In-memory TTL cache (10 min) with stale-while-revalidate
- **Hosting**: Railway (container-based, always-on)
- **Styling**: Custom CSS with dark theme (#1a1a2e background, #00d4ff accent)

## Project Structure
```
ContestTool/
├── champions.json         # Champion metadata with traits (local)
├── schemes.json           # Scheme card definitions (local)
├── FANTASY.md             # Fantasy points scoring reference
├── requirements.txt       # fastapi, uvicorn, pydantic, httpx
├── Procfile               # Railway deployment command
├── runtime.txt            # Python version for Railway
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI routes with lifespan management
│   ├── database.py        # DEPRECATED - SQLite fallback
│   ├── feed/              # Remote feed infrastructure
│   │   ├── __init__.py    # FeedCoordinator singleton
│   │   ├── config.py      # Environment-based settings
│   │   ├── client.py      # Async HTTP client (httpx + gzip)
│   │   ├── cache.py       # TTL cache with stale-while-revalidate
│   │   ├── store.py       # In-memory data store + indexes
│   │   └── exceptions.py  # FeedUnavailableError
│   ├── queries/           # Feed-backed query implementations
│   │   ├── __init__.py
│   │   ├── scoring.py     # calc_matchup_score formula
│   │   ├── fantasy.py     # Fantasy point calculations
│   │   ├── upcoming.py    # get_upcoming_summary()
│   │   ├── champion_matchups.py
│   │   ├── historical.py  # Point-in-time analysis with FP
│   │   ├── schemes.py     # Scheme trait matching
│   │   └── class_changes.py  # Track champion class changes
│   └── static/
│       ├── index.html     # Main SPA with 4 tabs
│       ├── styles.css     # Dark theme styling
│       └── app.js         # Tabulator tables + API calls
```

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `FEED_BASE_URL` | flowbot44.github.io/... | GitHub Pages feed URL |
| `FEED_TTL_SECONDS` | 600 | Cache TTL (10 min) |
| `FEED_HTTP_TIMEOUT_SECONDS` | 30 | HTTP request timeout |
| `FEED_MAX_PARTITIONS` | 14 | Max partition days to load |

## Remote Feed Structure
Base URL: `https://flowbot44.github.io/grand-arena-builder-skill/data`

- `latest.json` - Manifest with partition list
- `partitions/raw_matches_YYYY-MM-DD.json.gz` - Match data per day
- `cumulative/current_totals.json.gz` - Career stat aggregates

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

Located in `app/queries/scoring.py:calc_matchup_score()`

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

**MS Interpretation**: Higher MS = better win probability. Actual win rates by MS bucket are displayed dynamically on the Analysis tab based on historical data.

## Fantasy Points (FP) System

Located in `app/queries/fantasy.py`. Only **champions** score fantasy points (not supporters).

**Scoring Formula:**
| Stat | Points |
|------|--------|
| Eliminations | 80 pts each |
| Deposits | 50 pts each |
| Wart Distance | 0.5625 pts/unit (45 per 80) |
| Victory | 300 pts |

**Projected FP** = Career avg stats + (MS/100 × 300 win bonus)
**Actual FP** = Game stats + 300 if won

See `FANTASY.md` for detailed documentation.

## API Endpoints

### GET /api/upcoming
Returns champions with aggregated MS and projected FP for scheduled games.
- Includes `avg_proj_fp` and `total_proj_fp` fields

### GET /api/champions/{token_id}/matchups
Returns detailed per-game matchup breakdown with supporter info and `proj_fp`.

### GET /api/analysis
Returns historical games with **point-in-time** MS and FP calculations for backtesting.
- Default limit: 50000 (configurable via `?limit=N`)
- Uses champion win rate from games BEFORE each match
- Uses supporter career stats from performances BEFORE each match
- This prevents lookahead bias in backtesting
- **Both perspectives**: Each match appears twice (once for each champion's view)
- Search filter only matches Champion column (to see that champion's matchups)
- Includes `proj_fp`, `actual_fp`, and `fp_diff` per game
- Returns `bucket_stats` (win rates by MS range) and `fp_stats` (avg projected/actual FP)

### GET /api/schemes
Returns champions with matching scheme traits and MS data.

### GET /api/class-changes
Returns champions who have changed classes, with old/new class and change date.

## Scheme Trait Matching

Schemes give bonus points when champions have specific traits. Defined in `SCHEME_TRAITS` dict in `app/queries/schemes.py`.

Examples:
- "Costume Party": Onesie trait or specific head traits
- "Midnight Strike": Shadow trait
- "Golden Shower": Gold trait (excluding Gold Can, Gold Katana)
- "Call to Arms": Ronin or Samurai trait

## Key Implementation Details

### Point-in-Time Backtesting
The analysis tab calculates MS and FP using only data available BEFORE each game was played:
1. Champion win rates (from games before that date)
2. Supporter career eliminations/deposits (from performances before that date)
3. Champion career stats for FP projection

### Class Change Tracking
Class history is tracked from **scored matches only** (not scheduled) to ensure accurate change dates. The `store.py` tracks `class_history` per token_id with `(class, first_seen_date)` tuples.

### Match ID Structure
MongoDB ObjectID format: first 8 hex chars = Unix timestamp (when record created).
Games on same day have sequential IDs - position determines order within day.

### Contest Time Blocks
- 9AM UTC (4AM EST)
- 5PM UTC (12PM EST)
- 1AM UTC (8PM EST)

### Detail Panel Positioning
Detail panels are positioned below tables (not inserted into Tabulator's DOM) to avoid clipping issues when tables are filtered.

## Running the App

### Local Development
```bash
cd ContestTool
pip install -r requirements.txt
export FEED_BASE_URL=https://flowbot44.github.io/grand-arena-builder-skill/data
uvicorn app.main:app --reload --port 8001
# Open http://localhost:8001
```

### Railway Deployment
1. Connect GitHub repo to Railway
2. Set environment variable: `FEED_BASE_URL`
3. Railway auto-deploys on push to main
4. Uses `Procfile` for startup command

## Frontend Features

### Upcoming Tab
- Table of champions sorted by expected wins
- Shows Avg FP and Total FP projections
- Click row to expand matchup details with supporter stats and per-game FP
- Filter by class, search by name

### Analysis Tab
- Historical game results with MS and Fantasy Points
- Bucket stats showing win rate by MS range
- Shows Proj FP, Actual FP, and +/- difference for each game
- Click row to expand supporter details with link to Grand Arena match page
- Filter by result (W/L), minimum MS, and search by champion name

### Schemes Tab
- Filter champions by scheme card compatibility
- Shows which trait-based schemes each champion qualifies for
- Click to see upcoming matchups

### Class Changes Tab
- Shows champions who have changed classes over time
- Displays old class, new class, and date of change
- Useful for tracking meta shifts

## Hosting Architecture (Implemented)
GitHub Actions + GitHub Pages + Railway:
- **GitHub Actions**: Runs hourly to pull match data from Grand Arena API
- **GitHub Pages**: Hosts JSON/GZIP feed files (partitions, cumulative stats)
- **Railway**: Hosts FastAPI app with in-memory caching
- **Data Window**: 14-day rolling window of match data

### Caching Behavior
- Fresh cache: Serve immediately (< 10 min old)
- Stale cache: Try refresh, serve stale on failure (< 15 min old)
- Empty cache: Fetch or return 503 with Retry-After header

## Classes
Defender, Striker, Sprinter, Bruiser, Center, Grinder, Forward, Flanker, Support, Anchor
