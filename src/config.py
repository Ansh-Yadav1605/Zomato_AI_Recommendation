"""
config.py — Configuration & environment variables.

Loads settings from a .env file using python-dotenv and exposes
them via a Pydantic BaseSettings class for type-safe access.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root directory (two levels up from src/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    Attributes:
        GROQ_API_KEY:       API key for the Groq inference service.
        LLM_MODEL:          Model identifier to use with Groq (e.g., llama-3.3-70b-versatile).
        LLM_TEMPERATURE:    Sampling temperature for the LLM (0.0 = deterministic, 1.0 = creative).
        LLM_MAX_TOKENS:     Maximum tokens in the LLM response.
        LLM_TIMEOUT:        Request timeout in seconds for Groq API calls.
        LLM_MAX_RETRIES:    Maximum number of retry attempts for failed LLM requests.
        CACHE_TTL_SECONDS:  Time-to-live for cached LLM responses (in seconds).
        MAX_CANDIDATES:     Maximum number of candidate restaurants to send to the LLM.
        APP_HOST:           Host address for the FastAPI server.
        APP_PORT:           Port number for the FastAPI server.
        APP_DEBUG:          Enable debug mode (verbose logging, auto-reload).
        DATASET_ID:         Hugging Face dataset identifier.
    """

    # ── Groq / LLM Configuration ──────────────────────────────────────
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT: int = 30
    LLM_MAX_RETRIES: int = 3

    # ── Caching ───────────────────────────────────────────────────────
    CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # ── Filter Engine ─────────────────────────────────────────────────
    MAX_CANDIDATES: int = 20

    # ── Application Server ────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = int(os.environ.get("PORT", 8000))
    APP_DEBUG: bool = False

    # ── Dataset ───────────────────────────────────────────────────────
    DATASET_ID: str = "ManikaSaini/zomato-restaurant-recommendation"

    # ── Budget Mapping (₹ for two) ────────────────────────────────────
    BUDGET_RANGES: dict = {
        "low": (0, 500),
        "medium": (501, 1500),
        "high": (1501, float("inf")),
    }

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Singleton settings instance — import this wherever config is needed.
settings = Settings()
