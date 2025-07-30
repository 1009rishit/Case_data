# Unified Judgments Scraper

This project is a unified Scrapy-based web crawler that integrates multiple court data scrapers:
- Punjab & Haryana High Court case crawler
- Delhi High Court judgments scraper
- A utility spider that parses data from a local file

It supports full crawling, form submission, CAPTCHA solving, pagination, PDF link extraction, and exporting results to CSV/Excel.

---

## 📁 Project Structure

unified_scraper/
├── scrapy.cfg
├── requirements.txt
├── README.md
└── unified_scraper/
├── init.py
├── items.py # Common item definitions (can be extended)
├── middlewares.py # Shared/custom middleware (if needed)
├── pipelines.py # Excel export pipeline
├── settings.py # Unified settings
└── spiders/
├── init.py
├── phhc_spider.py # Legacy PHHC spider (optional)
├── newspider.py # Main PHHC spider (form-based)
├── judgment_spider.py # Delhi High Court spider with CSRF/
└── parse_from_file.py # Spider to parse data from a local 

---

## 📦 Requirements

Python 3.8+  
Install dependencies using:

```bash
pip install -r requirements.txt
requirements.txt

scrapy
pandas
openpyxl
beautifulsoup4
lxml

🕷️ Available Spiders
1. newspider (PHHC Crawler – Recommended)
Crawls case data from Punjab & Haryana High Court for the last 60 days

Handles form submission, pagination, and case type filtering

Exports to results.xlsx and results.csv
scrapy crawl newspider

2. judgment_spider (Delhi High Court)
Scrapes Delhi High Court judgment listings

Handles CSRF tokens, session cookies, and numeric CAPTCHAs

Extracts case number, date, parties, and PDF/TXT download links
scrapy crawl delhi_spider


3. phhc_spider (Optional Legacy PHHC Spider)
Alternate or older spider for PHHC site (kept for fallback or reference)
scrapy crawl phhc_spider

4. parse_from_file (Offline Data Parser)
Parses judgments/case data from a local HTML or structured file

Useful for post-processing, testing, or archival data

scrapy crawl parse_from_file
📤 Output

PHHC spiders:

results.csv, results.xlsx (automatically saved using pipelines)

Delhi HC spider:

judgments.csv (you can also export JSON via -o judgments.json)

⚙️ Customization
Date range / filtering:
Modify start_date, end_date, or form logic in newspider.py / judgment_spider.py

Export logic:
Modify pipelines.py to change output file paths, formats, or filters

Headers / proxies / CAPTCHA solving:
Configure in settings.py or middlewares.py