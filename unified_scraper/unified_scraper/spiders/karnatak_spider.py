import scrapy
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from unified_scraper.utils.captcha_resolver import XevilCaptchaSolver
import logging


class KarnatakaSpider(scrapy.Spider):
    name = "karnataka_spider"
    allowed_domains = ["hcservices.ecourts.gov.in"]
    start_urls = ["https://hcservices.ecourts.gov.in/hcservices/main.php"]

    custom_settings = {
        "FEEDS": {"results.csv": {"format": "csv"}}
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solver = XevilCaptchaSolver()
        self.logger.setLevel(logging.INFO)

        today = datetime.today()
        self.from_date = (today - timedelta(days=1)).strftime("%d-%m-%Y")
        self.to_date = today.strftime("%d-%m-%Y")

    def parse(self, response):
        """Initial request loads cookies + captcha image."""
        captcha_src = response.css("#captcha_image::attr(src)").get()
        if not captcha_src:
            self.logger.error("Captcha image not found on page")
            return

        captcha_url = response.urljoin(captcha_src)
        yield scrapy.Request(
            captcha_url,
            callback=self.parse_captcha,
            meta={"cookiejar": response.meta.get("cookiejar")}
        )

    def parse_captcha(self, response):
        """Download captcha and solve it."""
        captcha_text = self.solver.solve(response.body)
        if not captcha_text:
            self.logger.error("Captcha solving failed")
            return

        self.logger.info(f"Solved Captcha: {captcha_text}")

        # Karnataka High Court codes (extracted from manual inspection)
        formdata = {
            "court_code": "3",              # Karnataka HC
            "state_code": "3",
            "court_complex_code": "3",      # Bench code (Bengaluru)
            "caseStatusSearchType": "COorderDate",
            "from_date": self.from_date,
            "to_date": self.to_date,
            "captcha": captcha_text
        }

        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/138.0.0.0 Safari/537.36",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://hcservices.ecourts.gov.in",
            "referer": "https://hcservices.ecourts.gov.in/hcservices/main.php",
            "x-requested-with": "XMLHttpRequest",
        }

        yield scrapy.FormRequest(
            url="https://hcservices.ecourts.gov.in/hcservices/main.php",
            formdata=formdata,
            method="POST",
            headers=headers,
            callback=self.parse_results,
            meta={
                "cookiejar": response.meta.get("cookiejar"),
                "retry": 0  # Track retries for captcha
            }
        )

    def parse_results(self, response):
        """Parse the search results table."""
        text = response.text
        if "invalid captcha" in text.lower():
            retry = response.meta.get("retry", 0)
            if retry < 3:
                self.logger.warning(f"Invalid captcha, retrying... attempt {retry+1}")
                # Retry by fetching a new captcha
                yield scrapy.Request(
                    self.start_urls[0],
                    callback=self.parse,
                    dont_filter=True,
                    meta={"cookiejar": response.meta.get("cookiejar"), "retry": retry + 1}
                )
            else:
                self.logger.error("Max captcha retries reached")
            return

        try:
            # sometimes JSON, sometimes HTML — check both
            if response.headers.get("Content-Type", b"").startswith(b"application/json"):
                data = response.json()
                rows_html = data.get("data", "")
                soup = BeautifulSoup(rows_html, "html.parser")
            else:
                soup = BeautifulSoup(text, "html.parser")

            rows = soup.select("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue

                item = {
                    "case_no": cols[0].get_text(strip=True),
                    "party": cols[1].get_text(strip=True),
                    "date": cols[2].get_text(strip=True),
                    "status": cols[3].get_text(strip=True),
                }

                # If a PDF/document link exists, capture it
                link = row.find("a", href=True)
                if link:
                    item["document_link"] = response.urljoin(link["href"])

                yield item

        except Exception as e:
            self.logger.error(f"Failed to parse results: {e}")
