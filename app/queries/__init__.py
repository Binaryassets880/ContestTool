"""Query implementations using feed data store."""

from .upcoming import get_upcoming_summary
from .champion_matchups import get_champion_matchups
from .historical import get_historical_analysis
from .schemes import get_schemes_data
from .scoring import calc_matchup_score, get_grade, get_edge_label
from .scoring_v4 import calc_composition_score
from .composition import classify_supporter, detect_team_composition, get_pattern_display
from .composition_analysis import (
    build_composition_matrix,
    validate_hypotheses,
    get_composition_analysis_summary,
)
from .class_changes import get_class_changes
from .composition_table import get_composition_table
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
    "calc_composition_score",
    "get_grade",
    "get_edge_label",
    "classify_supporter",
    "detect_team_composition",
    "get_pattern_display",
    "build_composition_matrix",
    "validate_hypotheses",
    "get_composition_analysis_summary",
    "get_class_changes",
    "get_composition_table",
    "calc_projected_fp",
    "calc_actual_fp",
    "get_fp_tier",
    "FP_ELIM",
    "FP_DEP",
    "FP_WART",
    "FP_WIN",
]
