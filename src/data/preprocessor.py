"""
preprocessor.py — Data cleaning & normalization.

Takes the raw Pandas DataFrame from the loader and produces a clean,
typed, indexed DataFrame ready for the filter engine.

Processing pipeline (mirrors architecture.md § 3.1):
  Raw Download → Parse & Validate → Normalize Fields
  → Handle Missing Values → Index by Location & Cuisine → Data Store
"""

import logging
import re
from typing import Dict, List, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column mapping ────────────────────────────────────────────────────
# Maps raw HuggingFace column names → clean internal names.
RAW_TO_CLEAN: Dict[str, str] = {
    "name": "name",
    "url": "url",
    "address": "address",
    "location": "location",
    "listed_in(city)": "city",
    "cuisines": "cuisines",
    "approx_cost(for two people)": "average_cost",
    "rate": "rating",
    "votes": "votes",
    "online_order": "online_order",
    "book_table": "book_table",
    "rest_type": "rest_type",
    "dish_liked": "dish_liked",
    "menu_item": "menu_item",
    "listed_in(type)": "listed_in_type",
}

# Columns that must exist in the raw dataset for processing to proceed.
REQUIRED_RAW_COLUMNS: List[str] = ["name", "location", "rate"]


def validate_schema(df: pd.DataFrame) -> None:
    """
    Verify that the raw DataFrame contains the minimum required columns.

    Raises:
        ValueError: If any required column is missing.
    """
    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Dataset schema validation failed. Missing columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )
    logger.info("Schema validation passed. Found %d columns.", len(df.columns))


def _parse_rating(value) -> float:
    """
    Convert a rating value to float.

    The raw dataset stores ratings as strings like '4.1/5', 'NEW',
    '-', or NaN.  This function extracts the numeric portion and
    clamps it to [0.0, 5.0].
    """
    if pd.isna(value):
        return 0.0

    value_str = str(value).strip()

    # Handle known non-numeric placeholders
    if value_str.lower() in ("new", "-", "", "nan", "none"):
        return 0.0

    # Extract the numeric part (e.g., "4.1/5" → "4.1")
    match = re.match(r"([0-9]*\.?[0-9]+)", value_str)
    if match:
        rating = float(match.group(1))
        # Clamp to [0.0, 5.0]
        return max(0.0, min(5.0, rating))

    return 0.0


def _parse_cost(value) -> float:
    """
    Convert a cost string to float.

    Handles values like '800', '1,200', 'N/A', NaN, etc.
    Returns 0.0 for unparseable values.
    """
    if pd.isna(value):
        return 0.0

    value_str = str(value).strip().replace(",", "")

    # Remove currency symbols if present
    value_str = re.sub(r"[₹$€£]", "", value_str).strip()

    try:
        cost = float(value_str)
        return max(0.0, cost)  # Discard negative values
    except (ValueError, TypeError):
        return 0.0


def _parse_bool(value) -> bool:
    """
    Convert a 'Yes'/'No' string (or similar) to a Python bool.
    """
    if pd.isna(value):
        return False
    return str(value).strip().lower() in ("yes", "true", "1")


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize the raw dataset.

    Steps:
      1. Validate schema
      2. Rename columns to clean internal names
      3. Normalize field types (rating, cost, booleans)
      4. Handle missing values
      5. Deduplicate
      6. Reset index

    Args:
        df: Raw DataFrame from the loader.

    Returns:
        Cleaned DataFrame ready for the filter engine.
    """
    logger.info("Starting preprocessing on %d rows …", len(df))

    # ── 1. Schema validation ──────────────────────────────────────────
    validate_schema(df)

    # ── 2. Rename columns ────────────────────────────────────────────
    # Only rename columns that exist in the raw data
    rename_map = {k: v for k, v in RAW_TO_CLEAN.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Keep only the columns we care about
    keep_cols = [v for v in RAW_TO_CLEAN.values() if v in df.columns]
    df = df[keep_cols].copy()

    # ── 3. Normalize types ───────────────────────────────────────────

    # Rating: "4.1/5" → 4.1
    if "rating" in df.columns:
        df["rating"] = df["rating"].apply(_parse_rating)

    # Cost: "1,200" → 1200.0
    if "average_cost" in df.columns:
        df["average_cost"] = df["average_cost"].apply(_parse_cost)
    else:
        df["average_cost"] = 0.0

    # Votes: ensure int
    if "votes" in df.columns:
        df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    else:
        df["votes"] = 0

    # Booleans
    for bool_col in ("online_order", "book_table"):
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].apply(_parse_bool)
        else:
            df[bool_col] = False

    # ── 4. Handle missing / empty values ─────────────────────────────

    # Drop rows with no name or no location — these are unusable
    before = len(df)
    df = df.dropna(subset=["name", "location"])
    df = df[df["name"].str.strip().astype(bool)]
    df = df[df["location"].str.strip().astype(bool)]
    dropped = before - len(df)
    if dropped > 0:
        logger.info("Dropped %d rows with missing name/location.", dropped)

    # Fill remaining string NaNs with empty strings
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].fillna("")

    # Trim whitespace from all string columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()

    # Normalize cuisines: trim each cuisine in comma-separated list
    if "cuisines" in df.columns:
        df["cuisines"] = df["cuisines"].apply(
            lambda x: ", ".join(c.strip() for c in str(x).split(",") if c.strip())
        )

    # ── 5. Deduplicate ───────────────────────────────────────────────
    # Keep the entry with the most votes for duplicate name+location pairs
    before = len(df)
    df = df.sort_values("votes", ascending=False).drop_duplicates(
        subset=["name", "location"], keep="first"
    )
    dupes_removed = before - len(df)
    if dupes_removed > 0:
        logger.info("Removed %d duplicate entries.", dupes_removed)

    # ── 6. Reset index ───────────────────────────────────────────────
    df = df.reset_index(drop=True)

    logger.info(
        "Preprocessing complete: %d clean rows × %d columns.",
        len(df),
        len(df.columns),
    )

    return df


def build_indices(df: pd.DataFrame) -> Dict[str, object]:
    """
    Build lookup indices for fast filtering.

    Returns a dictionary with:
        - "locations":       Sorted list of unique location strings.
        - "cuisines":        Sorted list of unique individual cuisine types.
        - "location_index":  Dict mapping location → list of DataFrame row indices.
        - "cuisine_index":   Dict mapping cuisine → set of DataFrame row indices.

    Args:
        df: The preprocessed DataFrame.

    Returns:
        Dictionary of indices.
    """
    # Unique locations
    locations: List[str] = sorted(df["location"].unique().tolist())

    # Unique individual cuisines (split from comma-separated strings)
    all_cuisines: Set[str] = set()
    for cuisine_str in df["cuisines"]:
        for c in str(cuisine_str).split(","):
            c = c.strip()
            if c:
                all_cuisines.add(c)
    cuisines: List[str] = sorted(all_cuisines)

    # Location → row indices
    location_index: Dict[str, List[int]] = {}
    for idx, loc in df["location"].items():
        location_index.setdefault(loc, []).append(idx)

    # Cuisine → row indices (a restaurant can appear under multiple cuisines)
    cuisine_index: Dict[str, Set[int]] = {}
    for idx, cuisine_str in df["cuisines"].items():
        for c in str(cuisine_str).split(","):
            c = c.strip()
            if c:
                cuisine_index.setdefault(c, set()).add(idx)

    logger.info(
        "Indices built: %d locations, %d cuisine types.",
        len(locations),
        len(cuisines),
    )

    return {
        "locations": locations,
        "cuisines": cuisines,
        "location_index": location_index,
        "cuisine_index": cuisine_index,
    }
