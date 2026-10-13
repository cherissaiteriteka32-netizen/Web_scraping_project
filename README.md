# Group 8 Web Scraping

This repository contains a Jupyter notebook for a group web-scraping and data-mining project. The notebook begins an exploration of itch.io's top-selling games page.

## Notebook

- `data_mining.ipynb` imports the scraping and data-analysis libraries, checks itch.io's `robots.txt`, and starts requesting the top-sellers page.

The notebook is a work in progress; run its cells in order and complete the analysis as the project develops.

## Setup

Use Python with Jupyter installed, then install the libraries imported by the notebook:

```bash
python -m pip install jupyter requests beautifulsoup4 pandas matplotlib wordcloud
```

Start Jupyter or open `data_mining.ipynb` in VS Code with the Jupyter extension and a Python environment that has those packages installed.

## Responsible scraping

Before scraping, review the target site's terms and `robots.txt`. Use reasonable request rates and avoid collecting data from disallowed paths.
