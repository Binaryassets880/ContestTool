"""Query implementations using feed data store."""

from .upcoming import get_upcoming_summary
from .champion_matchups import get_champion_matchups
from .historical import get_historical_analysis
from .schemes import get_schemes_data
from .scoring import calc_matchup_score, get_edge_label
from .class_changes import get_class_changes
from .fantasy import (
    calc_projected_fp,
    calc_actual_fp,
    get_fp_tier,
    FP_ELIM,
    FP_DEP,
    FP_WART,
    FP_WIN,
)

__all__ = [
    "get_upcoming_summary",
    "get_champion_matchups",
    "get_historical_analysis",
    "get_schemes_data",
    "calc_matchup_score",
    "get_edge_label",
    "get_class_changes",
    "calc_projected_fp",
    "calc_actual_fp",
    "get_fp_tier",
    "FP_ELIM",
    "FP_DEP",
    "FP_WART",
    "FP_WIN",
]
