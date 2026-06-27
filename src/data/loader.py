"""
loader.py — Dataset download & ingestion from Hugging Face.

Downloads the Zomato restaurant dataset using the `datasets` library,
caches it locally after the first download, and returns it as a
Pandas DataFrame for downstream preprocessing.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# Local cache directory (inside the project root)
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".cache" / "datasets"


def load_dataset_from_hf(
    dataset_id: str = "ManikaSaini/zomato-restaurant-recommendation",
    split: str = "train",
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Download the Zomato dataset from Hugging Face and return as a DataFrame.

    On the first call the dataset is downloaded and cached locally.
    Subsequent calls load from the cache.

    Args:
        dataset_id: Hugging Face dataset identifier.
        split:      Dataset split to load (default: "train").
        cache_dir:  Directory to cache the downloaded dataset.
                    Defaults to ``<project_root>/.cache/datasets``.

    Returns:
        pd.DataFrame containing the raw dataset.

    Raises:
        ConnectionError: If Hugging Face is unreachable and no cache exists.
        ValueError:      If the downloaded dataset is empty (0 rows).
    """
    if cache_dir is None:
        cache_dir = _CACHE_DIR

    cache_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading dataset '%s' (split=%s) …", dataset_id, split)

    # Try downloading the CSV file directly from Hugging Face to optimize memory and speed
    direct_url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/zomato.csv"
    logger.info("Attempting direct CSV download from %s", direct_url)
    try:
        df = pd.read_csv(direct_url)
        logger.info("Direct CSV download successful.")
    except Exception as direct_exc:
        logger.warning(
            "Direct CSV download failed: %s. Falling back to 'datasets' library.", 
            direct_exc
        )
        try:
            # Fallback to datasets library
            from datasets import load_dataset as hf_load_dataset

            ds = hf_load_dataset(
                dataset_id,
                split=split,
                cache_dir=str(cache_dir),
                trust_remote_code=False,
            )
            df = ds.to_pandas()
        except Exception as exc:
            logger.error("Failed to load dataset from Hugging Face fallback: %s", exc)
            raise ConnectionError(
                f"Could not load dataset '{dataset_id}' from Hugging Face. "
                f"Check your internet connection or verify the dataset ID. "
                f"Original error: {exc}"
            ) from exc

    if df.empty:
        raise ValueError(
            f"Dataset '{dataset_id}' (split={split}) is empty (0 rows). "
            "Cannot proceed without restaurant data."
        )

    logger.info(
        "Dataset loaded successfully: %d rows × %d columns",
        len(df),
        len(df.columns),
    )
    logger.debug("Columns: %s", list(df.columns))

    return df
