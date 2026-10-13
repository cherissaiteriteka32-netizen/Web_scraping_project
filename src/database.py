"""SQLite database schema and load functions for the Group 8 project."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd

DEFAULT_DB = Path("database/itchio_top_sellers.db")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    developer TEXT,
    developer_url TEXT
);
CREATE TABLE IF NOT EXISTS observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    scraped_at TEXT NOT NULL,
    rank INTEGER,
    price_text TEXT,
    price_value REAL,
    genres TEXT,
    source_page TEXT,
    FOREIGN KEY(product_id) REFERENCES products(product_id),
    UNIQUE(product_id, scraped_at)
);
CREATE INDEX IF NOT EXISTS idx_observations_scraped_at ON observations(scraped_at);
CREATE INDEX IF NOT EXISTS idx_observations_rank ON observations(rank);
"""


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def load_dataframe(df: pd.DataFrame, db_path: str | Path = DEFAULT_DB) -> int:
    """Upsert products and daily observations. Returns rows attempted."""
    if df.empty:
        return 0
    conn = connect(db_path)
    count = 0
    try:
        for row in df.to_dict(orient="records"):
            url = row.get("url")
            title = row.get("title")
            if not url or not title:
                continue
            conn.execute(
                """INSERT INTO products(url, title, developer, developer_url)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(url) DO UPDATE SET
                     title=excluded.title,
                     developer=COALESCE(excluded.developer, products.developer),
                     developer_url=COALESCE(excluded.developer_url, products.developer_url)""",
                (str(url), str(title), _nullable(row.get("developer")), _nullable(row.get("developer_url"))),
            )
            product_id = conn.execute(
                "SELECT product_id FROM products WHERE url = ?", (str(url),)
            ).fetchone()[0]
            scraped_at = row.get("scraped_at")
            if pd.isna(scraped_at):
                scraped_at = None
            elif hasattr(scraped_at, "isoformat"):
                scraped_at = scraped_at.isoformat()
            if not scraped_at:
                continue
            rank = _nullable(row.get("rank"))
            price_value = _nullable(row.get("price_value"))
            conn.execute(
                """INSERT INTO observations
                   (product_id, scraped_at, rank, price_text, price_value, genres, source_page)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(product_id, scraped_at) DO UPDATE SET
                     rank=excluded.rank, price_text=excluded.price_text,
                     price_value=excluded.price_value, genres=excluded.genres,
                     source_page=excluded.source_page""",
                (
                    product_id, str(scraped_at), rank,
                    _nullable(row.get("price_text")), price_value,
                    _nullable(row.get("genres")), _nullable(row.get("source_page")),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def _nullable(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            pass
    return value


def read_observations(db_path: str | Path = DEFAULT_DB) -> pd.DataFrame:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}. Run a collection and load it first.")
    with sqlite3.connect(path) as conn:
        return pd.read_sql_query(
            """SELECT p.product_id, p.url, p.title, p.developer, p.developer_url,
                      o.scraped_at, o.rank, o.price_text, o.price_value, o.genres, o.source_page
               FROM products p JOIN observations o ON p.product_id = o.product_id
               ORDER BY o.scraped_at, o.rank""",
            conn,
        )


if __name__ == "__main__":
    print(f"Database schema is ready at {DEFAULT_DB}")
