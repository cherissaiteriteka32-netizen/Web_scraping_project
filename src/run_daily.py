"""Run one daily collection, clean it, and load the relational database."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

from scraper import scrape_top_sellers
from cleaning import clean_dataframe
from database import load_dataframe, DEFAULT_DB


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=500)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--max-pages", type=int, default=30)
    args = parser.parse_args()

    raw_records = scrape_top_sellers(
        target_items=args.target,
        delay_seconds=args.delay,
        max_pages=args.max_pages,
    )
    if not raw_records:
        print("No records were collected. Review logs/collection.log and document the outcome.")
        return

    raw_df = pd.DataFrame(raw_records)
    cleaned_df = clean_dataframe(raw_df)
    output_path = Path("data/processed/cleaned_games.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(output_path, index=False, encoding="utf-8")
    loaded = load_dataframe(cleaned_df, DEFAULT_DB)
    print(f"Raw records: {len(raw_df)}")
    print(f"Clean records: {len(cleaned_df)}")
    print(f"Rows loaded/updated in SQLite: {loaded}")
    print(f"Clean CSV: {output_path}")
    print(f"Database: {DEFAULT_DB}")


if __name__ == "__main__":
    main()
