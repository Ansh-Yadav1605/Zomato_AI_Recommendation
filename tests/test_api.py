"""
test_api.py — Integration tests for the FastAPI REST API.

Tests all endpoints: /health, /locations, /cuisines, and /recommend
using both valid and invalid payloads, and verifies error handling.
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock
import pandas as pd

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.main import app, _rate_limit_store
from src.models.schemas import RestaurantRecommendation


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Clear the rate limiter store before each test to prevent leaks."""
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


@pytest.fixture
def sample_df():
    """Create a small test DataFrame mimicking preprocessed restaurant data."""
    data = {
        "name": [
            "Pizza Palace", "Curry House", "Sushi Spot",
            "Burger Joint", "Taco Town", "Pasta Place",
            "Noodle Bar", "Dosa Corner", "Kebab King",
            "Dim Sum Den",
        ],
        "url": ["http://example.com"] * 10,
        "address": ["123 Main St"] * 10,
        "location": [
            "Koramangala", "Koramangala", "Koramangala",
            "Indiranagar", "Indiranagar", "Koramangala",
            "Koramangala", "Koramangala", "Indiranagar",
            "Koramangala",
        ],
        "city": ["Bangalore"] * 10,
        "cuisines": [
            "Italian, Pizza", "Indian, Curry", "Japanese, Sushi",
            "American, Burgers", "Mexican, Tacos", "Italian, Pasta",
            "Chinese, Noodles", "South Indian, Dosa", "North Indian, Kebab",
            "Chinese, Dim Sum",
        ],
        "average_cost": [800, 400, 1200, 600, 350, 1000, 500, 200, 900, 700],
        "rating": [4.2, 4.5, 4.0, 3.8, 4.1, 3.5, 3.9, 4.3, 4.0, 3.7],
        "votes": [500, 800, 300, 450, 200, 150, 350, 600, 400, 250],
        "online_order": [True, True, False, True, True, False, True, True, False, True],
        "book_table": [True, False, True, False, False, True, False, False, True, False],
        "rest_type": ["Casual Dining"] * 10,
        "dish_liked": [""] * 10,
        "menu_item": [""] * 10,
        "listed_in_type": ["Delivery"] * 10,
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_indices(sample_df):
    """Build indices from the sample DataFrame."""
    from src.data.preprocessor import build_indices
    return build_indices(sample_df)


@pytest.fixture
def client(sample_df, sample_indices):
    """
    Create a test client with pre-loaded test dataset.

    Patches the data loading functions so the lifespan event uses
    our test data instead of downloading from Hugging Face.
    """
    with (
        patch("src.main.load_dataset_from_hf", return_value=sample_df),
        patch("src.main.preprocess", return_value=sample_df),
        patch("src.main.build_indices", return_value=sample_indices),
    ):
        with TestClient(app) as tc:
            yield tc


@pytest.fixture
def client_no_data():
    """
    Create a test client with no dataset loaded (degraded mode).

    Patches the data loading to raise an error so the lifespan
    starts the app in degraded mode.
    """
    with patch(
        "src.main.load_dataset_from_hf",
        side_effect=ConnectionError("Test: no data"),
    ):
        with TestClient(app) as tc:
            yield tc


# ═══════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    """Tests for the GET /health endpoint."""

    def test_health_check_with_data(self, client):
        """Health check returns 'healthy' when dataset is loaded."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["dataset_loaded"] is True
        assert data["dataset_rows"] == 10
        assert "llm_model" in data

    def test_health_check_no_data(self, client_no_data):
        """Health check returns 'degraded' when dataset is not loaded."""
        response = client_no_data.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"
        assert data["dataset_loaded"] is False
        assert data["dataset_rows"] == 0


# ═══════════════════════════════════════════════════════════════════════
# GET /locations
# ═══════════════════════════════════════════════════════════════════════


class TestLocationsEndpoint:
    """Tests for the GET /locations endpoint."""

    def test_get_locations(self, client):
        """Returns a list of unique locations from the dataset."""
        response = client.get("/locations")
        assert response.status_code == 200

        data = response.json()
        assert "count" in data
        assert "locations" in data
        assert isinstance(data["locations"], list)
        assert data["count"] == len(data["locations"])

        # Should contain known locations from the test data
        assert "Koramangala" in data["locations"]
        assert "Indiranagar" in data["locations"]

    def test_get_locations_no_data(self, client_no_data):
        """Returns 503 when dataset is not loaded."""
        response = client_no_data.get("/locations")
        assert response.status_code == 503

    def test_locations_are_sorted(self, client):
        """Locations should be returned in alphabetical order."""
        response = client.get("/locations")
        data = response.json()
        locations = data["locations"]
        assert locations == sorted(locations)


# ═══════════════════════════════════════════════════════════════════════
# GET /cuisines
# ═══════════════════════════════════════════════════════════════════════


class TestCuisinesEndpoint:
    """Tests for the GET /cuisines endpoint."""

    def test_get_cuisines(self, client):
        """Returns a list of unique cuisine types from the dataset."""
        response = client.get("/cuisines")
        assert response.status_code == 200

        data = response.json()
        assert "count" in data
        assert "cuisines" in data
        assert isinstance(data["cuisines"], list)
        assert data["count"] == len(data["cuisines"])

        # Should contain known cuisines from the test data
        assert "Italian" in data["cuisines"]
        assert "Indian" in data["cuisines"]
        assert "Chinese" in data["cuisines"]

    def test_get_cuisines_no_data(self, client_no_data):
        """Returns 503 when dataset is not loaded."""
        response = client_no_data.get("/cuisines")
        assert response.status_code == 503

    def test_cuisines_are_sorted(self, client):
        """Cuisines should be returned in alphabetical order."""
        response = client.get("/cuisines")
        data = response.json()
        cuisines = data["cuisines"]
        assert cuisines == sorted(cuisines)


# ═══════════════════════════════════════════════════════════════════════
# POST /recommend
# ═══════════════════════════════════════════════════════════════════════


class TestRecommendEndpoint:
    """Tests for the POST /recommend endpoint."""

    @patch("src.api.routes.call_llm")
    def test_recommend_success(self, mock_call_llm, client):
        """
        Successful recommendation returns 200 with recommendations
        and metadata.
        """
        # Mock the LLM to return predictable results
        mock_call_llm.return_value = [
            RestaurantRecommendation(
                restaurant_name="Pizza Palace",
                cuisine="Italian, Pizza",
                rating=4.2,
                estimated_cost="₹800 for two",
                explanation="Great pizza place with high ratings.",
            ),
            RestaurantRecommendation(
                restaurant_name="Pasta Place",
                cuisine="Italian, Pasta",
                rating=3.5,
                estimated_cost="₹1000 for two",
                explanation="Authentic Italian pasta dishes.",
            ),
        ]

        response = client.post(
            "/recommend",
            json={
                "location": "Koramangala",
                "budget": "medium",
                "cuisine": "Italian",
                "min_rating": 3.0,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["recommendations"]) == 2
        assert data["recommendations"][0]["restaurant_name"] == "Pizza Palace"
        assert data["filter_metadata"]["matched_location"] == "Koramangala"
        assert data["model_used"] is not None
        assert data["response_time_ms"] is not None

    @patch("src.api.routes.call_llm")
    def test_recommend_minimal_request(self, mock_call_llm, client):
        """Only location and budget are required."""
        mock_call_llm.return_value = [
            RestaurantRecommendation(
                restaurant_name="Curry House",
                cuisine="Indian",
                rating=4.5,
                estimated_cost="₹400 for two",
                explanation="Top-rated local favourite.",
            ),
        ]

        response = client.post(
            "/recommend",
            json={"location": "Koramangala", "budget": "low"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_recommend_invalid_location(self, client):
        """Invalid location returns 422 with suggestions."""
        response = client.post(
            "/recommend",
            json={"location": "Nonexistent Place", "budget": "medium"},
        )
        assert response.status_code == 422

        data = response.json()
        detail = data["detail"]
        assert "Nonexistent Place" in detail.get("message", "") or "user_location" in detail

    def test_recommend_missing_location(self, client):
        """Missing required field returns 422."""
        response = client.post(
            "/recommend",
            json={"budget": "medium"},
        )
        assert response.status_code == 422

    def test_recommend_missing_budget(self, client):
        """Missing required budget field returns 422."""
        response = client.post(
            "/recommend",
            json={"location": "Koramangala"},
        )
        assert response.status_code == 422

    def test_recommend_invalid_budget(self, client):
        """Invalid budget value returns 422."""
        response = client.post(
            "/recommend",
            json={"location": "Koramangala", "budget": "ultra"},
        )
        assert response.status_code == 422

    def test_recommend_invalid_rating_too_high(self, client):
        """Rating above 5.0 returns 422."""
        response = client.post(
            "/recommend",
            json={
                "location": "Koramangala",
                "budget": "medium",
                "min_rating": 6.0,
            },
        )
        assert response.status_code == 422

    def test_recommend_invalid_rating_too_low(self, client):
        """Rating below 0.0 returns 422."""
        response = client.post(
            "/recommend",
            json={
                "location": "Koramangala",
                "budget": "medium",
                "min_rating": -1.0,
            },
        )
        assert response.status_code == 422

    @patch("src.api.routes.call_llm")
    def test_recommend_with_additional_preferences(self, mock_call_llm, client):
        """Additional preferences are passed through to the LLM."""
        mock_call_llm.return_value = []

        response = client.post(
            "/recommend",
            json={
                "location": "Koramangala",
                "budget": "high",
                "additional_preferences": "family-friendly with outdoor seating",
            },
        )
        assert response.status_code == 200

    def test_recommend_no_data(self, client_no_data):
        """Returns 503 when dataset is not loaded."""
        response = client_no_data.post(
            "/recommend",
            json={"location": "Koramangala", "budget": "medium"},
        )
        assert response.status_code == 503

    @patch("src.api.routes.call_llm")
    def test_recommend_llm_failure(self, mock_call_llm, client):
        """Returns 503 when the LLM call fails."""
        mock_call_llm.side_effect = RuntimeError("LLM service unavailable")

        response = client.post(
            "/recommend",
            json={"location": "Koramangala", "budget": "medium"},
        )
        assert response.status_code == 503

    @patch("src.api.routes.call_llm")
    def test_recommend_response_metadata(self, mock_call_llm, client):
        """Response includes filter metadata and timing info."""
        mock_call_llm.return_value = []

        response = client.post(
            "/recommend",
            json={"location": "Koramangala", "budget": "medium"},
        )
        assert response.status_code == 200

        data = response.json()
        metadata = data.get("filter_metadata")
        assert metadata is not None
        assert "total_restaurants" in metadata
        assert "candidates_found" in metadata
        assert "filters_applied" in metadata
        assert isinstance(metadata["filters_applied"], list)

    @patch("src.api.routes.call_llm")
    def test_recommend_fuzzy_location(self, mock_call_llm, client):
        """Fuzzy location matching works (e.g., lowercase input)."""
        mock_call_llm.return_value = []

        response = client.post(
            "/recommend",
            json={"location": "koramangala", "budget": "medium"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filter_metadata"]["matched_location"] == "Koramangala"


# ═══════════════════════════════════════════════════════════════════════
# Error Handling & Middleware
# ═══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    """Tests for error handling and middleware behaviour."""

    def test_404_for_unknown_route(self, client):
        """Unknown routes return 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Wrong HTTP method returns 405."""
        response = client.get("/recommend")
        assert response.status_code == 405

    def test_response_has_timing_header(self, client):
        """Responses include the X-Response-Time-Ms header."""
        response = client.get("/health")
        header_value = response.headers.get("x-response-time-ms")
        assert header_value is not None, (
            f"Expected 'x-response-time-ms' header. "
            f"Got headers: {dict(response.headers)}"
        )

    def test_cors_headers_present(self, client):
        """CORS headers are present in responses."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" in response.headers


# ═══════════════════════════════════════════════════════════════════════
# POST /recommend — Edge Cases
# ═══════════════════════════════════════════════════════════════════════


class TestRecommendEdgeCases:
    """Edge case tests for the recommendation endpoint."""

    def test_empty_body(self, client):
        """Empty body returns 422."""
        response = client.post("/recommend", json={})
        assert response.status_code == 422

    def test_additional_preferences_max_length(self, client):
        """Additional preferences exceeding max length are rejected."""
        long_text = "a" * 501
        response = client.post(
            "/recommend",
            json={
                "location": "Koramangala",
                "budget": "medium",
                "additional_preferences": long_text,
            },
        )
        assert response.status_code == 422

    @patch("src.api.routes.call_llm")
    def test_recommend_empty_cuisine_string(self, mock_call_llm, client):
        """Empty string cuisine is treated as None (no cuisine filter)."""
        mock_call_llm.return_value = []

        response = client.post(
            "/recommend",
            json={
                "location": "Koramangala",
                "budget": "medium",
                "cuisine": "",
            },
        )
        # Empty string for an Optional[str] may pass validation but
        # should be handled gracefully
        assert response.status_code in (200, 422)
