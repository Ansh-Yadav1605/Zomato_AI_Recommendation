# Pydantic models and schemas
"""
src.models — Data models for the recommendation system.

Public API:
    Restaurant                — Pydantic model for a single restaurant entity.
    RecommendationRequest     — Pydantic model for user preference input.
    RecommendationResponse    — Pydantic model for API response envelope.
    RestaurantRecommendation  — Pydantic model for a single LLM recommendation.
    FilterMetadata            — Pydantic model for filter pipeline metadata.
    BUDGET_RANGES             — Canonical budget tier → cost range mapping.
"""

from src.models.restaurant import Restaurant
from src.models.schemas import (
    BUDGET_RANGES,
    FilterMetadata,
    RecommendationRequest,
    RecommendationResponse,
    RestaurantRecommendation,
)

__all__ = [
    "Restaurant",
    "RecommendationRequest",
    "RecommendationResponse",
    "RestaurantRecommendation",
    "FilterMetadata",
    "BUDGET_RANGES",
]
