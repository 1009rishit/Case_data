# Unified Judgments Scraper

This project is a unified Scrapy-based web crawler that integrates multiple court data scrapers:
- Punjab & Haryana High Court case crawler
- Delhi High Court judgments scraper

It supports full crawling, form submission, CAPTCHA solving, pagination, PDF link extraction, and exporting results to CSV/Excel.


## 📁 Project Structure

unified_scraper/
├── scrapy.cfg
├── requirements.txt
├── README.md
├── crawl.log
├── 2025
└── unified_scraper/
    ├── init.py
    ├── items.py
    ├── middlewares.py 
    ├── pipelines.py 
    ├── settings.py 
    └── spiders/
    |    ├── init.py
    |    ├── phhc_spider.py # Legacy PHHC spider (optional)
    |    ├── haryana_spider.py # Main PHHC spider (form-based)
    |    ├── delhi_spider.py # Delhi High Court spider with CSRF/
    |    └── parse_from_file.py # Spider to parse data from a local 
    ├── utils
        ├── captcha_resolver.py
        ├── pdf_downloader.py
        ├── upload_to_azure.py

## 📦 Requirements

Python 3.8+  
Install dependencies using:

```bash
pip install -r requirements.txt
requirements.txt

scrapy==2.13.3
pandas>=1.5.0
openpyxl>=3.1.0
beautifulsoup4
lxml
datetime
requests
hashlib
base64
logging



🕷️ Available Spiders

1. haryana_spider (PHHC Crawler – Recommended)
Crawls case data from Punjab & Haryana High Court for the last 60 days

Handles form submission, pagination, and case type filtering

Exports to haryana_result.csv
scrapy crawl hppc_case_form_dynamic -o haryana_result.csv


2. delhi_spider (Delhi High Court)
Scrapes Delhi High Court judgment listings for last 60 days

Handles CSRF tokens, session cookies, and numeric CAPTCHAs

Extracts case number, date, parties, and PDF/TXT download links
scrapy crawl delhi_spider -o delhi_result.csv

3. Link_to_pdf spider(general purpose spider)

Scrape all the link in the csv file just need to change the file path
scrapy crawl general



UTILS:-

1. captcha_resolver
general class to automate the captcha

2.pdf_downloader
if any csv file that contains the pdf link then directly call the function to download all pdf if no captcha is there

3.upload_to_azure
file to upload the pdf to the azure database

DATABASE
create_db- to create the db
high_court_database- to configure database
models.py- to define table 
insert_csv.py- to insert the csv file to the database

how to run- 
1. python create_b.py
2. python insert_csv.py 

⚙️ Customization
Date range / filtering:
Modify start_date, end_date, or form logic in newspider.py / judgment_spider.py

Export logic:
Modify pipelines.py to change output file paths, formats, or filters

Headers / proxies / CAPTCHA solving:
Configure in settings.py or middlewares.py