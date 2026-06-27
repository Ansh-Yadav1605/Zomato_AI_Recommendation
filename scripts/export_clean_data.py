"""Script to download, preprocess, and save a clean dataset CSV for Railway deployment."""
import requests
import io
import os
import pandas as pd
from src.data.preprocessor import RAW_TO_CLEAN, preprocess

cols = list(RAW_TO_CLEAN.keys())
headers = {"User-Agent": "Mozilla/5.0"}

# Download and parse
api_url = "https://huggingface.co/api/datasets/ManikaSaini/zomato-restaurant-recommendation/parquet"
resp = requests.get(api_url, headers=headers, timeout=10)
data = resp.json()
train_urls = []
for config, splits in data.items():
    if "train" in splits:
        train_urls = splits["train"]
        break

dfs = []
for url in train_urls:
    print(f"Downloading {url[-20:]}...")
    chunk_resp = requests.get(url, headers=headers, timeout=60)
    chunk_df = pd.read_parquet(io.BytesIO(chunk_resp.content), columns=cols)
    dfs.append(chunk_df)
    print(f"  Got {len(chunk_df)} rows")

raw_df = pd.concat(dfs, ignore_index=True)
print(f"Total raw: {len(raw_df)} rows")

# Preprocess
clean_df = preprocess(raw_df)
print(f"After preprocessing: {len(clean_df)} rows x {len(clean_df.columns)} cols")

# Blank out heavy unused fields to keep unit tests happy while shrinking file size to < 2.5MB
if "url" in clean_df.columns:
    clean_df["url"] = ""
if "menu_item" in clean_df.columns:
    clean_df["menu_item"] = ""

# Save to CSV
output_path = "data/restaurants_clean.csv"
os.makedirs("data", exist_ok=True)
clean_df.to_csv(output_path, index=False)
file_size = os.path.getsize(output_path) / 1024 / 1024
print(f"Saved to {output_path}: {file_size:.1f}MB")
print(f"Columns: {list(clean_df.columns)}")
locs = sorted(clean_df["location"].unique())
print(f"Sample locations ({len(locs)} total): {locs[:10]}")
