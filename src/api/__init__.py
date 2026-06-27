# API route definitions
"""
src.api — REST API layer.

Public API:
    router — FastAPI APIRouter with all endpoint definitions.
"""

from src.api.routes import router

__all__ = ["router"]
