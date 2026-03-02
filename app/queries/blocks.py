"""Contest block utilities for grouping scheduled games.

=== BLOCK ASSIGNMENT SYSTEM - DO NOT MODIFY WITHOUT EXPLICIT REQUEST ===

This module handles assigning games to contest time blocks (8PM, 4AM, 12PM).
The logic is carefully calibrated and MUST follow these rules:

1. MATCH_ID = PLAY ORDER
   Games are played in match_id order. The match_id is a MongoDB ObjectID where
   the first 8 hex chars encode the creation timestamp. Sequential IDs = sequential play.

2. PER-CHAMPION POSITION CYCLING
   Each champion's games are assigned blocks based on their position in that
   champion's sorted match list:
   - Positions 0-9:   8PM block
   - Positions 10-19: 4AM block
   - Positions 20-29: 12PM block
   - Positions 30+:   Cycle repeats (30-39 = 8PM, etc.)

3. INCLUDE ALL MATCHES (SCHEDULED + SCORED) FOR POSITION CALCULATION
   If you only count scheduled matches, positions SHIFT as games complete:
   - Before: 30 scheduled games → Chef Maki at position 20 (12PM) ✓
   - After 10 scored: 20 scheduled → Chef Maki at position 10 (4AM) ✗
   By including scored games, positions stay stable.

4. DUAL FILTER REQUIRED
   Matches must pass BOTH filters to be counted:
   - is_new_format_date(match.match_date): Scheduled for March 2, 2026+
   - is_new_format_match(match_id): Created after Feb 28, 2026

   WHY BOTH? There's a "Feb 19 batch" of games created on Feb 19 but scheduled
   for March 2. These were created before the new block system and must be
   EXCLUDED from block assignment. The match_id timestamp filter catches these.

5. SORT BY MATCH_ID WITHIN BLOCKS
   When displaying matchups, sort by (date, block, match_id) to show correct
   play order within each block.

See CLAUDE.md for additional documentation.
"""

from datetime import datetime, timezone
from collections import defaultdict

# Contest blocks (using EST labels as primary)
CONTEST_BLOCKS = {
    1: {"hour": 1, "label": "8 PM", "utc": "1 AM UTC"},
    2: {"hour": 9, "label": "4 AM", "utc": "9 AM UTC"},
    3: {"hour": 17, "label": "12 PM", "utc": "5 PM UTC"},
}

# New 10-game block format starts on March 2, 2026 (8 PM EST March 1 = 1 AM UTC March 2)
NEW_FORMAT_START_DATE = "2026-03-02"

# Timestamp cutoff for NEW FORMAT games - games created after this are new format
# The "Feb 19 batch" has timestamps ~1771498072 (Feb 19-20) - these are EXCLUDED
# New format games have timestamp >= 1772337790 (Feb 28, 2026 ~11 PM UTC)
# This filter is REQUIRED to exclude Feb 19 batch from block calculations
NEW_FORMAT_START_TIMESTAMP = 1772337790


def extract_timestamp_from_match_id(match_id: str) -> int:
    """Extract Unix timestamp from MongoDB ObjectID (first 8 hex chars)."""
    try:
        return int(match_id[:8], 16)
    except (ValueError, TypeError):
        return 0


def is_new_format_match(match_id: str) -> bool:
    """Check if a match is part of the new 10-game block format based on match_id timestamp."""
    timestamp = extract_timestamp_from_match_id(match_id)
    return timestamp >= NEW_FORMAT_START_TIMESTAMP


def is_new_format_date(match_date: str) -> bool:
    """Check if a match date is part of the new 10-game block format."""
    return match_date >= NEW_FORMAT_START_DATE


def get_utc_today() -> str:
    """Get today's date in YYYY-MM-DD format (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_current_block() -> int:
    """Get current/next block number (1, 2, or 3).

    Block windows (UTC):
    - Block 1: 1 AM - 5 AM
    - Block 2: 9 AM - 1 PM
    - Block 3: 5 PM - 9 PM
    """
    hour = datetime.now(timezone.utc).hour

    if hour < 5:
        return 1  # Block 1 active (1-5 AM)
    elif hour < 9:
        return 2  # Before Block 2
    elif hour < 13:
        return 2  # Block 2 active (9 AM - 1 PM)
    elif hour < 17:
        return 3  # Before Block 3
    elif hour < 21:
        return 3  # Block 3 active (5-9 PM)
    else:
        return 1  # After 9 PM, next block is Block 1 tomorrow


def assign_blocks_to_matches(match_ids: list[str]) -> dict[str, int]:
    """Assign block numbers to matches - cycles every 30 games.

    Pattern repeats forever:
    - Games 0-9: Block 1 (8PM)
    - Games 10-19: Block 2 (4AM)
    - Games 20-29: Block 3 (12PM)
    - Games 30-39: Block 1 (8PM)
    - etc.
    """
    if not match_ids:
        return {}

    sorted_ids = sorted(match_ids)

    result = {}
    for i, mid in enumerate(sorted_ids):
        position_in_cycle = i % 30
        if position_in_cycle < 10:
            result[mid] = 1  # 8PM
        elif position_in_cycle < 20:
            result[mid] = 2  # 4AM
        else:
            result[mid] = 3  # 12PM

    return result


def assign_blocks_to_all_matches(store) -> dict[str, int]:
    """Assign block numbers to all scheduled matches across all dates.

    === DO NOT MODIFY WITHOUT EXPLICIT REQUEST - SEE MODULE DOCSTRING ===

    Blocks are assigned PER CHAMPION, not globally:
    - Each champion's matches are sorted by match_id (= play order)
    - Games 0-9: 8PM, 10-19: 4AM, 20-29: 12PM (cycling every 30)

    CRITICAL IMPLEMENTATION DETAILS:

    1. Position uses ALL matches (scheduled + scored) so blocks don't shift
       as games complete. Without this, a 12PM game becomes 4AM after the
       8PM block finishes.

    2. DUAL FILTER REQUIRED - matches must pass BOTH:
       - is_new_format_date(): match scheduled for March 2+
       - is_new_format_match(): match CREATED after Feb 28
       This excludes the "Feb 19 batch" (created Feb 19, scheduled March 2).

    Returns:
        dict mapping match_id -> block number (1=8PM, 2=4AM, 3=12PM)
        Only includes scheduled matches (not scored).
    """
    # Build per-champion match lists (ALL matches, not just scheduled)
    # This ensures block positions don't shift as games are completed
    matches_by_champion: dict[int, list[str]] = defaultdict(list)

    # Include both scheduled and scored matches for position calculation
    all_match_ids = store.scheduled_matches + store.scored_matches

    for match_id in all_match_ids:
        match = store.matches.get(match_id)
        if not match:
            continue

        # Only new format matches get blocks
        # Must pass BOTH checks:
        # 1. Scheduled for March 2+ (date check)
        # 2. Created in new format era (excludes Feb 19 batch)
        if not is_new_format_date(match.match_date):
            continue
        if not is_new_format_match(match_id):
            continue

        # Find both champions in this match
        for player in match.players:
            if player.get("is_champion"):
                token_id = player.get("token_id")
                if token_id:
                    matches_by_champion[token_id].append(match_id)

    # Sort each champion's matches and build position lookup
    # Key: (token_id, match_id) -> position in that champion's sorted list
    champion_positions: dict[tuple[int, str], int] = {}

    for token_id, match_ids in matches_by_champion.items():
        sorted_ids = sorted(match_ids)
        for position, mid in enumerate(sorted_ids):
            champion_positions[(token_id, mid)] = position

    # Assign blocks based on each champion's position
    # Since each match has 2 champions, we use the first champion's position
    # (both champions in a match should have the same relative position)
    result = {}

    for match_id in store.scheduled_matches:
        match = store.matches.get(match_id)
        if not match:
            continue

        # Same filters as above
        if not is_new_format_date(match.match_date):
            continue
        if not is_new_format_match(match_id):
            continue

        # Find the first champion and use their position
        for player in match.players:
            if player.get("is_champion"):
                token_id = player.get("token_id")
                if token_id and (token_id, match_id) in champion_positions:
                    position = champion_positions[(token_id, match_id)]
                    position_in_cycle = position % 30
                    if position_in_cycle < 10:
                        result[match_id] = 1  # 8PM
                    elif position_in_cycle < 20:
                        result[match_id] = 2  # 4AM
                    else:
                        result[match_id] = 3  # 12PM
                    break

    return result


def get_block_label(block: int) -> str:
    """Get human-readable label for a block."""
    return CONTEST_BLOCKS.get(block, {}).get("label", f"Block {block}")
