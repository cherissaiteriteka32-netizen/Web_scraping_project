"""Day 1 warm-up: scrape Books to Scrape pagination and detail pages.

Install dependencies: pip install requests beautifulsoup4 pandas
Run: python warmup_books.py
"""
import csv
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

# Starting page and identity for the course project.
START_URL = "https://books.toscrape.com/"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
USER_AGENT = "DSC2107-Group8-Warmup (wmubs4@gmail.com)"
OUT = Path(__file__).resolve().parent / "data" / "raw" / "books_warmup.csv"
MIN_DELAY, MAX_DELAY = 2, 5

# Keep a readable record of each page visited and any errors.
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def fetch(url):
    """Fetch a page after a respectful delay and parse its HTML."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    response = session.get(url, timeout=20)
    # Do not try to bypass a block or CAPTCHA; fail visibly instead.
    if response.status_code in (401, 403, 429):
        raise RuntimeError(f"HTTP {response.status_code}; stop and document the block.")
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")


def main():
    """Follow listing-page pagination, then visit each book's detail page."""
    # Check robots.txt before requesting any catalog page.
    robots_response = session.get(ROBOTS_URL, timeout=20)
    robots_response.raise_for_status()
    robots = RobotFileParser()
    robots.parse(robots_response.text.splitlines())
    if not robots.can_fetch(USER_AGENT, START_URL):
        raise RuntimeError("robots.txt does not allow the starting page; stopping.")

    rows, listing_url = [], START_URL
    seen = set()
    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Continue until the site has no next page. This is pagination handling.
    while listing_url:
        logging.info("Listing page: %s", listing_url)
        listing_soup = fetch(listing_url)
        # Each article.product_pod represents one book card on the listing page.
        for card in listing_soup.select("article.product_pod"):
            link = card.select_one("h3 a")
            if not link:
                continue
            detail_url = urljoin(listing_url, link.get("href", ""))
            if detail_url in seen:
                continue
            seen.add(detail_url)

            # Some fields are available immediately on the listing card.
            title = link.get("title") or link.get_text(strip=True)
            price_node = card.select_one(".price_color")
            availability_node = card.select_one(".availability")
            rating_node = card.select_one(".star-rating")
            listing_price = price_node.get_text(strip=True) if price_node else None
            listing_availability = availability_node.get_text(" ", strip=True) if availability_node else None
            listing_rating = next((c for c in (rating_node.get("class", []) if rating_node else []) if c != "star-rating"), None)

            # Open the individual detail page to collect information not on the card.
            detail_soup = fetch(detail_url)
            product_table = {}
            for tr in detail_soup.select("table.table-striped tr"):
                th, td = tr.select_one("th"), tr.select_one("td")
                if th and td:
                    product_table[th.get_text(strip=True)] = td.get_text(" ", strip=True)
            description = detail_soup.select_one("#product_description + p")

            rows.append({
                "title": title,
                "price": listing_price,
                "availability": listing_availability,
                "rating": listing_rating,
                "detail_url": detail_url,
                "upc": product_table.get("UPC"),
                "product_type": product_table.get("Product Type"),
                "tax": product_table.get("Tax"),
                "number_available": product_table.get("Availability"),
                "description": description.get_text(" ", strip=True) if description else None,
                "scraped_at": scraped_at,
            })

        # The 'next' anchor gives the next listing page; no link means end of pagination.
        next_link = listing_soup.select_one("li.next a")
        listing_url = urljoin(listing_url, next_link.get("href")) if next_link else None

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Save the complete warm-up output to CSV for inspection.
    with OUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    logging.info("Warm-up complete: %s books saved to %s", len(rows), OUT)


if __name__ == "__main__":
    main()
