"""Scheme matching and champion trait analysis."""

import json
from pathlib import Path

from .upcoming import get_upcoming_summary

# Scheme trait requirements mapping (copied from database.py)
SCHEME_TRAITS = {
    "Costume Party": {
        "contains": ["Onesie"],
        "exact": [
            "Lemon Head",
            "Kappa Head",
            "Tomato Head",
            "Bear Head",
            "Frog Head",
            "Blob Head",
        ],
    },
    "Shapeshifting": {
        "contains": ["Tongue Out"],
        "exact": ["Tanuki Mask", "Kitsune Mask", "Cat Mask"],
    },
    "Midnight Strike": {"contains": ["Shadow"]},
    "Dress to Impress": {"contains": ["Kimono"]},
    "Housekeeping": {
        "contains": ["Apron"],
        "exact": ["Garbage Can", "Gold Can", "Toilet Paper"],
    },
    "Dungaree Duel": {"exact": ["Pink Overalls", "Blue Overalls", "Green Overalls"]},
    "Tear Jerking": {"contains": ["Crying"]},
    "Golden Shower": {
        "contains": ["Gold"],
        "exclude": ["Gold Can", "Gold Katana"],  # Only fur, not items
    },
    "Rainbow Riot": {"contains": ["Rainbow"]},
    "Divine Intervention": {"contains": ["Spirit"]},
    "Whale Watching": {"exact": ["1 of 1"]},
    "Call to Arms": {"exact": ["Ronin", "Samurai"]},
    "Malicious Intent": {
        "contains": ["Devious"],
        "exact": ["Oni Mask", "Tengu Mask", "Skull Mask"],
    },
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


async def get_schemes_data() -> dict:
    """Get champions with their matching schemes and avg MS."""
    # Load champions data from local file
    champions_path = Path(__file__).parent.parent.parent / "champions.json"
    with open(champions_path, "r") as f:
        champions = json.load(f)

    # Get upcoming summary for MS data
    upcoming = await get_upcoming_summary()
    upcoming_by_id = {c["token_id"]: c for c in upcoming}

    # Build results
    results = []
    scheme_names = list(SCHEME_TRAITS.keys())

    for champ in champions:
        token_id = champ["id"]
        traits = champ["traits"]

        # Find matching schemes
        matching_schemes = []
        for scheme_name in scheme_names:
            if champion_matches_scheme(traits, scheme_name):
                matching_schemes.append(scheme_name)

        # Get MS data if available
        upcoming_data = upcoming_by_id.get(token_id)

        if upcoming_data:
            results.append(
                {
                    "token_id": token_id,
                    "name": champ["name"],
                    "class": upcoming_data["class"],
                    "matching_schemes": matching_schemes,
                    "games": upcoming_data["games"],
                    "avg_score": upcoming_data["avg_score"],
                    "expected_wins": upcoming_data["expected_wins"],
                    "has_upcoming": True,
                }
            )
        else:
            # Champion has no upcoming games
            champ_class = traits[0] if traits else "Unknown"
            results.append(
                {
                    "token_id": token_id,
                    "name": champ["name"],
                    "class": champ_class,
                    "matching_schemes": matching_schemes,
                    "games": 0,
                    "avg_score": 0,
                    "expected_wins": 0,
                    "has_upcoming": False,
                }
            )

    # Sort by avg_score descending (best matchups first)
    results.sort(key=lambda x: (x["has_upcoming"], x["avg_score"]), reverse=True)

    return {"champions": results, "schemes": scheme_names}
