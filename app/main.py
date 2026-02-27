"""FastAPI application for Grand Arena Contest Tool."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .feed import FeedCoordinator, FeedUnavailableError
from .queries import (
    get_champion_matchups,
    get_class_changes,
    get_historical_analysis,
    get_schemes_data,
    get_upcoming_summary,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup feed."""
    logger.info("Starting Grand Arena Contest Tool...")
    feed = FeedCoordinator.get_instance()
    try:
        await feed.initialize()
        logger.info("Feed coordinator initialized successfully")
    except FeedUnavailableError as e:
        logger.error(f"Failed to initialize feed: {e}")
        # Allow startup to continue - will return 503 on API calls
    yield
    logger.info("Shutting down...")
    await feed.shutdown()


app = FastAPI(title="Grand Arena Contest Tool", lifespan=lifespan)

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint with feed status."""
    feed = FeedCoordinator.get_instance()
    return feed.get_health_info()


@app.get("/api/upcoming")
async def api_upcoming():
    """Get all champions with their aggregated matchup scores for upcoming games."""
    try:
        return await get_upcoming_summary()
    except FeedUnavailableError as e:
        logger.error(f"Feed unavailable for /api/upcoming: {e}")
        raise HTTPException(
            status_code=503,
            detail="Feed data temporarily unavailable. Please try again later.",
            headers={"Retry-After": str(e.retry_after)},
        )


@app.get("/api/champions/{token_id}/matchups")
async def api_champion_matchups(token_id: int):
    """Get detailed matchup breakdown for a specific champion."""
    try:
        result = await get_champion_matchups(token_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Champion not found")
        return result
    except FeedUnavailableError as e:
        logger.error(f"Feed unavailable for /api/champions/{token_id}/matchups: {e}")
        raise HTTPException(
            status_code=503,
            detail="Feed data temporarily unavailable. Please try again later.",
            headers={"Retry-After": str(e.retry_after)},
        )


@app.get("/api/analysis")
async def api_analysis(limit: int = 50000):
    """Get historical games with matchup scores for analysis."""
    try:
        return await get_historical_analysis(limit)
    except FeedUnavailableError as e:
        logger.error(f"Feed unavailable for /api/analysis: {e}")
        raise HTTPException(
            status_code=503,
            detail="Feed data temporarily unavailable. Please try again later.",
            headers={"Retry-After": str(e.retry_after)},
        )


@app.get("/api/schemes")
async def api_schemes():
    """Get champions with their matching schemes and MS data."""
    try:
        return await get_schemes_data()
    except FeedUnavailableError as e:
        logger.error(f"Feed unavailable for /api/schemes: {e}")
        raise HTTPException(
            status_code=503,
            detail="Feed data temporarily unavailable. Please try again later.",
            headers={"Retry-After": str(e.retry_after)},
        )


@app.get("/api/class-changes")
async def api_class_changes():
    """Get champions that have changed class."""
    try:
        return await get_class_changes()
    except FeedUnavailableError as e:
        logger.error(f"Feed unavailable for /api/class-changes: {e}")
        raise HTTPException(
            status_code=503,
            detail="Feed data temporarily unavailable. Please try again later.",
            headers={"Retry-After": str(e.retry_after)},
        )
