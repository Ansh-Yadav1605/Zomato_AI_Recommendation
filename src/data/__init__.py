# Data ingestion and preprocessing
"""
src.data — Dataset loading, cleaning, and indexing.

Public API:
    load_dataset_from_hf  — Download the Zomato dataset from Hugging Face.
    preprocess            — Clean and normalize the raw DataFrame.
    build_indices         — Build location/cuisine lookup indices.
    validate_schema       — Check that required columns exist.
"""

from src.data.loader import load_dataset_from_hf
from src.data.preprocessor import build_indices, preprocess, validate_schema

__all__ = [
    "load_dataset_from_hf",
    "preprocess",
    "build_indices",
    "validate_schema",
]
