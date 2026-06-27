"""
predict.py — End-to-end restaurant recommendation prediction.

Loads the Zomato dataset, filters by user preferences, and uses
the Groq LLM to rank and recommend the top 5 restaurants.

Usage:
    python predict.py
"""

import sys
import os
import time
import logging

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("predict")


def main():
    # -- 1. Load & preprocess the dataset --
    logger.info("=" * 60)
    logger.info("AI-Powered Restaurant Recommendation System")
    logger.info("=" * 60)

    from src.data.loader import load_dataset_from_hf
    from src.data.preprocessor import preprocess, build_indices
    from src.services.filter_engine import (
        validate_location,
        match_cuisine,
        filter_restaurants,
        LocationNotFoundError,
    )
    from src.services.prompt_builder import build_prompt
    from src.services.llm_client import call_llm, _cache_key

    start_time = time.time()

    logger.info("Loading dataset from Hugging Face...")
    raw_df = load_dataset_from_hf()

    logger.info("Preprocessing dataset...")
    clean_df = preprocess(raw_df)

    logger.info("Building indices...")
    indices = build_indices(clean_df)

    load_time = time.time() - start_time
    logger.info("Dataset ready: %d restaurants in %.1fs", len(clean_df), load_time)

    # -- 2. User preferences --
    user_location = "Bellandur"
    user_budget = "medium"   # Rs.1500 is the upper bound of medium (Rs.500-1500)
    user_cuisine = None      # No specific cuisine preference
    user_min_rating = 4.2
    user_additional = None

    logger.info("-" * 60)
    logger.info("User preferences:")
    logger.info("  Location:   %s", user_location)
    logger.info("  Budget:     %s (up to Rs.1500)", user_budget)
    logger.info("  Min rating: %.1f", user_min_rating)
    logger.info("-" * 60)

    # -- 3. Validate location --
    try:
        matched_location = validate_location(user_location, indices["locations"])
        logger.info("Location matched: '%s' -> '%s'", user_location, matched_location)
    except LocationNotFoundError as e:
        logger.error(str(e))
        print(f"\n[ERROR] {e}")
        if e.suggestions:
            print(f"   Suggestions: {', '.join(e.suggestions)}")
        print(f"\n   Available locations (sample): {', '.join(indices['locations'][:20])}")
        sys.exit(1)

    # -- 4. Filter restaurants --
    filter_start = time.time()
    result = filter_restaurants(
        df=clean_df,
        indices=indices,
        location=matched_location,
        budget=user_budget,
        cuisine=user_cuisine,
        min_rating=user_min_rating,
    )
    filter_time = time.time() - filter_start

    logger.info(
        "Filter complete: %d candidates in %.3fs",
        len(result.candidates),
        filter_time,
    )
    if result.constraints_relaxed:
        logger.info("Constraints relaxed: %s", result.constraints_relaxed)

    if result.candidates.empty:
        print("\n[ERROR] No restaurants found matching your criteria.")
        print("   Try relaxing your filters (lower rating or different budget).")
        sys.exit(0)

    # Show candidates
    print(f"\n[CANDIDATES] Found {len(result.candidates)} candidate restaurants in {matched_location}:")
    print("-" * 80)
    for i, (_, row) in enumerate(result.candidates.iterrows(), 1):
        print(f"  {i:2d}. {row['name']:<35s} Rating: {row['rating']:.1f}  Cost: Rs.{row['average_cost']:.0f}  ({row['cuisines']})")
    print("-" * 80)

    # -- 5. Build prompt & call LLM --
    logger.info("Building prompt for Groq LLM...")
    messages = build_prompt(
        location=matched_location,
        budget=user_budget,
        candidates_df=result.candidates,
        cuisine=user_cuisine,
        min_rating=user_min_rating,
        additional_preferences=user_additional,
    )

    cache_key = _cache_key(
        matched_location, user_budget, user_cuisine, user_min_rating, user_additional
    )

    logger.info("Calling Groq API (model: llama-3.3-70b-versatile)...")
    llm_start = time.time()

    try:
        recommendations = call_llm(messages, cache_key_str=cache_key)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        print(f"\n[ERROR] LLM call failed: {e}")
        sys.exit(1)

    llm_time = time.time() - llm_start
    total_time = time.time() - start_time

    # -- 6. Display results --
    print("\n" + "=" * 80)
    print("  TOP 5 RESTAURANT RECOMMENDATIONS")
    print(f"  Location: {matched_location} | Budget: {user_budget} | Min Rating: {user_min_rating}")
    print("=" * 80)

    if not recommendations:
        print("\n  [WARNING] The LLM did not return any recommendations.")
        print("  Showing filtered candidates instead.")
    else:
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"\n  {'=' * 76}")
            print(f"  #{i}  {rec.restaurant_name}")
            print(f"  {'=' * 76}")
            print(f"  Cuisine:     {rec.cuisine}")
            print(f"  Rating:      {rec.rating}/5")
            print(f"  Cost:        {rec.estimated_cost}")
            print(f"  Why:         {rec.explanation}")

    print(f"\n{'-' * 80}")
    print(f"  Timing:  Data load: {load_time:.1f}s | Filter: {filter_time:.3f}s | LLM: {llm_time:.1f}s | Total: {total_time:.1f}s")
    print(f"  Stats:   Candidates evaluated: {len(result.candidates)}")
    if result.constraints_relaxed:
        print(f"  Notice:  Constraints relaxed: {', '.join(result.constraints_relaxed)}")
    print(f"{'-' * 80}\n")


if __name__ == "__main__":
    main()
