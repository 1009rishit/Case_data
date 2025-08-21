import scrapy
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from unified_scraper.utils.captcha_resolver import XevilCaptchaSolver


class KarnatakaSpider(scrapy.Spider):
    name = "karnataka_spider"
    allowed_domains = ["hcservices.ecourts.gov.in"]
    start_urls = ["https://hcservices.ecourts.gov.in/hcservices/main.php"]

    custom_settings = {
        "FEEDS": {"results.csv": {"format": "csv"}}
    }

    # ✅ Karnataka High Court benches (fixed)
    benches = {
        "1": "Principal Bench at Bengaluru",
        "2": "Bench at Dharwad",
        "3": "Bench at Kalburagi"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solver = XevilCaptchaSolver()
        self.logger.setLevel(logging.INFO)

        today = datetime.today()
        self.from_date = (today - timedelta(days=1)).strftime("%d-%m-%Y")
        self.to_date = today.strftime("%d-%m-%Y")

        # Karnataka codes
        self.state_code = "3"
        self.court_code = "3"   # Karnataka HC main code

    def parse(self, response):
        """Step 1: Iterate only Karnataka benches directly."""
        for bench_code, bench_name in self.benches.items():
            self.logger.info(f"🔹 Selected Bench: {bench_name} ({bench_code})")

            # Load the order date search page where captcha is shown
            yield scrapy.Request(
                url="https://hcservices.ecourts.gov.in/hcservices/main.php",
                callback=self.parse_orderdate_captcha,
                meta={
                    "cookiejar": response.meta.get("cookiejar"),
                    "bench_code": bench_code,
                    "bench_name": bench_name
                }
            )

    def parse_orderdate_captcha(self, response):
        """Step 2: Fetch the captcha from Order Date search page."""
        captcha_src = response.css("#captcha_image::attr(src)").get()
        if not captcha_src:
            self.logger.error(f"No captcha image for bench {response.meta['bench_name']}")
            return

        captcha_url = response.urljoin(captcha_src)
        yield scrapy.Request(
            captcha_url,
            callback=self.solve_captcha,
            meta=response.meta
        )

    def solve_captcha(self, response):
        """Step 3: Solve captcha and submit search form."""
        captcha_text = self.solver.solve(response.body)
        if not captcha_text:
            self.logger.error(f"[{response.meta['bench_name']}] Captcha solving failed")
            return

        self.logger.info(f"[{response.meta['bench_name']}] ✅ Solved Captcha: {captcha_text}")

        bench_code = response.meta["bench_code"]

        formdata = {
            "action_code": "getCOJudgement",   # 🔑 Required for results
            "court_code": self.court_code,
            "state_code": self.state_code,
            "court_complex_code": bench_code,
            "caseStatusSearchType": "COorderDate",
            "from_date": self.from_date,
            "to_date": self.to_date,
            "captcha": captcha_text,
            "appFlag": "web",
        }

        headers = {
            "user-agent": "Mozilla/5.0",
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
            meta=response.meta
        )

    def parse_results(self, response):
        """Step 4: Parse the search results table."""
        text = response.text
        bench_name = response.meta["bench_name"]

        if "invalid captcha" in text.lower():
            self.logger.error(f"[{bench_name}] ❌ Invalid captcha — retry needed")
            return

        try:
            if response.headers.get("Content-Type", b"").startswith(b"application/json"):
                data = response.json()
                rows_html = data.get("data", "")
                soup = BeautifulSoup(rows_html, "html.parser")
            else:
                soup = BeautifulSoup(text, "html.parser")

            rows = soup.select("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 3:
                    continue

                case_no = cols[1].get_text(strip=True)
                order_date = cols[2].get_text(strip=True)

                link = cols[3].find("a", href=True) if len(cols) > 3 else None
                pdf_link = response.urljoin(link["href"]) if link else None

                yield {
                    "bench": bench_name,
                    "case_no": case_no,
                    "date": order_date,
                    "document_link": pdf_link
                }

        except Exception as e:
            self.logger.error(f"[{bench_name}] Failed to parse results: {e}")
