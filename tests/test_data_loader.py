"""
test_data_loader.py — Unit tests for data loading and preprocessing.

Tests cover:
  - Dataset schema validation (expected columns exist)
  - Preprocessing produces correct column names and types
  - Rating parsing edge cases (4.1/5, NEW, -, NaN)
  - Cost parsing edge cases (1,200 / N/A / negative)
  - Boolean parsing (Yes/No → True/False)
  - Missing-value handling (rows with null name/location are dropped)
  - Deduplication (same name+location keeps highest votes)
  - Index building (location and cuisine lookups)
"""

import pandas as pd
# pyrefly: ignore [missing-import]
import pytest

from src.data.preprocessor import (
    _parse_bool,
    _parse_cost,
    _parse_rating,
    build_indices,
    preprocess,
    validate_schema,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


def _make_raw_df(rows: list[dict] | None = None) -> pd.DataFrame:
    """
    Build a minimal raw DataFrame mimicking the Hugging Face dataset
    schema. If *rows* is None, returns a sensible default set.
    """
    if rows is None:
        rows = [
            {
                "url": "https://zomato.com/r1",
                "address": "123 MG Road",
                "name": "Pizza Palace",
                "online_order": "Yes",
                "book_table": "No",
                "rate": "4.1/5",
                "votes": 300,
                "phone": "9876543210",
                "location": "Koramangala",
                "rest_type": "Casual Dining",
                "dish_liked": "Margherita Pizza",
                "cuisines": "Italian, Pizza",
                "approx_cost(for two people)": "800",
                "reviews_list": "[]",
                "menu_item": "Pizza, Pasta",
                "listed_in(type)": "Delivery",
                "listed_in(city)": "Bangalore",
            },
            {
                "url": "https://zomato.com/r2",
                "address": "456 Brigade Road",
                "name": "Dragon Wok",
                "online_order": "Yes",
                "book_table": "Yes",
                "rate": "3.8/5",
                "votes": 150,
                "phone": "9876543211",
                "location": "Indiranagar",
                "rest_type": "Casual Dining",
                "dish_liked": "Chilli Chicken",
                "cuisines": "Chinese, Thai",
                "approx_cost(for two people)": "1,200",
                "reviews_list": "[]",
                "menu_item": "Noodles",
                "listed_in(type)": "Dine-out",
                "listed_in(city)": "Bangalore",
            },
            {
                "url": "https://zomato.com/r3",
                "address": "789 Church Street",
                "name": "Café Mocha",
                "online_order": "No",
                "book_table": "No",
                "rate": "NEW",
                "votes": 0,
                "phone": "9876543212",
                "location": "Koramangala",
                "rest_type": "Café",
                "dish_liked": "",
                "cuisines": "Coffee, Beverages",
                "approx_cost(for two people)": "400",
                "reviews_list": "[]",
                "menu_item": "Latte",
                "listed_in(type)": "Delivery",
                "listed_in(city)": "Bangalore",
            },
        ]
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# Schema Validation
# ═══════════════════════════════════════════════════════════════════════


class TestSchemaValidation:
    """Tests for validate_schema()."""

    def test_valid_schema_passes(self):
        df = _make_raw_df()
        validate_schema(df)  # should not raise

    def test_missing_required_column_raises(self):
        df = _make_raw_df()
        df = df.drop(columns=["name"])
        with pytest.raises(ValueError, match="Missing columns"):
            validate_schema(df)

    def test_missing_multiple_columns_reports_all(self):
        df = _make_raw_df()
        df = df.drop(columns=["name", "location"])
        with pytest.raises(ValueError, match="name"):
            validate_schema(df)


# ═══════════════════════════════════════════════════════════════════════
# Rating Parsing
# ═══════════════════════════════════════════════════════════════════════


class TestRatingParsing:
    """Tests for _parse_rating()."""

    @pytest.mark.parametrize(
        "input_val, expected",
        [
            ("4.1/5", 4.1),
            ("3.8/5", 3.8),
            ("4.5", 4.5),
            ("5.0", 5.0),
            ("0", 0.0),
        ],
    )
    def test_numeric_ratings(self, input_val, expected):
        assert _parse_rating(input_val) == expected

    @pytest.mark.parametrize(
        "input_val",
        ["NEW", "new", "-", "", "nan", "None", None],
    )
    def test_non_numeric_returns_zero(self, input_val):
        assert _parse_rating(input_val) == 0.0

    def test_rating_clamped_to_max_five(self):
        assert _parse_rating("7.2") == 5.0

    def test_negative_rating_clamped_to_zero(self):
        assert _parse_rating("-0.5") == 0.0

    def test_nan_value(self):
        assert _parse_rating(float("nan")) == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Cost Parsing
# ═══════════════════════════════════════════════════════════════════════


class TestCostParsing:
    """Tests for _parse_cost()."""

    def test_plain_number(self):
        assert _parse_cost("800") == 800.0

    def test_comma_separated(self):
        assert _parse_cost("1,200") == 1200.0

    def test_with_currency_symbol(self):
        assert _parse_cost("₹800") == 800.0

    def test_na_returns_zero(self):
        assert _parse_cost("N/A") == 0.0

    def test_none_returns_zero(self):
        assert _parse_cost(None) == 0.0

    def test_negative_returns_zero(self):
        assert _parse_cost("-100") == 0.0

    def test_nan_returns_zero(self):
        assert _parse_cost(float("nan")) == 0.0

    def test_empty_string_returns_zero(self):
        assert _parse_cost("") == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Boolean Parsing
# ═══════════════════════════════════════════════════════════════════════


class TestBoolParsing:
    """Tests for _parse_bool()."""

    @pytest.mark.parametrize("val", ["Yes", "yes", "YES", "True", "true", "1"])
    def test_truthy_values(self, val):
        assert _parse_bool(val) is True

    @pytest.mark.parametrize("val", ["No", "no", "NO", "False", "false", "0", ""])
    def test_falsy_values(self, val):
        assert _parse_bool(val) is False

    def test_none_returns_false(self):
        assert _parse_bool(None) is False


# ═══════════════════════════════════════════════════════════════════════
# Preprocessing Pipeline
# ═══════════════════════════════════════════════════════════════════════


class TestPreprocess:
    """Tests for the full preprocess() pipeline."""

    def test_output_has_expected_columns(self):
        df = preprocess(_make_raw_df())
        expected = {
            "name", "url", "address", "location", "city", "cuisines",
            "average_cost", "rating", "votes", "online_order", "book_table",
            "rest_type", "dish_liked", "menu_item", "listed_in_type",
        }
        assert expected.issubset(set(df.columns))

    def test_rating_column_is_float(self):
        df = preprocess(_make_raw_df())
        assert df["rating"].dtype == float

    def test_average_cost_column_is_float(self):
        df = preprocess(_make_raw_df())
        assert df["average_cost"].dtype == float

    def test_votes_column_is_int(self):
        df = preprocess(_make_raw_df())
        assert pd.api.types.is_integer_dtype(df["votes"])

    def test_online_order_is_bool(self):
        df = preprocess(_make_raw_df())
        assert df["online_order"].dtype == bool

    def test_book_table_is_bool(self):
        df = preprocess(_make_raw_df())
        assert df["book_table"].dtype == bool

    def test_no_null_names(self):
        df = preprocess(_make_raw_df())
        assert df["name"].isna().sum() == 0
        assert (df["name"].str.strip() == "").sum() == 0

    def test_no_null_locations(self):
        df = preprocess(_make_raw_df())
        assert df["location"].isna().sum() == 0
        assert (df["location"].str.strip() == "").sum() == 0

    def test_new_rating_becomes_zero(self):
        df = preprocess(_make_raw_df())
        cafe_row = df[df["name"] == "Café Mocha"].iloc[0]
        assert cafe_row["rating"] == 0.0

    def test_comma_cost_parsed_correctly(self):
        df = preprocess(_make_raw_df())
        dragon_row = df[df["name"] == "Dragon Wok"].iloc[0]
        assert dragon_row["average_cost"] == 1200.0

    def test_rows_with_missing_name_are_dropped(self):
        rows = [
            {
                "name": None,
                "location": "Koramangala",
                "rate": "4.0/5",
                "votes": 10,
                "cuisines": "Indian",
                "approx_cost(for two people)": "500",
                "online_order": "Yes",
                "book_table": "No",
            },
            {
                "name": "Valid Restaurant",
                "location": "Indiranagar",
                "rate": "3.5/5",
                "votes": 50,
                "cuisines": "Chinese",
                "approx_cost(for two people)": "600",
                "online_order": "No",
                "book_table": "No",
            },
        ]
        df = preprocess(pd.DataFrame(rows))
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Valid Restaurant"

    def test_rows_with_empty_name_are_dropped(self):
        rows = [
            {
                "name": "   ",
                "location": "Koramangala",
                "rate": "4.0/5",
                "votes": 10,
                "cuisines": "Indian",
                "approx_cost(for two people)": "500",
                "online_order": "Yes",
                "book_table": "No",
            },
        ]
        df = preprocess(pd.DataFrame(rows))
        assert len(df) == 0

    def test_deduplication_keeps_highest_votes(self):
        rows = [
            {
                "name": "Same Place",
                "location": "Koramangala",
                "rate": "3.5/5",
                "votes": 50,
                "cuisines": "Indian",
                "approx_cost(for two people)": "500",
                "online_order": "Yes",
                "book_table": "No",
            },
            {
                "name": "Same Place",
                "location": "Koramangala",
                "rate": "4.0/5",
                "votes": 200,
                "cuisines": "Indian, North Indian",
                "approx_cost(for two people)": "600",
                "online_order": "Yes",
                "book_table": "Yes",
            },
        ]
        df = preprocess(pd.DataFrame(rows))
        assert len(df) == 1
        assert df.iloc[0]["votes"] == 200

    def test_cuisines_trimmed(self):
        rows = [
            {
                "name": "Trimmer",
                "location": "HSR",
                "rate": "4.0/5",
                "votes": 10,
                "cuisines": "  Italian ,  Pizza , Pasta  ",
                "approx_cost(for two people)": "700",
                "online_order": "Yes",
                "book_table": "No",
            },
        ]
        df = preprocess(pd.DataFrame(rows))
        assert df.iloc[0]["cuisines"] == "Italian, Pizza, Pasta"


# ═══════════════════════════════════════════════════════════════════════
# Index Building
# ═══════════════════════════════════════════════════════════════════════


class TestBuildIndices:
    """Tests for build_indices()."""

    def test_locations_are_unique_and_sorted(self):
        df = preprocess(_make_raw_df())
        indices = build_indices(df)
        locs = indices["locations"]
        assert locs == sorted(set(locs))

    def test_cuisines_are_individual_and_sorted(self):
        df = preprocess(_make_raw_df())
        indices = build_indices(df)
        cuisines = indices["cuisines"]
        # Each cuisine should be a single type, not comma-separated
        for c in cuisines:
            assert "," not in c
        assert cuisines == sorted(cuisines)

    def test_location_index_maps_to_valid_rows(self):
        df = preprocess(_make_raw_df())
        indices = build_indices(df)
        for loc, row_indices in indices["location_index"].items():
            for idx in row_indices:
                assert df.loc[idx, "location"] == loc

    def test_cuisine_index_maps_to_valid_rows(self):
        df = preprocess(_make_raw_df())
        indices = build_indices(df)
        for cuisine, row_indices in indices["cuisine_index"].items():
            for idx in row_indices:
                assert cuisine in df.loc[idx, "cuisines"]

    def test_koramangala_has_two_restaurants(self):
        df = preprocess(_make_raw_df())
        indices = build_indices(df)
        assert len(indices["location_index"]["Koramangala"]) == 2

    def test_italian_cuisine_index_exists(self):
        df = preprocess(_make_raw_df())
        indices = build_indices(df)
        assert "Italian" in indices["cuisines"]
        assert "Italian" in indices["cuisine_index"]
