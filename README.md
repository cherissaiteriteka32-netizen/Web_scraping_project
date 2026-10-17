# DSC2107 Group 8 — itch.io Top Sellers

## Project goal
Collect daily snapshots of publicly visible itch.io Top Sellers listings, clean the data, store products and observations in SQLite, and analyse the seven-day dataset.

**Important:** This project is a cautious starter implementation. Run reconnaissance first and confirm the actual page structure and pagination before collecting the full target. Websites can change. Never bypass access controls.

## Repository layout
- `requirements.txt` — Python dependencies for the scraper and notebooks.
- `data_mining.ipynb` — reconnaissance, robots.txt check, HTML inspection and a small test.
- `itchio_top_sellers_eight_charts.ipynb` — analysis of the raw daily snapshots; includes eight chart sections.
- `src/scraper.py` — public HTML scraper with pagination, polite delays, retries, logging and raw JSON/CSV output.
- `src/cleaning.py` — cleaning helpers, timestamps, ranks and numeric prices.
- `src/database.py` — SQLite schema and loading helpers for `products` and `observations`.
- `src/run_daily.py` — one daily scrape, clean, and database load.
- `data/raw/` — dated raw daily snapshots; preserve these unchanged as evidence.
- `data/processed/` — most recent cleaned CSV.
- `database/` — SQLite database.
- `logs/` — collection logs.
- `outputs/` — chart images, analysis copy, and other generated outputs.
- `reports/` — reconnaissance notes, collection log, and final report deliverables.

## 1. Set up in VS Code (Windows)
Open this folder in VS Code. In Terminal, run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m ipykernel install --user --name group8-itchio --display-name "Python (Group 8 itch.io)"
```

If PowerShell blocks activation, you can use the interpreter directly:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In VS Code, install/enable the Python and Jupyter extensions. Open `data_mining.ipynb`, choose the `Python (Group 8 itch.io)` kernel, and run the cells from top to bottom.

## 2. Reconnaissance before full scraping
1. Open `data_mining.ipynb`.
2. Run the robots.txt check and HTML inspection.
3. Verify that the page's visible listing cards and next-page link are being found.
4. Use your browser's Developer Tools → Network tab to check whether listing data is in the HTML or loaded separately. Do not use private/authenticated endpoints.
5. Fill in `reports/reconnaissance_notes.md` and export it to PDF for the one-page reconnaissance deliverable. Track each scheduled run in `reports/collection_log.md`.
6. If selectors return zero listings, do not run a full scrape. Update the selectors in `src/scraper.py` only after examining the live HTML.

## 3. Run a small test first
From the repository root:
```powershell
python -m src.scraper --target 100 --delay 3 --max-pages 5
```
Then inspect `data/raw/`. Note: `src` can be run as a package from the root; if your environment reports an import error, use `python src/scraper.py --target 100 --delay 3 --max-pages 5`.

Use the Day 3 sample run to verify at least 100 listings, readable game titles, rank, and timestamps before the official collection window. Record actual reconnaissance results in `reports/reconnaissance_notes.md`.

## 4. Daily collection
The marking brief schedules seven collection runs on assignment Days 4–10. Confirm the calendar dates with your lecturer; do not backdate a run or count a failed/undersized run as complete. If assignment Day 1 was October 15, then October 17 is the Day 3 sample and the official daily snapshots run October 18–24. Only start the seven-day collection after reconnaissance and the sample run are accepted:
```powershell
python src/run_daily.py --target 500 --delay 3 --max-pages 30
```
Run once per scheduled day, targeting 500 ranked listings. After saving the dated raw JSON/CSV files, the scraper commits only those two files and pushes the commit to the current branch on the `origin` GitHub remote. Git credentials and permission to push to that branch must be configured. If publishing fails, the raw files remain local and the command reports an error; push them before considering that day's GitHub backup complete. If the website blocks or rate-limits the scraper, stop and document the event rather than retrying aggressively. Run each day in the same repository so the SQLite database accumulates observations. The cleaned CSV is replaced each run; the raw daily files are the historical source of truth.

## 5. Analyse
Open `itchio_top_sellers_eight_charts.ipynb`, select the project kernel, and run cells from the top after collecting data. The notebook combines CSV snapshots in `data/raw/` when available and uses the cleaned CSV only as a fallback. Some requested analyses need fields the current scraper may not provide, such as original/list price or platform support; report those as data limitations instead of inferring them.

## 6. Export notebook to HTML/PDF
From the repository root:
```powershell
jupyter nbconvert --to html itchio_top_sellers_eight_charts.ipynb --output analysis.html --output-dir reports
jupyter nbconvert --to pdf itchio_top_sellers_eight_charts.ipynb --output analysis.pdf --output-dir reports
```
PDF export can require a LaTeX installation. If it fails, use VS Code/Jupyter's Export menu or submit HTML if the assignment permits it. The HTML file is an export, not a separate scraper.

## 7. Data integrity and interpretation
- Keep raw snapshots unchanged. Cleaned files are separate.
- `price_text` is retained because currencies and price formats may differ.
- `price_value` is a parsed numeric amount, not a currency-converted value. Do not compare different currencies as if they were the same.
- A Top Sellers rank is a ranking signal, not a direct count of units sold, revenue, or profit.
- If the collected dataset does not support a question (for example, discounts or platform support), say so and do not invent a result.
- Report actual run dates, actual row counts, missingness, and any blocked/failed collection days.

## Data dictionary
| Field | Meaning |
|---|---|
| `scraped_at` | UTC timestamp when a listing was collected |
| `rank` | Position in the collected listing sequence for that snapshot |
| `title` | Visible game/listing title |
| `url` | Canonical listing URL |
| `developer` | Visible developer/author text, if found |
| `developer_url` | Developer profile URL, if found |
| `price_text` | Original visible price string |
| `price_value` | Numeric amount parsed from price text; free is 0, unknown is missing |
| `genres` | Visible genre/tag text when available |
| `source_page` | Page from which the record was extracted |

