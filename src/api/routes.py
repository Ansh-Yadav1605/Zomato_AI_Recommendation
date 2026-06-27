"""
routes.py — FastAPI route definitions.

Defines the REST API endpoints:
    POST /recommend  — Main recommendation endpoint
    GET  /locations  — List of valid locations from the dataset
    GET  /cuisines   — List of known cuisine types
    GET  /health     — Health check
"""

import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException, Request

from src.config import settings
from src.models.schemas import (
    FilterMetadata,
    RecommendationRequest,
    RecommendationResponse,
    RestaurantRecommendation,
)
from src.services.filter_engine import (
    FilterResult,
    LocationNotFoundError,
    filter_restaurants,
    match_cuisine,
    validate_location,
)
from src.services.llm_client import _cache_key, call_llm
from src.services.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════


@router.get("/health", tags=["system"])
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns the service status, dataset row count, and
    whether the Groq API key is configured.
    """
    df = request.app.state.df
    dataset_loaded = df is not None and len(df) > 0

    return {
        "status": "healthy" if dataset_loaded else "degraded",
        "dataset_loaded": dataset_loaded,
        "dataset_rows": len(df) if df is not None else 0,
        "groq_api_key_configured": bool(settings.GROQ_API_KEY),
        "llm_model": settings.LLM_MODEL,
    }


# ═══════════════════════════════════════════════════════════════════════
# GET /locations
# ═══════════════════════════════════════════════════════════════════════


@router.get("/locations", tags=["data"])
async def get_locations(request: Request) -> dict:
    """
    Return the sorted list of valid locations from the dataset.

    Used by the frontend to populate the location dropdown.
    """
    indices = request.app.state.indices
    if indices is None:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded yet. Please try again shortly.",
        )

    locations: List[str] = indices.get("locations", [])
    return {
        "count": len(locations),
        "locations": locations,
    }


# ═══════════════════════════════════════════════════════════════════════
# GET /cuisines
# ═══════════════════════════════════════════════════════════════════════


@router.get("/cuisines", tags=["data"])
async def get_cuisines(request: Request) -> dict:
    """
    Return the sorted list of known cuisine types from the dataset.

    Used by the frontend to populate the cuisine autocomplete.
    """
    indices = request.app.state.indices
    if indices is None:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded yet. Please try again shortly.",
        )

    cuisines: List[str] = indices.get("cuisines", [])
    return {
        "count": len(cuisines),
        "cuisines": cuisines,
    }


# ═══════════════════════════════════════════════════════════════════════
# POST /recommend
# ═══════════════════════════════════════════════════════════════════════


@router.post("/recommend", tags=["recommendation"], response_model=RecommendationResponse)
async def recommend(request: Request, body: RecommendationRequest):
    """
    Main recommendation endpoint.

    Orchestrates the full pipeline:
        1. Validate inputs (location, cuisine)
        2. Filter restaurant candidates
        3. Build LLM prompt from candidates + preferences
        4. Call the Groq LLM for ranked recommendations
        5. Return structured response with metadata

    Returns 422 for validation errors, 503 for LLM failures.
    """
    start_time = time.time()

    df = request.app.state.df
    indices = request.app.state.indices

    # Guard: dataset must be loaded
    if df is None or indices is None:
        raise HTTPException(
            status_code=503,
            detail="Dataset not loaded. The server is still initialising.",
        )

    known_locations = indices.get("locations", [])
    known_cuisines = indices.get("cuisines", [])

    # ── 1. Validate & resolve location ────────────────────────────────
    try:
        matched_location = validate_location(body.location, known_locations)
    except LocationNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "user_location": exc.user_location,
                "suggestions": exc.suggestions,
                "valid_locations_sample": known_locations[:20],
            },
        )

    # ── 2. Resolve cuisine (fuzzy match) ──────────────────────────────
    matched_cuisine = match_cuisine(body.cuisine, known_cuisines)

    # ── 3. Filter candidates ──────────────────────────────────────────
    try:
        filter_result: FilterResult = filter_restaurants(
            df=df,
            indices=indices,
            location=matched_location,
            budget=body.budget,
            cuisine=matched_cuisine,
            min_rating=body.min_rating,
        )
    except Exception as exc:
        logger.error("Filter engine error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while filtering restaurants. Please try again.",
        )

    candidates_df = filter_result.candidates

    # If no candidates at all, return early with a helpful message
    if candidates_df.empty:
        elapsed_ms = (time.time() - start_time) * 1000
        return RecommendationResponse(
            success=True,
            recommendations=[],
            filter_metadata=FilterMetadata(
                total_restaurants=len(df),
                candidates_found=0,
                filters_applied=filter_result.filters_applied,
                constraints_relaxed=filter_result.constraints_relaxed,
                matched_location=filter_result.matched_location,
                matched_cuisine=filter_result.matched_cuisine,
            ),
            model_used=settings.LLM_MODEL,
            response_time_ms=round(elapsed_ms, 1),
            message=(
                f"No restaurants found in '{matched_location}' matching your criteria. "
                "Try broadening your budget or lowering the minimum rating."
            ),
        )

    # ── 4. Build prompt & call LLM ────────────────────────────────────
    messages = build_prompt(
        location=matched_location,
        budget=body.budget,
        candidates_df=candidates_df,
        cuisine=matched_cuisine,
        min_rating=body.min_rating,
        additional_preferences=body.additional_preferences,
    )

    cache_key = _cache_key(
        location=matched_location,
        budget=body.budget,
        cuisine=matched_cuisine,
        min_rating=body.min_rating,
        additional_preferences=body.additional_preferences,
    )

    try:
        recommendations: List[RestaurantRecommendation] = call_llm(
            messages=messages,
            cache_key_str=cache_key,
        )
    except (RuntimeError, ValueError, ImportError) as exc:
        logger.error("LLM call failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "message": "The AI recommendation service is temporarily unavailable. Please try again later.",
                "error_type": type(exc).__name__,
            },
        )

    # ── 5. Build response ─────────────────────────────────────────────
    elapsed_ms = (time.time() - start_time) * 1000

    # Build informational message if constraints were relaxed
    message = None
    if filter_result.constraints_relaxed:
        relaxed_str = ", ".join(filter_result.constraints_relaxed)
        message = (
            f"Some filters were relaxed to find more results: {relaxed_str}. "
            "Results may include restaurants outside your original criteria."
        )

    return RecommendationResponse(
        success=True,
        recommendations=recommendations,
        filter_metadata=FilterMetadata(
            total_restaurants=len(df),
            candidates_found=len(candidates_df),
            filters_applied=filter_result.filters_applied,
            constraints_relaxed=filter_result.constraints_relaxed,
            matched_location=filter_result.matched_location,
            matched_cuisine=filter_result.matched_cuisine,
        ),
        model_used=settings.LLM_MODEL,
        response_time_ms=round(elapsed_ms, 1),
        message=message,
    )
