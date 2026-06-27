"""
llm_client.py — Groq LLM API integration.

Handles sending prompts to the Groq API, retries with exponential
backoff, rate limiting, response parsing, and caching.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from src.config import settings
from src.models.schemas import RestaurantRecommendation

logger = logging.getLogger(__name__)

# ── Simple in-memory cache ────────────────────────────────────────────
_cache: Dict[str, tuple[float, Any]] = {}  # key → (timestamp, value)


def _cache_key(
    location: str,
    budget: str,
    cuisine: Optional[str],
    min_rating: float,
    additional_preferences: Optional[str],
) -> str:
    """Generate a deterministic cache key from the request parameters."""
    raw = f"{location}|{budget}|{cuisine}|{min_rating}|{additional_preferences}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cached(key: str) -> Optional[List[RestaurantRecommendation]]:
    """Return cached result if still valid (within TTL), else None."""
    if key in _cache:
        ts, value = _cache[key]
        if time.time() - ts < settings.CACHE_TTL_SECONDS:
            logger.info("Cache hit for key %s…", key[:12])
            return value
        else:
            del _cache[key]
    return None


def _set_cache(key: str, value: List[RestaurantRecommendation]) -> None:
    """Store a result in the cache."""
    _cache[key] = (time.time(), value)


def call_llm(
    messages: list[dict[str, str]],
    cache_key_str: Optional[str] = None,
) -> List[RestaurantRecommendation]:
    """
    Send a prompt to the Groq API and parse the response.

    Implements:
        - Retry with exponential backoff (max 3 retries)
        - Rate limiting (HTTP 429) and server error (5xx) handling
        - JSON response parsing into RestaurantRecommendation models
        - In-memory caching

    Args:
        messages:       Chat messages list (from prompt_builder.build_prompt).
        cache_key_str:  Optional pre-computed cache key. If provided and a
                        cached result exists, the API call is skipped.

    Returns:
        List of RestaurantRecommendation objects.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    # Check cache
    if cache_key_str:
        cached = _get_cached(cache_key_str)
        if cached is not None:
            return cached

    # Lazy import to avoid import errors if groq is not installed
    try:
        from groq import Groq
    except ImportError:
        raise ImportError(
            "The 'groq' package is required. Install it with: pip install groq"
        )

    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )

    client = Groq(api_key=settings.GROQ_API_KEY)

    last_error = None
    for attempt in range(1, settings.LLM_MAX_RETRIES + 1):
        try:
            logger.info(
                "Groq API call attempt %d/%d (model=%s)…",
                attempt,
                settings.LLM_MAX_RETRIES,
                settings.LLM_MODEL,
            )

            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
                timeout=settings.LLM_TIMEOUT,
            )

            raw_content = response.choices[0].message.content
            logger.debug("Raw LLM response: %s", raw_content[:500])

            recommendations = _parse_response(raw_content)

            # Cache the result
            if cache_key_str:
                _set_cache(cache_key_str, recommendations)

            return recommendations

        except Exception as exc:
            last_error = exc
            error_str = str(exc)

            # Check if rate limited (429) or server error (5xx)
            is_retryable = (
                "429" in error_str
                or "rate" in error_str.lower()
                or "500" in error_str
                or "502" in error_str
                or "503" in error_str
            )

            if is_retryable and attempt < settings.LLM_MAX_RETRIES:
                wait = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                logger.warning(
                    "Retryable error (attempt %d): %s. Waiting %ds…",
                    attempt,
                    error_str[:100],
                    wait,
                )
                time.sleep(wait)
            elif attempt < settings.LLM_MAX_RETRIES:
                # Non-retryable but still have attempts
                wait = 1
                logger.warning(
                    "Error (attempt %d): %s. Retrying in %ds…",
                    attempt,
                    error_str[:100],
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "All %d attempts exhausted. Last error: %s",
                    settings.LLM_MAX_RETRIES,
                    error_str,
                )

    raise RuntimeError(
        f"LLM call failed after {settings.LLM_MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


def _parse_response(raw_content: str) -> List[RestaurantRecommendation]:
    """
    Parse the LLM's JSON response into RestaurantRecommendation models.

    Handles malformed JSON gracefully by returning an empty list.
    """
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM response as JSON: %s", exc)
        logger.debug("Raw content: %s", raw_content[:500])
        return []

    # The LLM should return {"recommendations": [...]}
    recs_data = data.get("recommendations", [])
    if not isinstance(recs_data, list):
        logger.error("'recommendations' is not a list: %s", type(recs_data))
        return []

    recommendations = []
    for item in recs_data:
        try:
            rec = RestaurantRecommendation(
                restaurant_name=item.get("restaurant_name", "Unknown"),
                cuisine=item.get("cuisine", "N/A"),
                rating=float(item.get("rating", 0.0)),
                estimated_cost=str(item.get("estimated_cost", "N/A")),
                explanation=item.get("explanation", "No explanation provided."),
            )
            recommendations.append(rec)
        except Exception as exc:
            logger.warning("Skipping malformed recommendation: %s — %s", item, exc)

    logger.info("Parsed %d recommendations from LLM response.", len(recommendations))
    return recommendations
