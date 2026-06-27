# Business logic services
"""
src.services — Business logic for filtering and LLM integration.

Public API:
    filter_restaurants    — Apply multi-stage filters to narrow restaurant candidates.
    validate_location     — Match user location against known dataset locations.
    match_cuisine         — Fuzzy-match user cuisine input to known cuisine types.
    LocationNotFoundError — Raised when a location cannot be matched.
    FilterResult          — Dataclass containing filter output and metadata.
"""

from src.services.filter_engine import (
    FilterResult,
    LocationNotFoundError,
    filter_restaurants,
    match_cuisine,
    validate_location,
)

__all__ = [
    "filter_restaurants",
    "validate_location",
    "match_cuisine",
    "LocationNotFoundError",
    "FilterResult",
]
