"""Cleaning and standardisation helpers for the itch.io Group 8 project."""
from __future__ import annotations

import re
from pathlib import Path
import pandas as pd


def parse_price(price_text):
    """Return numeric price if a clear amount exists; otherwise None.

    Currency symbols are not converted. Store the original price_text as well.
    Free/name-your-own-price values are represented by 0 only when explicitly
    stated as Free; unknown and name-your-own-price remain missing.
    """
    if price_text is None or pd.isna(price_text):
        return None
    text = str(price_text).strip()
    if re.search(r"\bfree\b", text, re.I):
        return 0.0
    if re.search(r"name your own price|pay what you want", text, re.I):
        return None
    # Remove thousands separators and look for a numeric amount.
    match = re.search(r"(\d[\d,]*(?:\.\d{1,2})?)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean a raw dataframe while retaining original price text."""
    cleaned = df.copy()
    for column in ["title", "url", "developer", "price_text", "source_page"]:
        if column not in cleaned:
            cleaned[column] = pd.NA
        cleaned[column] = cleaned[column].astype("string").str.strip()
        cleaned[column] = cleaned[column].replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})

    if "scraped_at" not in cleaned:
        cleaned["scraped_at"] = pd.NaT
    cleaned["scraped_at"] = pd.to_datetime(cleaned["scraped_at"], errors="coerce", utc=True)

    if "rank" not in cleaned:
        cleaned["rank"] = pd.NA
    cleaned["rank"] = pd.to_numeric(cleaned["rank"], errors="coerce").astype("Int64")

    cleaned["price_value"] = cleaned["price_text"].apply(parse_price)
    cleaned["price_value"] = pd.to_numeric(cleaned["price_value"], errors="coerce")

    if "genres" not in cleaned:
        cleaned["genres"] = pd.NA
    cleaned["genres"] = cleaned["genres"].apply(
        lambda x: " | ".join(x) if isinstance(x, list) else x
    )
    cleaned["genres"] = cleaned["genres"].astype("string").str.strip()
    cleaned["genres"] = cleaned["genres"].replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})

    # A product can appear on several days; preserve each daily observation.
    cleaned = cleaned.dropna(subset=["url", "title"])
    cleaned = cleaned.drop_duplicates(subset=["url", "scraped_at"], keep="last")
    return cleaned.reset_index(drop=True)


def clean_file(input_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.suffix.lower() == ".json":
        import json
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        records = payload.get("records", payload) if isinstance(payload, dict) else payload
        df = pd.DataFrame(records)
    else:
        df = pd.read_csv(input_path)
    cleaned = clean_dataframe(df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False, encoding="utf-8")
    return cleaned


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clean one raw daily CSV or JSON file.")
    parser.add_argument("input")
    parser.add_argument("--output", default="data/processed/cleaned_games.csv")
    args = parser.parse_args()
    result = clean_file(args.input, args.output)
    print(f"Saved {len(result)} cleaned rows to {args.output}")
