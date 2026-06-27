"""
filter_engine.py — Preference-based filtering logic.

Applies sequential filters (location → budget → cuisine → rating)
with graceful constraint relaxation when too few candidates remain.

Design (from architecture.md § 3.3):
    1. Filters are applied sequentially.
    2. If < 5 results remain, relax constraints in order:
       cuisine → budget → rating.
    3. Results are sorted by rating (desc), then votes (desc).
    4. Top 15–20 candidates are returned for the LLM.
"""

import difflib
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from src.config import settings

logger = logging.getLogger(__name__)

# Minimum number of candidates before constraint relaxation kicks in.
_MIN_CANDIDATES = 5


# ═══════════════════════════════════════════════════════════════════════
# Location Validation
# ═══════════════════════════════════════════════════════════════════════


class LocationNotFoundError(Exception):
    """Raised when the user's location cannot be matched in the dataset."""

    def __init__(self, user_location: str, valid_locations: List[str]):
        self.user_location = user_location
        self.valid_locations = valid_locations
        # Suggest close matches
        self.suggestions = difflib.get_close_matches(
            user_location, valid_locations, n=5, cutoff=0.4
        )
        detail = f"Location '{user_location}' not found in the dataset."
        if self.suggestions:
            detail += f" Did you mean: {', '.join(self.suggestions)}?"
        super().__init__(detail)


def validate_location(
    user_location: str, known_locations: List[str]
) -> str:
    """
    Match the user-provided location against known dataset locations.

    Matching strategy (in order):
        1. Exact match (case-insensitive).
        2. Substring match — the user input is contained within a known location
           or vice-versa (case-insensitive).
        3. Fuzzy match via ``difflib.get_close_matches`` (cutoff=0.6).

    Args:
        user_location:   Location string from the user.
        known_locations: Sorted list of unique locations from ``build_indices()``.

    Returns:
        The canonical location string from the dataset.

    Raises:
        LocationNotFoundError: If no match is found (includes suggestions).
    """
    query = user_location.strip()
    if not query:
        raise LocationNotFoundError(user_location, known_locations)

    query_lower = query.lower()

    # 1. Exact match (case-insensitive)
    for loc in known_locations:
        if loc.lower() == query_lower:
            logger.debug("Location exact match: '%s' → '%s'", query, loc)
            return loc

    # 2. Substring match
    substring_matches = [
        loc
        for loc in known_locations
        if query_lower in loc.lower() or loc.lower() in query_lower
    ]
    if len(substring_matches) == 1:
        logger.debug(
            "Location substring match: '%s' → '%s'", query, substring_matches[0]
        )
        return substring_matches[0]
    if len(substring_matches) > 1:
        # Multiple substring matches — pick the closest by difflib
        best = difflib.get_close_matches(query, substring_matches, n=1, cutoff=0.0)
        if best:
            logger.debug(
                "Location substring+fuzzy match: '%s' → '%s'", query, best[0]
            )
            return best[0]

    # 3. Fuzzy match
    fuzzy = difflib.get_close_matches(query, known_locations, n=1, cutoff=0.6)
    if fuzzy:
        logger.debug("Location fuzzy match: '%s' → '%s'", query, fuzzy[0])
        return fuzzy[0]

    raise LocationNotFoundError(user_location, known_locations)


# ═══════════════════════════════════════════════════════════════════════
# Cuisine Fuzzy Matching
# ═══════════════════════════════════════════════════════════════════════


def match_cuisine(
    user_cuisine: Optional[str], known_cuisines: List[str]
) -> Optional[str]:
    """
    Fuzzy-match the user's cuisine preference against known cuisine types.

    Matching strategy (in order):
        1. Exact match (case-insensitive).
        2. Substring match (case-insensitive).
        3. Fuzzy match via ``difflib.get_close_matches`` (cutoff=0.5).

    Args:
        user_cuisine:   User's cuisine preference string.
        known_cuisines: Sorted list of unique cuisine types from the dataset.

    Returns:
        The matched canonical cuisine string, or None if no match / input is None.
    """
    if not user_cuisine or not user_cuisine.strip():
        return None

    query = user_cuisine.strip()
    query_lower = query.lower()

    # 1. Exact match
    for c in known_cuisines:
        if c.lower() == query_lower:
            logger.debug("Cuisine exact match: '%s' → '%s'", query, c)
            return c

    # 2. Substring match
    substring_matches = [
        c for c in known_cuisines if query_lower in c.lower() or c.lower() in query_lower
    ]
    if len(substring_matches) == 1:
        logger.debug(
            "Cuisine substring match: '%s' → '%s'", query, substring_matches[0]
        )
        return substring_matches[0]
    if len(substring_matches) > 1:
        # Multiple — pick closest
        best = difflib.get_close_matches(query, substring_matches, n=1, cutoff=0.0)
        if best:
            logger.debug(
                "Cuisine substring+fuzzy match: '%s' → '%s'", query, best[0]
            )
            return best[0]

    # 3. Fuzzy match
    fuzzy = difflib.get_close_matches(query, known_cuisines, n=1, cutoff=0.5)
    if fuzzy:
        logger.debug("Cuisine fuzzy match: '%s' → '%s'", query, fuzzy[0])
        return fuzzy[0]

    logger.info("No cuisine match found for '%s'.", query)
    return None


# ═══════════════════════════════════════════════════════════════════════
# Filter Result
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class FilterResult:
    """
    Container for the output of the filter engine.

    Attributes:
        candidates:          Filtered & sorted DataFrame of restaurant candidates.
        filters_applied:     Names of filter stages that were applied.
        constraints_relaxed: Names of constraints that were relaxed.
        matched_location:    The canonical location matched in the dataset.
        matched_cuisine:     The canonical cuisine matched (or None).
    """

    candidates: pd.DataFrame
    filters_applied: List[str] = field(default_factory=list)
    constraints_relaxed: List[str] = field(default_factory=list)
    matched_location: Optional[str] = None
    matched_cuisine: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# Core Filter Engine
# ═══════════════════════════════════════════════════════════════════════


def _filter_by_location(
    df: pd.DataFrame, location: str, location_index: Dict[str, List[int]]
) -> pd.DataFrame:
    """Filter the DataFrame to rows matching the given location."""
    row_indices = location_index.get(location, [])
    return df.loc[df.index.isin(row_indices)]


def _filter_by_budget(
    df: pd.DataFrame, budget: str, budget_ranges: Optional[Dict] = None
) -> pd.DataFrame:
    """Filter the DataFrame to rows within the budget cost range."""
    ranges = budget_ranges or settings.BUDGET_RANGES
    if budget not in ranges:
        logger.warning("Unknown budget tier '%s', skipping budget filter.", budget)
        return df
    low, high = ranges[budget]
    return df[(df["average_cost"] >= low) & (df["average_cost"] <= high)]


def _filter_by_cuisine(
    df: pd.DataFrame, cuisine: str, cuisine_index: Dict[str, Set[int]]
) -> pd.DataFrame:
    """Filter the DataFrame to rows that serve the given cuisine."""
    row_indices = cuisine_index.get(cuisine, set())
    if not row_indices:
        # Fall back to case-insensitive substring search on the cuisines column
        mask = df["cuisines"].str.contains(cuisine, case=False, na=False)
        return df[mask]
    return df.loc[df.index.isin(row_indices)]


def _filter_by_rating(df: pd.DataFrame, min_rating: float) -> pd.DataFrame:
    """Filter the DataFrame to rows with rating >= min_rating."""
    return df[df["rating"] >= min_rating]


def _sort_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Sort candidates by rating (desc), then votes (desc) as tiebreaker."""
    return df.sort_values(
        by=["rating", "votes"], ascending=[False, False]
    ).reset_index(drop=True)


def filter_restaurants(
    df: pd.DataFrame,
    indices: Dict,
    location: str,
    budget: str,
    cuisine: Optional[str] = None,
    min_rating: float = 3.0,
    max_candidates: Optional[int] = None,
    budget_ranges: Optional[Dict] = None,
) -> FilterResult:
    """
    Apply sequential filters to narrow down restaurant candidates.

    Filter order: Location → Budget → Cuisine → Min Rating.

    If fewer than 5 candidates remain after all filters, constraints are
    relaxed in order: cuisine → budget → rating, until at least 5
    candidates are available (or no more relaxation is possible).

    Args:
        df:             Preprocessed restaurant DataFrame.
        indices:        Dict from ``build_indices()`` with location/cuisine lookups.
        location:       Canonical location string (already validated).
        budget:         Budget tier: "low", "medium", or "high".
        cuisine:        Matched cuisine string (or None to skip cuisine filter).
        min_rating:     Minimum rating threshold.
        max_candidates: Max candidates to return (default: settings.MAX_CANDIDATES).
        budget_ranges:  Optional override for budget range mapping.

    Returns:
        FilterResult containing the filtered, sorted candidate DataFrame
        and metadata about which filters/relaxations were applied.
    """
    if max_candidates is None:
        max_candidates = settings.MAX_CANDIDATES

    location_index = indices.get("location_index", {})
    cuisine_index = indices.get("cuisine_index", {})

    filters_applied: List[str] = []
    constraints_relaxed: List[str] = []

    # ── Stage 1: Location (never relaxed — it's required) ────────────
    result = _filter_by_location(df, location, location_index)
    filters_applied.append("location")
    logger.info(
        "After location filter ('%s'): %d candidates.", location, len(result)
    )

    if result.empty:
        # No restaurants at this location at all — return empty
        return FilterResult(
            candidates=_sort_candidates(result),
            filters_applied=filters_applied,
            constraints_relaxed=constraints_relaxed,
            matched_location=location,
            matched_cuisine=cuisine,
        )

    # ── Stage 2: Budget ──────────────────────────────────────────────
    after_budget = _filter_by_budget(result, budget, budget_ranges)
    filters_applied.append("budget")
    logger.info("After budget filter ('%s'): %d candidates.", budget, len(after_budget))

    # ── Stage 3: Cuisine (if provided) ───────────────────────────────
    if cuisine:
        after_cuisine = _filter_by_cuisine(after_budget, cuisine, cuisine_index)
        filters_applied.append("cuisine")
        logger.info(
            "After cuisine filter ('%s'): %d candidates.", cuisine, len(after_cuisine)
        )
    else:
        after_cuisine = after_budget

    # ── Stage 4: Min Rating ──────────────────────────────────────────
    after_rating = _filter_by_rating(after_cuisine, min_rating)
    filters_applied.append("min_rating")
    logger.info(
        "After rating filter (>= %.1f): %d candidates.", min_rating, len(after_rating)
    )

    # ── Constraint Relaxation ────────────────────────────────────────
    # If < _MIN_CANDIDATES, relax in order: cuisine → budget → rating
    final = after_rating

    if len(final) < _MIN_CANDIDATES:
        # Relax 1: Drop cuisine filter
        if cuisine and len(final) < _MIN_CANDIDATES:
            relaxed = _filter_by_rating(
                _filter_by_budget(result, budget, budget_ranges), min_rating
            )
            if len(relaxed) > len(final):
                final = relaxed
                constraints_relaxed.append("cuisine")
                logger.info(
                    "Relaxed cuisine constraint: now %d candidates.", len(final)
                )

        # Relax 2: Drop budget filter (keep cuisine relaxed too)
        if len(final) < _MIN_CANDIDATES:
            relaxed = _filter_by_rating(result, min_rating)
            if len(relaxed) > len(final):
                final = relaxed
                if "budget" not in constraints_relaxed:
                    constraints_relaxed.append("budget")
                logger.info(
                    "Relaxed budget constraint: now %d candidates.", len(final)
                )

        # Relax 3: Drop min rating filter
        if len(final) < _MIN_CANDIDATES:
            relaxed = result  # Only location filter remains
            if len(relaxed) > len(final):
                final = relaxed
                if "min_rating" not in constraints_relaxed:
                    constraints_relaxed.append("min_rating")
                logger.info(
                    "Relaxed rating constraint: now %d candidates.", len(final)
                )

    # ── Sort & Trim ──────────────────────────────────────────────────
    final = _sort_candidates(final)
    final = final.head(max_candidates)

    logger.info(
        "Filter engine complete: %d candidates returned (relaxed: %s).",
        len(final),
        constraints_relaxed or "none",
    )

    return FilterResult(
        candidates=final,
        filters_applied=filters_applied,
        constraints_relaxed=constraints_relaxed,
        matched_location=location,
        matched_cuisine=cuisine,
    )
