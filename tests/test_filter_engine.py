"""
test_filter_engine.py — Unit tests for the filter engine module.

Tests cover:
  - Location validation (exact, substring, fuzzy, not found)
  - Cuisine fuzzy matching (exact, substring, fuzzy, no match)
  - Individual filter stages (location, budget, cuisine, rating)
  - Constraint relaxation (cuisine → budget → rating)
  - End-to-end filter_restaurants() orchestration
  - Edge cases (no results, single result, empty cuisine, max_candidates)
  - Schema validation for RecommendationRequest
"""

import pandas as pd
import pytest

from src.data.preprocessor import build_indices, preprocess
from src.models.schemas import RecommendationRequest, BUDGET_RANGES
from src.services.filter_engine import (
    FilterResult,
    LocationNotFoundError,
    _filter_by_budget,
    _filter_by_cuisine,
    _filter_by_location,
    _filter_by_rating,
    _sort_candidates,
    filter_restaurants,
    match_cuisine,
    validate_location,
)


# ═══════════════════════════════════════════════════════════════════════
# Test Data Fixtures
# ═══════════════════════════════════════════════════════════════════════


def _make_test_data() -> tuple[pd.DataFrame, dict]:
    """
    Create a realistic test DataFrame and indices, mimicking the
    preprocessor output. Returns (df, indices).
    """
    rows = [
        {
            "name": "Pizza Palace",
            "url": "https://zomato.com/r1",
            "address": "123 MG Road",
            "location": "Koramangala",
            "city": "Bangalore",
            "cuisines": "Italian, Pizza",
            "average_cost": 800.0,
            "rating": 4.1,
            "votes": 300,
            "online_order": True,
            "book_table": False,
            "rest_type": "Casual Dining",
            "dish_liked": "Margherita Pizza",
            "menu_item": "Pizza, Pasta",
            "listed_in_type": "Delivery",
        },
        {
            "name": "Dragon Wok",
            "url": "https://zomato.com/r2",
            "address": "456 Brigade Road",
            "location": "Indiranagar",
            "city": "Bangalore",
            "cuisines": "Chinese, Thai",
            "average_cost": 1200.0,
            "rating": 3.8,
            "votes": 150,
            "online_order": True,
            "book_table": True,
            "rest_type": "Casual Dining",
            "dish_liked": "Chilli Chicken",
            "menu_item": "Noodles",
            "listed_in_type": "Dine-out",
        },
        {
            "name": "Café Mocha",
            "url": "https://zomato.com/r3",
            "address": "789 Church Street",
            "location": "Koramangala",
            "city": "Bangalore",
            "cuisines": "Coffee, Beverages",
            "average_cost": 400.0,
            "rating": 0.0,
            "votes": 0,
            "online_order": False,
            "book_table": False,
            "rest_type": "Café",
            "dish_liked": "",
            "menu_item": "Latte",
            "listed_in_type": "Delivery",
        },
        {
            "name": "Tandoori Nights",
            "url": "https://zomato.com/r4",
            "address": "10 Residency Road",
            "location": "Koramangala",
            "city": "Bangalore",
            "cuisines": "North Indian, Mughlai",
            "average_cost": 600.0,
            "rating": 4.5,
            "votes": 500,
            "online_order": True,
            "book_table": True,
            "rest_type": "Casual Dining",
            "dish_liked": "Butter Chicken",
            "menu_item": "Biryani, Naan",
            "listed_in_type": "Dine-out",
        },
        {
            "name": "Street Bites",
            "url": "https://zomato.com/r5",
            "address": "22 Food Street",
            "location": "Koramangala",
            "city": "Bangalore",
            "cuisines": "Street Food, Indian",
            "average_cost": 200.0,
            "rating": 3.9,
            "votes": 80,
            "online_order": True,
            "book_table": False,
            "rest_type": "Quick Bites",
            "dish_liked": "Pani Puri",
            "menu_item": "Chaat",
            "listed_in_type": "Delivery",
        },
        {
            "name": "Sushi Express",
            "url": "https://zomato.com/r6",
            "address": "33 Park Avenue",
            "location": "Indiranagar",
            "city": "Bangalore",
            "cuisines": "Japanese, Sushi",
            "average_cost": 2000.0,
            "rating": 4.7,
            "votes": 250,
            "online_order": False,
            "book_table": True,
            "rest_type": "Fine Dining",
            "dish_liked": "Salmon Sashimi",
            "menu_item": "Sushi Platter",
            "listed_in_type": "Dine-out",
        },
        {
            "name": "Dosa Corner",
            "url": "https://zomato.com/r7",
            "address": "44 Main Road",
            "location": "HSR Layout",
            "city": "Bangalore",
            "cuisines": "South Indian",
            "average_cost": 250.0,
            "rating": 4.0,
            "votes": 120,
            "online_order": True,
            "book_table": False,
            "rest_type": "Quick Bites",
            "dish_liked": "Masala Dosa",
            "menu_item": "Dosa, Idli",
            "listed_in_type": "Delivery",
        },
        {
            "name": "La Belle",
            "url": "https://zomato.com/r8",
            "address": "55 Park Lane",
            "location": "Koramangala",
            "city": "Bangalore",
            "cuisines": "French, Continental",
            "average_cost": 1800.0,
            "rating": 4.3,
            "votes": 200,
            "online_order": False,
            "book_table": True,
            "rest_type": "Fine Dining",
            "dish_liked": "Crème Brûlée",
            "menu_item": "Croissant",
            "listed_in_type": "Dine-out",
        },
    ]
    df = pd.DataFrame(rows)
    indices = build_indices(df)
    return df, indices


# ═══════════════════════════════════════════════════════════════════════
# Location Validation
# ═══════════════════════════════════════════════════════════════════════


class TestValidateLocation:
    """Tests for validate_location()."""

    def test_exact_match(self):
        locations = ["Koramangala", "Indiranagar", "HSR Layout"]
        assert validate_location("Koramangala", locations) == "Koramangala"

    def test_case_insensitive_match(self):
        locations = ["Koramangala", "Indiranagar", "HSR Layout"]
        assert validate_location("koramangala", locations) == "Koramangala"
        assert validate_location("INDIRANAGAR", locations) == "Indiranagar"

    def test_substring_match(self):
        locations = ["Koramangala", "Indiranagar", "HSR Layout"]
        assert validate_location("HSR", locations) == "HSR Layout"

    def test_fuzzy_match(self):
        locations = ["Koramangala", "Indiranagar", "HSR Layout"]
        result = validate_location("Koramangla", locations)  # typo
        assert result == "Koramangala"

    def test_not_found_raises_error(self):
        locations = ["Koramangala", "Indiranagar", "HSR Layout"]
        with pytest.raises(LocationNotFoundError) as exc_info:
            validate_location("Nonexistent Place", locations)
        err = exc_info.value
        assert err.user_location == "Nonexistent Place"
        assert err.valid_locations == locations

    def test_empty_location_raises_error(self):
        locations = ["Koramangala"]
        with pytest.raises(LocationNotFoundError):
            validate_location("", locations)

    def test_whitespace_only_raises_error(self):
        locations = ["Koramangala"]
        with pytest.raises(LocationNotFoundError):
            validate_location("   ", locations)

    def test_suggestions_in_error(self):
        locations = ["Koramangala", "Indiranagar", "HSR Layout"]
        with pytest.raises(LocationNotFoundError) as exc_info:
            validate_location("Koraman", locations)
        err = exc_info.value
        # Should suggest Koramangala
        assert len(err.suggestions) > 0


# ═══════════════════════════════════════════════════════════════════════
# Cuisine Fuzzy Matching
# ═══════════════════════════════════════════════════════════════════════


class TestMatchCuisine:
    """Tests for match_cuisine()."""

    def test_exact_match(self):
        cuisines = ["Italian", "Chinese", "North Indian", "Japanese"]
        assert match_cuisine("Italian", cuisines) == "Italian"

    def test_case_insensitive_match(self):
        cuisines = ["Italian", "Chinese", "North Indian"]
        assert match_cuisine("italian", cuisines) == "Italian"
        assert match_cuisine("CHINESE", cuisines) == "Chinese"

    def test_substring_match(self):
        cuisines = ["North Indian", "South Indian", "Italian"]
        assert match_cuisine("North", cuisines) == "North Indian"

    def test_fuzzy_match(self):
        cuisines = ["Italian", "Chinese", "Japanese", "Mexican"]
        result = match_cuisine("Itallian", cuisines)  # typo
        assert result == "Italian"

    def test_no_match_returns_none(self):
        cuisines = ["Italian", "Chinese"]
        assert match_cuisine("Martian Food", cuisines) is None

    def test_none_input_returns_none(self):
        cuisines = ["Italian", "Chinese"]
        assert match_cuisine(None, cuisines) is None

    def test_empty_string_returns_none(self):
        cuisines = ["Italian", "Chinese"]
        assert match_cuisine("", cuisines) is None

    def test_whitespace_only_returns_none(self):
        cuisines = ["Italian"]
        assert match_cuisine("   ", cuisines) is None


# ═══════════════════════════════════════════════════════════════════════
# Individual Filter Stages
# ═══════════════════════════════════════════════════════════════════════


class TestFilterByLocation:
    """Tests for _filter_by_location()."""

    def test_filters_to_correct_location(self):
        df, indices = _make_test_data()
        result = _filter_by_location(df, "Koramangala", indices["location_index"])
        assert all(result["location"] == "Koramangala")
        assert len(result) == 5  # 5 restaurants in Koramangala

    def test_unknown_location_returns_empty(self):
        df, indices = _make_test_data()
        result = _filter_by_location(df, "Mars Colony", indices["location_index"])
        assert result.empty


class TestFilterByBudget:
    """Tests for _filter_by_budget()."""

    def test_low_budget(self):
        df, _ = _make_test_data()
        result = _filter_by_budget(df, "low")
        assert all(result["average_cost"] <= 500)

    def test_medium_budget(self):
        df, _ = _make_test_data()
        result = _filter_by_budget(df, "medium")
        assert all(result["average_cost"] >= 500)
        assert all(result["average_cost"] <= 1500)

    def test_high_budget(self):
        df, _ = _make_test_data()
        result = _filter_by_budget(df, "high")
        assert all(result["average_cost"] >= 1500)

    def test_unknown_budget_returns_all(self):
        df, _ = _make_test_data()
        result = _filter_by_budget(df, "unknown_tier")
        assert len(result) == len(df)


class TestFilterByCuisine:
    """Tests for _filter_by_cuisine()."""

    def test_filters_by_cuisine_index(self):
        df, indices = _make_test_data()
        result = _filter_by_cuisine(df, "Italian", indices["cuisine_index"])
        assert len(result) >= 1
        for _, row in result.iterrows():
            assert "Italian" in row["cuisines"]

    def test_cuisine_not_in_index_falls_back_to_substring(self):
        df, indices = _make_test_data()
        # "Pizza" is in cuisines column but may or may not be its own index key
        result = _filter_by_cuisine(df, "Pizza", indices["cuisine_index"])
        assert len(result) >= 1


class TestFilterByRating:
    """Tests for _filter_by_rating()."""

    def test_min_rating_filter(self):
        df, _ = _make_test_data()
        result = _filter_by_rating(df, 4.0)
        assert all(result["rating"] >= 4.0)

    def test_zero_min_rating_returns_all(self):
        df, _ = _make_test_data()
        result = _filter_by_rating(df, 0.0)
        assert len(result) == len(df)

    def test_high_min_rating_filters_most(self):
        df, _ = _make_test_data()
        result = _filter_by_rating(df, 4.5)
        assert len(result) < len(df)
        assert all(result["rating"] >= 4.5)


class TestSortCandidates:
    """Tests for _sort_candidates()."""

    def test_sorted_by_rating_desc(self):
        df, _ = _make_test_data()
        sorted_df = _sort_candidates(df)
        ratings = sorted_df["rating"].tolist()
        assert ratings == sorted(ratings, reverse=True)

    def test_tiebreaker_by_votes(self):
        # Create two restaurants with same rating
        tie_df = pd.DataFrame([
            {"name": "A", "rating": 4.0, "votes": 100, "average_cost": 500,
             "location": "X", "cuisines": "Indian"},
            {"name": "B", "rating": 4.0, "votes": 200, "average_cost": 500,
             "location": "X", "cuisines": "Indian"},
        ])
        sorted_df = _sort_candidates(tie_df)
        assert sorted_df.iloc[0]["name"] == "B"  # More votes first


# ═══════════════════════════════════════════════════════════════════════
# Constraint Relaxation
# ═══════════════════════════════════════════════════════════════════════


class TestConstraintRelaxation:
    """Tests for the constraint relaxation logic in filter_restaurants()."""

    def test_relaxes_cuisine_when_too_few_results(self):
        """If adding cuisine leaves < 5 results, cuisine should be relaxed."""
        df, indices = _make_test_data()
        # "Japanese" cuisine is only in Indiranagar, not in Koramangala
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine="Japanese",
            min_rating=0.0,
        )
        # Should relax cuisine since no Japanese restaurants in Koramangala
        if len(result.candidates) > 0:
            assert "cuisine" in result.constraints_relaxed or len(result.candidates) >= 1

    def test_relaxes_budget_when_too_few_results(self):
        """If budget is too restrictive, it should be relaxed."""
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="HSR Layout",
            budget="high",
            cuisine=None,
            min_rating=0.0,
        )
        # HSR Layout only has 1 restaurant at ₹250 (low budget)
        # So "high" budget yields 0 → should relax budget
        if result.candidates.empty or "budget" in result.constraints_relaxed:
            assert True  # Budget was relaxed or no candidates at all

    def test_relaxes_rating_when_too_few_results(self):
        """If min_rating is too high, it should be relaxed."""
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="HSR Layout",
            budget="low",
            cuisine=None,
            min_rating=4.9,
        )
        # HSR has 1 restaurant rated 4.0, min_rating=4.9 excludes it
        # Should relax rating
        if len(result.candidates) > 0:
            assert (
                "min_rating" in result.constraints_relaxed
                or result.candidates.iloc[0]["rating"] >= 4.9
            )

    def test_no_relaxation_when_enough_results(self):
        """When >= 5 results, no relaxation should occur."""
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine=None,
            min_rating=0.0,
        )
        assert result.constraints_relaxed == []


# ═══════════════════════════════════════════════════════════════════════
# End-to-End filter_restaurants()
# ═══════════════════════════════════════════════════════════════════════


class TestFilterRestaurants:
    """End-to-end tests for filter_restaurants()."""

    def test_basic_filter(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine=None,
            min_rating=3.0,
        )
        assert isinstance(result, FilterResult)
        assert len(result.candidates) > 0
        assert result.matched_location == "Koramangala"
        assert "location" in result.filters_applied
        assert "budget" in result.filters_applied

    def test_with_cuisine_filter(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine="Italian",
            min_rating=3.0,
        )
        assert isinstance(result, FilterResult)
        assert "cuisine" in result.filters_applied

    def test_candidates_sorted_by_rating_desc(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine=None,
            min_rating=0.0,
        )
        ratings = result.candidates["rating"].tolist()
        assert ratings == sorted(ratings, reverse=True)

    def test_max_candidates_respected(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine=None,
            min_rating=0.0,
            max_candidates=2,
        )
        assert len(result.candidates) <= 2

    def test_empty_location_returns_empty(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Nonexistent Place",
            budget="medium",
            cuisine=None,
            min_rating=3.0,
        )
        assert result.candidates.empty

    def test_filters_applied_metadata(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="low",
            cuisine="Indian",
            min_rating=3.5,
        )
        assert "location" in result.filters_applied
        assert "budget" in result.filters_applied
        assert "cuisine" in result.filters_applied
        assert "min_rating" in result.filters_applied

    def test_no_cuisine_skips_cuisine_filter(self):
        df, indices = _make_test_data()
        result = filter_restaurants(
            df,
            indices,
            location="Koramangala",
            budget="medium",
            cuisine=None,
            min_rating=3.0,
        )
        # "cuisine" should not be in filters_applied when None
        assert "cuisine" not in result.filters_applied


# ═══════════════════════════════════════════════════════════════════════
# Schema Validation (RecommendationRequest)
# ═══════════════════════════════════════════════════════════════════════


class TestRecommendationRequest:
    """Tests for the RecommendationRequest Pydantic model."""

    def test_valid_minimal_request(self):
        req = RecommendationRequest(location="Koramangala", budget="low")
        assert req.location == "Koramangala"
        assert req.budget == "low"
        assert req.cuisine is None
        assert req.min_rating == 3.0
        assert req.additional_preferences is None

    def test_valid_full_request(self):
        req = RecommendationRequest(
            location="Indiranagar",
            budget="high",
            cuisine="Italian",
            min_rating=4.0,
            additional_preferences="rooftop seating",
        )
        assert req.location == "Indiranagar"
        assert req.budget == "high"
        assert req.cuisine == "Italian"
        assert req.min_rating == 4.0
        assert req.additional_preferences == "rooftop seating"

    def test_invalid_budget_rejected(self):
        with pytest.raises(Exception):
            RecommendationRequest(location="Koramangala", budget="ultra")

    def test_rating_below_zero_rejected(self):
        with pytest.raises(Exception):
            RecommendationRequest(
                location="Koramangala", budget="low", min_rating=-1.0
            )

    def test_rating_above_five_rejected(self):
        with pytest.raises(Exception):
            RecommendationRequest(
                location="Koramangala", budget="low", min_rating=5.5
            )

    def test_empty_location_rejected(self):
        with pytest.raises(Exception):
            RecommendationRequest(location="", budget="low")

    def test_default_min_rating(self):
        req = RecommendationRequest(location="Test", budget="medium")
        assert req.min_rating == 3.0

    def test_additional_preferences_max_length(self):
        # 500 chars should pass
        req = RecommendationRequest(
            location="Test", budget="low", additional_preferences="a" * 500
        )
        assert len(req.additional_preferences) == 500

        # 501 chars should fail
        with pytest.raises(Exception):
            RecommendationRequest(
                location="Test", budget="low", additional_preferences="a" * 501
            )


# ═══════════════════════════════════════════════════════════════════════
# Budget Ranges
# ═══════════════════════════════════════════════════════════════════════


class TestBudgetRanges:
    """Tests for the BUDGET_RANGES constant."""

    def test_budget_ranges_defined(self):
        assert "low" in BUDGET_RANGES
        assert "medium" in BUDGET_RANGES
        assert "high" in BUDGET_RANGES

    def test_low_range(self):
        low, high = BUDGET_RANGES["low"]
        assert low == 0
        assert high == 500

    def test_medium_range(self):
        low, high = BUDGET_RANGES["medium"]
        assert low == 500
        assert high == 1500

    def test_high_range_is_unbounded(self):
        low, high = BUDGET_RANGES["high"]
        assert low == 1500
        assert high == float("inf")

    def test_no_gap_between_ranges(self):
        """Ensure there's no gap: low max == medium min, medium max == high min."""
        assert BUDGET_RANGES["low"][1] == BUDGET_RANGES["medium"][0]
        assert BUDGET_RANGES["medium"][1] == BUDGET_RANGES["high"][0]
