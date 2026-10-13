"""
Responsible itch.io Top Sellers scraper for DSC2107 Group 8.

This script requests public HTML pages only. It does not log in, bypass access
controls, solve CAPTCHAs, or call undocumented/private endpoints.

Before a full run:
1. Read the current robots.txt and the assignment instructions.
2. Run the reconnaissance notebook and verify the HTML selectors.
3. If access is denied, throttled, or challenged, stop and document it.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib.robotparser import RobotFileParser
from urllib3.util.retry import Retry

BASE_URL = "https://itch.io/games/top-sellers"
ROBOTS_URL = "https://itch.io/robots.txt"
CONTACT_EMAIL = "cherissaiteriteka32@gmail.com"
USER_AGENT = (
    "DSC2107-Group8-StudentResearch "
    f"(contact: {CONTACT_EMAIL})"
)
DEFAULT_DELAY_SECONDS = 3.0
DEFAULT_TARGET_ITEMS = 500
MAX_PAGES_DEFAULT = 30
OUTPUT_DIR = Path("data/raw")
LOG_DIR = Path("logs")


def build_session() -> requests.Session:
    """Create a session with a descriptive User-Agent and cautious retries."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.8",
    })
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        status=3,
        backoff_factor=2,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "collection.log", encoding="utf-8"),
        ],
    )


def check_robots(session: requests.Session, target_url: str = BASE_URL) -> bool:
    """Fetch and parse robots.txt; fail closed if it cannot be checked."""
    response = session.get(ROBOTS_URL, timeout=20)
    response.raise_for_status()
    parser = RobotFileParser()
    parser.set_url(ROBOTS_URL)
    parser.parse(response.text.splitlines())
    allowed = parser.can_fetch(USER_AGENT, target_url)
    logging.info("robots.txt checked. Target allowed for this User-Agent: %s", allowed)
    if not allowed:
        raise PermissionError(
            f"robots.txt does not allow this target for the configured User-Agent: {target_url}"
        )
    return True


def _first_text(node, selectors: list[str]) -> str | None:
    for selector in selectors:
        found = node.select_one(selector)
        if found:
            text = found.get_text(" ", strip=True)
            if text:
                return text
    return None


def _first_link(node, selectors: list[str]) -> tuple[str | None, str | None]:
    for selector in selectors:
        found = node.select_one(selector)
        if found and found.get("href"):
            return found.get_text(" ", strip=True) or None, found["href"]
    return None, None


def parse_game_cell(cell, page_url: str, rank: int, scraped_at: str) -> dict[str, Any] | None:
    """Extract fields from a likely listing card using tolerant selectors."""
    title, href = _first_link(cell, [
        "a.game_link", ".game_title a", ".title a", "a.title", "a[href*='/games/']"
    ])
    if not title:
        # Some card structures place the title in a heading link.
        title, href = _first_link(cell, ["h2 a", "h3 a", "h4 a"])
    if not title or not href:
        return None

    absolute_url = urljoin(page_url, href)
    parsed = urlparse(absolute_url)
    if parsed.netloc and not parsed.netloc.endswith("itch.io"):
        # Avoid accidentally recording unrelated links as product pages.
        return None

    developer, developer_href = _first_link(cell, [
        ".game_author a", ".author a", ".game_author", ".user_link", "a[href*='/profile/']"
    ])
    price_text = _first_text(cell, [
        ".price", ".game_price", ".price_value", ".buy_button", ".game_buy"
    ])
    genres = []
    for selector in [".game_genre", ".genre_tag", ".game_tags a", ".tags a", ".game_genre a"]:
        for tag in cell.select(selector):
            value = tag.get_text(" ", strip=True)
            if value and value not in genres:
                genres.append(value)

    # Capture visible labels as a fallback, but do not pretend unknown fields exist.
    if not price_text:
        visible = cell.get_text(" ", strip=True)
        match = re.search(r"(Free|Name your own price|[$€£]\s?[\d,.]+)", visible, re.I)
        if match:
            price_text = match.group(1)

    return {
        "scraped_at": scraped_at,
        "rank": rank,
        "title": title.strip(),
        "url": absolute_url,
        "developer": developer.strip() if developer else None,
        "developer_url": urljoin(page_url, developer_href) if developer_href else None,
        "price_text": price_text,
        "genres": genres,
        "source_page": page_url,
    }


def extract_listings(html: str, page_url: str, rank_start: int, scraped_at: str):
    soup = BeautifulSoup(html, "html.parser")
    cells = soup.select(".game_cell")
    if not cells:
        # Diagnostic fallback only; selectors must be confirmed in reconnaissance.
        cells = soup.select("[class*='game_cell']")
    records = []
    for offset, cell in enumerate(cells):
        item = parse_game_cell(cell, page_url, rank_start + offset, scraped_at)
        if item:
            records.append(item)

    next_url = None
    for link in soup.select("a[href]"):
        label = link.get_text(" ", strip=True).lower()
        classes = " ".join(link.get("class", [])).lower()
        aria = (link.get("aria-label") or "").lower()
        if "next" in label or "next" in classes or "next" in aria:
            candidate = urljoin(page_url, link["href"])
            if urlparse(candidate).netloc.endswith("itch.io"):
                next_url = candidate
                break
    return records, next_url, len(cells)


def scrape_top_sellers(
    target_items: int = DEFAULT_TARGET_ITEMS,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    max_pages: int = MAX_PAGES_DEFAULT,
    output_dir: str | Path = OUTPUT_DIR,
) -> list[dict[str, Any]]:
    """Scrape up to target_items, pausing between pages and saving raw files."""
    if target_items < 1:
        raise ValueError("target_items must be at least 1.")
    if delay_seconds < 2:
        raise ValueError("Use at least a 2-second delay between page requests.")

    configure_logging()
    session = build_session()
    check_robots(session, BASE_URL)

    now = datetime.now(timezone.utc)
    scraped_at = now.isoformat(timespec="seconds")
    page_url = BASE_URL
    records: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    page_count = 0

    while page_url and len(records) < target_items and page_count < max_pages:
        if page_count:
            time.sleep(delay_seconds)
        page_count += 1
        logging.info("Requesting page %s (%s/%s)", page_url, page_count, max_pages)

        try:
            response = session.get(page_url, timeout=25)
        except requests.RequestException as exc:
            logging.error("Network error; stopping rather than hammering the site: %s", exc)
            break

        if response.status_code in (401, 403, 429):
            logging.error(
                "Access denied or rate-limited (HTTP %s). Stop and document this response.",
                response.status_code,
            )
            break
        response.raise_for_status()

        page_records, next_url, found_cells = extract_listings(
            response.text, response.url, len(records) + 1, scraped_at
        )
        logging.info(
            "Page had %s possible cards and %s parsed listings.",
            found_cells, len(page_records)
        )
        if not page_records:
            logging.warning(
                "No listings parsed. Check the reconnaissance notebook and selectors; stopping."
            )
            break

        for record in page_records:
            if record["url"] in seen_urls:
                continue
            seen_urls.add(record["url"])
            record["rank"] = len(records) + 1
            records.append(record)
            if len(records) >= target_items:
                break

        if not next_url or next_url == page_url:
            logging.warning("No usable next-page link found; stopping pagination.")
            break
        page_url = next_url

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d")
    json_path = output_path / f"itchio_top_sellers_{stamp}.json"
    csv_path = output_path / f"itchio_top_sellers_{stamp}.csv"

    payload = {
        "project": "DSC2107 Group 8 - itch.io Top Sellers",
        "scraped_at": scraped_at,
        "target_items": target_items,
        "records_collected": len(records),
        "pages_requested": page_count,
        "source_url": BASE_URL,
        "user_agent": USER_AGENT,
        "records": records,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # CSV is a convenient representation; JSON above preserves list fields.
    import pandas as pd
    csv_df = pd.DataFrame(records)
    if "genres" in csv_df.columns:
        csv_df["genres"] = csv_df["genres"].apply(
            lambda values: " | ".join(values) if isinstance(values, list) else values
        )
    csv_df.to_csv(csv_path, index=False, encoding="utf-8")

    logging.info("Saved raw JSON: %s", json_path)
    logging.info("Saved raw CSV: %s", csv_path)
    logging.info("Collected %s unique listings.", len(records))
    return records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect public itch.io Top Sellers listings.")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_ITEMS)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT)
    args = parser.parse_args()
    scrape_top_sellers(args.target, args.delay, args.max_pages)
