BOT_NAME = "unified_scraper"

SPIDER_MODULES = ["unified_scraper.spiders"]
NEWSPIDER_MODULE = "unified_scraper.spiders"

# GENERAL CRAWLING SETTINGS
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 150
CONCURRENT_REQUESTS_PER_DOMAIN = 75
DOWNLOAD_DELAY = 0.1

# HEADERS
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1)",
}

# AUTO THROTTLING
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 10.0
AUTOTHROTTLE_DEBUG = False

# ITEM PIPELINES
ITEM_PIPELINES = {
    "unified_scraper.pipelines.ExcelExportPipeline": 300,
    # Add more pipelines as needed
}

# MIDDLEWARES (Uncomment if needed)
# SPIDER_MIDDLEWARES = {
#     "unified_scraper.middlewares.UnifiedSpiderMiddleware": 543,
# }

# DOWNLOADER_MIDDLEWARES = {
#     "unified_scraper.middlewares.UnifiedDownloaderMiddleware": 543,
# }

# FEEDS (Generic — override per spider at runtime if needed)
FEEDS = {
    'results.csv': {
        'format': 'csv',
        'encoding': 'utf8',
        'overwrite': True,
    }
}

# LOGGING
LOG_FILE = "crawl.log"
LOG_LEVEL = "INFO"

# ENCODING
FEED_EXPORT_ENCODING = "utf-8"
