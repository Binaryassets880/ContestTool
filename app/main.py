from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from . import database

app = FastAPI(title="Grand Arena Contest Tool")

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(static_dir / "index.html")


@app.get("/api/upcoming")
async def get_upcoming():
    """Get all champions with their aggregated matchup scores for upcoming games."""
    return database.get_upcoming_summary()


@app.get("/api/champions/{token_id}/matchups")
async def get_champion_matchups(token_id: int):
    """Get detailed matchup breakdown for a specific champion."""
    result = database.get_champion_matchups(token_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Champion not found")
    return result


@app.get("/api/analysis")
async def get_analysis(limit: int = 1000):
    """Get historical games with matchup scores for analysis."""
    return database.get_historical_analysis(limit)


@app.get("/api/schemes")
async def get_schemes():
    """Get champions with their matching schemes and MS data."""
    return database.get_schemes_data()
