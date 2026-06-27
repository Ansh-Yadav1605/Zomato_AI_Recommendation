"""
schemas.py — Pydantic models for API request/response validation.

Defines RecommendationRequest, RecommendationResponse,
and RestaurantRecommendation models used across the API layer.
"""

from typing import List, Literal, Optional

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════


class RecommendationRequest(BaseModel):
    """
    User preferences for a restaurant recommendation query.

    Attributes:
        location:               Locality / neighbourhood (required).
        budget:                 Budget tier — "low", "medium", or "high" (required).
        cuisine:                Preferred cuisine type, e.g. "Italian" (optional).
        min_rating:             Minimum acceptable aggregate rating (0.0–5.0).
        additional_preferences: Free-text notes, e.g. "family-friendly" (optional).
    """

    location: str = Field(
        ...,
        min_length=1,
        description="Locality or neighbourhood, e.g. 'Koramangala'.",
    )
    budget: Literal["low", "medium", "high"] = Field(
        ...,
        description="Budget tier: low (₹0–500), medium (₹500–1500), high (₹1500+).",
    )
    cuisine: Optional[str] = Field(
        default=None,
        description="Preferred cuisine type, e.g. 'Italian'. Fuzzy-matched against known cuisines.",
    )
    min_rating: float = Field(
        default=3.0,
        ge=0.0,
        le=5.0,
        description="Minimum aggregate rating (0.0–5.0). Default: 3.0.",
    )
    additional_preferences: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Free-text preferences, e.g. 'rooftop seating, live music'.",
    )


# ═══════════════════════════════════════════════════════════════════════
# Response Models
# ═══════════════════════════════════════════════════════════════════════


class RestaurantRecommendation(BaseModel):
    """
    A single restaurant recommendation returned by the LLM.

    Attributes:
        restaurant_name: Name of the restaurant.
        cuisine:         Cuisine types served.
        rating:          Aggregate user rating (0.0–5.0).
        estimated_cost:  Approximate cost for two (₹).
        explanation:     LLM-generated explanation of why this restaurant fits.
    """

    restaurant_name: str
    cuisine: str
    rating: float = Field(ge=0.0, le=5.0)
    estimated_cost: str
    explanation: str


class FilterMetadata(BaseModel):
    """
    Metadata about the filtering process applied to produce candidates.

    Attributes:
        total_restaurants:  Total restaurants in the dataset.
        candidates_found:   Number of candidates after filtering.
        filters_applied:    List of filter stages that were applied.
        constraints_relaxed: List of constraints that were relaxed (if any).
        matched_location:   The actual location string matched in the dataset.
        matched_cuisine:    The actual cuisine string matched (if fuzzy-matched).
    """

    total_restaurants: int
    candidates_found: int
    filters_applied: List[str] = Field(default_factory=list)
    constraints_relaxed: List[str] = Field(default_factory=list)
    matched_location: Optional[str] = None
    matched_cuisine: Optional[str] = None


class RecommendationResponse(BaseModel):
    """
    Full API response for a recommendation request.

    Attributes:
        success:          Whether the request was processed successfully.
        recommendations:  List of top restaurant recommendations from the LLM.
        filter_metadata:  Details about filtering stages and constraint relaxation.
        model_used:       LLM model identifier used for ranking.
        response_time_ms: End-to-end response time in milliseconds.
        message:          Optional message (e.g. info about relaxed constraints).
    """

    success: bool = True
    recommendations: List[RestaurantRecommendation] = Field(default_factory=list)
    filter_metadata: Optional[FilterMetadata] = None
    model_used: Optional[str] = None
    response_time_ms: Optional[float] = None
    message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# Budget Mapping (canonical reference — also in config.py)
# ═══════════════════════════════════════════════════════════════════════

BUDGET_RANGES = {
    "low": (0, 500),
    "medium": (500, 1500),
    "high": (1500, float("inf")),
}
