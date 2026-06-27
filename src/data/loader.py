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

from src.data.preprocessor import RAW_TO_CLEAN

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

    # Clean subset of columns to load (excludes heavy unused fields like reviews_list)
    cols_to_load = list(RAW_TO_CLEAN.keys())

    # 1. Try downloading pre-converted parquet files from Hugging Face (highly optimized for speed and memory)
    try:
        import requests
        
        parquet_api_url = f"https://huggingface.co/api/datasets/{dataset_id}/parquet"
        logger.info("Attempting to query Hugging Face Parquet API: %s", parquet_api_url)
        resp = requests.get(parquet_api_url, timeout=10)
        if resp.status_code == 200:
            parquet_data = resp.json()
            train_urls = []
            for config, splits in parquet_data.items():
                if split in splits:
                    train_urls = splits[split]
                    break
            
            if train_urls:
                logger.info("Found %d parquet chunks. Downloading, filtering columns, and merging...", len(train_urls))
                # Only load required columns from Parquet files to prevent OOM memory spikes
                dfs = [pd.read_parquet(url, columns=cols_to_load) for url in train_urls]
                df = pd.concat(dfs, ignore_index=True)
                logger.info("Direct Parquet load successful.")
                return df
            else:
                logger.warning("No Parquet files found for split '%s' in metadata.", split)
        else:
            logger.warning("Hugging Face Parquet API returned status: %d", resp.status_code)
    except Exception as parquet_exc:
        logger.warning("Direct Parquet load failed: %s. Trying direct CSV...", parquet_exc)

    # 2. Try downloading the CSV file directly from Hugging Face to optimize memory and speed
    direct_url = f"https://huggingface.co/datasets/{dataset_id}/resolve/main/zomato.csv"
    logger.info("Attempting direct CSV download from %s", direct_url)
    try:
        # Only parse the required columns to save memory and time
        df = pd.read_csv(direct_url, usecols=cols_to_load)
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
