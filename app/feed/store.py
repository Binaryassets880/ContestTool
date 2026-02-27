"""In-memory data store with indexes for efficient queries."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MatchRecord:
    """Normalized match record from feed."""

    match_id: str
    match_date: str
    team_won: Optional[int]
    win_type: Optional[str]
    state: str
    players: list[dict]
    performances: list[dict]


@dataclass
class FeedDataStore:
    """In-memory store with efficient indexes."""

    # Raw data
    matches: dict[str, MatchRecord] = field(default_factory=dict)
    cumulative_stats: dict[int, dict] = field(default_factory=dict)

    # Indexes
    matches_by_date: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    matches_by_token: dict[int, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    scheduled_matches: list[str] = field(default_factory=list)
    scored_matches: list[str] = field(default_factory=list)

    # Pre-computed aggregates
    class_matchup_winrates: dict[tuple[str, str], float] = field(default_factory=dict)
    champion_winrates: dict[int, dict] = field(default_factory=dict)

    # Class change tracking
    class_history: dict[int, list[tuple[str, str]]] = field(
        default_factory=lambda: defaultdict(list)
    )  # token_id -> [(match_date, class), ...]

    def clear(self):
        """Clear all data and indexes."""
        self.matches.clear()
        self.cumulative_stats.clear()
        self.matches_by_date.clear()
        self.matches_by_token.clear()
        self.scheduled_matches.clear()
        self.scored_matches.clear()
        self.class_matchup_winrates.clear()
        self.champion_winrates.clear()
        self.class_history.clear()

    def load_partition(self, partition_data: list[dict]):
        """Load a partition into the store."""
        loaded = 0
        for record in partition_data:
            match_obj = record.get("match", {})
            match_id = match_obj.get("match_id")

            if not match_id:
                continue
            if match_id in self.matches:
                continue  # Already loaded

            match_record = MatchRecord(
                match_id=match_id,
                match_date=match_obj.get("match_date", ""),
                team_won=match_obj.get("team_won"),
                win_type=match_obj.get("win_type"),
                state=match_obj.get("state", ""),
                players=record.get("players", []),
                performances=record.get("performances", []),
            )
            self.matches[match_id] = match_record
            self._index_match(match_record)
            loaded += 1

        logger.info(f"Loaded {loaded} new matches from partition")

    def _index_match(self, match: MatchRecord):
        """Build indexes for a match."""
        self.matches_by_date[match.match_date].append(match.match_id)

        for player in match.players:
            token_id = player.get("token_id")
            if token_id:
                self.matches_by_token[token_id].append(match.match_id)

            # Track class history for champions (scored matches only)
            if player.get("is_champion") and token_id and match.state == "scored":
                player_class = player.get("class", "")
                if player_class:
                    self.class_history[token_id].append((match.match_date, player_class))

        if match.state == "scheduled":
            self.scheduled_matches.append(match.match_id)
        elif match.state == "scored":
            self.scored_matches.append(match.match_id)

    def load_cumulative(self, cumulative_data: list[dict]):
        """Load cumulative stats."""
        for record in cumulative_data:
            token_id = record.get("token_id")
            if token_id:
                games = record.get("games_played_cum", 0)
                self.cumulative_stats[token_id] = {
                    "games_played": games,
                    "wins": record.get("wins_cum", 0),
                    "eliminations": record.get("eliminations_cum", 0),
                    "deposits": record.get("deposits_cum", 0),
                    "wart_distance": record.get("wart_distance_cum", 0),
                    # Pre-compute averages
                    "avg_elims": (
                        record.get("eliminations_cum", 0) / games if games > 0 else 1.0
                    ),
                    "avg_deps": (
                        record.get("deposits_cum", 0) / games if games > 0 else 1.5
                    ),
                    "avg_wart": (
                        record.get("wart_distance_cum", 0) / games if games > 0 else 0.0
                    ),
                }
        logger.info(f"Loaded cumulative stats for {len(cumulative_data)} players")

    def rebuild_aggregates(self):
        """Rebuild pre-computed aggregates from loaded data."""
        logger.info("Rebuilding aggregate statistics...")
        self._compute_champion_winrates()
        self._compute_class_matchups()
        logger.info(
            f"Aggregates built: {len(self.champion_winrates)} champions, "
            f"{len(self.class_matchup_winrates)} class matchups"
        )

    def _compute_champion_winrates(self):
        """Compute champion win rates from scored matches."""
        champ_stats: dict[int, dict] = defaultdict(
            lambda: {"wins": 0, "games": 0, "name": "", "class": ""}
        )

        # First, collect champion info from ALL matches (including scheduled)
        # This ensures we have name/class even if no scored matches exist
        for match_id, match in self.matches.items():
            for player in match.players:
                if player.get("is_champion"):
                    token_id = player.get("token_id")
                    if token_id and not champ_stats[token_id]["name"]:
                        champ_stats[token_id]["name"] = player.get("name", "")
                        champ_stats[token_id]["class"] = player.get("class", "")

        # Then compute win rates from scored matches only
        for match_id in self.scored_matches:
            match = self.matches[match_id]
            for player in match.players:
                if player.get("is_champion"):
                    token_id = player["token_id"]
                    team = player["team"]
                    won = match.team_won == team

                    champ_stats[token_id]["games"] += 1
                    if won:
                        champ_stats[token_id]["wins"] += 1
                    # Update name/class in case we have better info from scored match
                    if player.get("name"):
                        champ_stats[token_id]["name"] = player.get("name", "")
                    if player.get("class"):
                        champ_stats[token_id]["class"] = player.get("class", "")

        self.champion_winrates = {
            token_id: {
                **stats,
                "win_pct": (
                    round(100 * stats["wins"] / stats["games"], 1)
                    if stats["games"] > 0
                    else 50.0
                ),
            }
            for token_id, stats in champ_stats.items()
        }

    def _compute_class_matchups(self):
        """Compute class vs class win rates."""
        matchup_stats: dict[tuple[str, str], dict] = defaultdict(
            lambda: {"wins": 0, "games": 0}
        )

        for match_id in self.scored_matches:
            match = self.matches[match_id]
            champions = [p for p in match.players if p.get("is_champion")]
            if len(champions) != 2:
                continue

            c1, c2 = champions
            if c1["team"] > c2["team"]:
                c1, c2 = c2, c1  # Ensure consistent team ordering

            # c1 vs c2
            key1 = (c1.get("class", ""), c2.get("class", ""))
            matchup_stats[key1]["games"] += 1
            if match.team_won == c1["team"]:
                matchup_stats[key1]["wins"] += 1

            # c2 vs c1
            key2 = (c2.get("class", ""), c1.get("class", ""))
            matchup_stats[key2]["games"] += 1
            if match.team_won == c2["team"]:
                matchup_stats[key2]["wins"] += 1

        # Only include matchups with enough games
        self.class_matchup_winrates = {
            key: round(100 * stats["wins"] / stats["games"], 1)
            for key, stats in matchup_stats.items()
            if stats["games"] >= 10
        }

    def get_career_stats(self, token_id: int) -> dict:
        """Get career stats for a token from cumulative data."""
        if token_id in self.cumulative_stats:
            stats = self.cumulative_stats[token_id]
            return {
                "career_elims": stats["avg_elims"],
                "career_deps": stats["avg_deps"],
                "career_wart": stats["avg_wart"],
            }
        # Default values for unknown tokens
        return {"career_elims": 1.0, "career_deps": 1.5, "career_wart": 0.0}

    def get_career_stats_before_date(self, token_id: int, before_date: str) -> dict:
        """Get career stats using only performances before a specific date.

        Required for point-in-time historical analysis.
        """
        elims, deps, wart, count = 0.0, 0.0, 0.0, 0

        for match_id in self.matches_by_token.get(token_id, []):
            match = self.matches.get(match_id)
            if not match or match.match_date >= before_date:
                continue
            if match.state != "scored":
                continue

            for perf in match.performances:
                if perf.get("token_id") == token_id:
                    elims += perf.get("eliminations", 0) or 0
                    deps += perf.get("deposits", 0) or 0
                    wart += perf.get("wart_distance", 0) or 0
                    count += 1

        if count > 0:
            return {
                "career_elims": elims / count,
                "career_deps": deps / count,
                "career_wart": wart / count,
            }
        return {"career_elims": 1.0, "career_deps": 1.5, "career_wart": 0.0}

    def get_champion_winrate_before_date(self, token_id: int, before_date: str) -> float:
        """Get champion win rate using only matches before a specific date.

        Required for point-in-time historical analysis.
        """
        wins, games = 0, 0

        for match_id in self.matches_by_token.get(token_id, []):
            match = self.matches.get(match_id)
            if not match or match.state != "scored" or match.match_date >= before_date:
                continue

            for player in match.players:
                if player.get("token_id") == token_id and player.get("is_champion"):
                    games += 1
                    if match.team_won == player["team"]:
                        wins += 1
                    break

        return round(100 * wins / games, 1) if games > 0 else 50.0

    def get_class_matchup(self, my_class: str, opp_class: str) -> float:
        """Get class matchup win rate."""
        return self.class_matchup_winrates.get((my_class, opp_class), 50.0)

    def get_champion_info(self, token_id: int) -> Optional[dict]:
        """Get basic champion info from winrates data."""
        return self.champion_winrates.get(token_id)

    def get_class_changes(self) -> list[dict]:
        """Detect all Mokis that have changed class.

        Returns a list of class change events, sorted by change date descending.
        """
        changes = []
        for token_id, history in self.class_history.items():
            if len(history) < 2:
                continue

            # Sort by date
            sorted_history = sorted(history, key=lambda x: x[0])

            # Find changes
            for i in range(1, len(sorted_history)):
                prev_date, prev_class = sorted_history[i - 1]
                curr_date, curr_class = sorted_history[i]

                if prev_class != curr_class and prev_class and curr_class:
                    champ_info = self.champion_winrates.get(token_id, {})
                    changes.append(
                        {
                            "token_id": token_id,
                            "name": champ_info.get("name", f"#{token_id}"),
                            "old_class": prev_class,
                            "new_class": curr_class,
                            "change_date": curr_date,
                            "last_match_as_old": prev_date,
                        }
                    )

        # Sort by change date descending (most recent first)
        return sorted(changes, key=lambda x: x["change_date"], reverse=True)
