"""Get class changes for champions."""

from ..feed import get_feed


async def get_class_changes() -> dict:
    """Get all detected class changes.

    Returns a dict with:
    - total_changes: number of class change events detected
    - changes: list of change events sorted by date descending
    """
    feed = await get_feed()
    store = feed.store

    changes = store.get_class_changes()

    return {
        "total_changes": len(changes),
        "changes": changes,
    }
