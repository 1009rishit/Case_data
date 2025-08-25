import scrapy
from datetime import datetime, timedelta
import logging
from unified_scraper.utils.captcha_resolver import XevilCaptchaSolver
import json
import urllib.parse
from scrapy.downloadermiddlewares.cookies import CookiesMiddleware

class KarnatakaSpider(scrapy.Spider):
    name = "karnataka_spider"
    allowed_domains = ["hcservices.ecourts.gov.in"]
    start_urls = ["https://hcservices.ecourts.gov.in/hcservices/main.php"]

    custom_settings = {
        "FEEDS": {
            "results.csv": {
                "format": "csv",
                "overwrite": True,   # ensures CSV is replaced, not appended
                "fields": ["bench", "case_no", "date", "document_link"],  # enforce columns
            }
        },
        "COOKIES_ENABLED": True,
    }

    benches = {
        "1": "Principal Bench at Bengaluru",
        "2": "Bench at Dharwad",
        "3": "Bench at Kalburagi",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solver = XevilCaptchaSolver()
        self.logger.setLevel(logging.INFO)

        today = datetime.today()
        self.from_date = (today - timedelta(days=3)).strftime("%d-%m-%Y")
        self.to_date = today.strftime("%d-%m-%Y")

        self.state_code = "3"  # Karnataka state code

    def parse(self, response):
        """Step 1: Request each bench (mimics fillHCBench call)."""
        for bench_code, bench_name in self.benches.items():
            payload = {
                "action_code": "fillHCBench",
                "state_code": self.state_code,
                "appFlag": "web",
            }

            yield scrapy.FormRequest(
                url="https://hcservices.ecourts.gov.in/hcservices/main.php",
                formdata=payload,
                callback=self.parse_bench_response,
                meta={
                    "cookiejar": bench_code,
                    "bench_code": bench_code,
                    "bench_name": bench_name,
                },
                dont_filter=True,
            )

    def parse_bench_response(self, response):
        """Step 2: Fetch captcha."""
        captcha_url = "https://hcservices.ecourts.gov.in/hcservices/securimage/securimage_show.php"
        yield scrapy.Request(
            captcha_url,
            callback=self.solve_captcha,
            meta=response.meta,
            dont_filter=True,
        )

    def solve_captcha(self, response):
        """Step 3: Solve captcha and submit search form with date range."""
        bench_name = response.meta["bench_name"]
        captcha_text = self.solver.solve(response.body)

        if not captcha_text:
            self.logger.error(f"[{bench_name}] Captcha solving failed")
            return

        self.logger.info(f"[{bench_name}] Captcha: {captcha_text}")

        bench_code = response.meta["bench_code"]

        formdata = {
            "court_code": bench_code,
            "state_code": self.state_code,
            "court_complex_code": bench_code,
            "caseStatusSearchType": "COorderDate",
            "from_date": self.from_date,
            "to_date": self.to_date,
            "captcha": captcha_text,
        }

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://hcservices.ecourts.gov.in",
            "Referer": "https://hcservices.ecourts.gov.in/hcservices/main.php",
        }

        yield scrapy.FormRequest(
            url="https://hcservices.ecourts.gov.in/hcservices/cases_qry/index_qry.php?action_code=showRecords",
            formdata=formdata,
            headers=headers,
            method="POST",
            callback=self.parse_results,
            meta=response.meta,
            dont_filter=True,
        )

    def build_valid_pdf_url(self, rec, bench_code):
        """Build valid PDF URL from record data."""
        base = "https://hcservices.ecourts.gov.in/hcservices/cases/display_pdf.php"

        filename_raw = urllib.parse.unquote(rec.get("orderurlpath", ""))
        filename_q = urllib.parse.quote(filename_raw, safe="")

        type_name = rec.get("type_name")
        reg_no = rec.get("reg_no") or rec.get("fil_no")
        reg_year = rec.get("reg_year") or rec.get("fil_year")

        if not (type_name and reg_no and reg_year):
            return None

        caseno = f"{type_name}/{int(reg_no)}/{int(reg_year)}"
        cino = rec.get("cino")

        params = [
            ("filename", filename_q),
            ("caseno", caseno),
            ("cCode", bench_code),
            ("appFlag", "web"),
            ("normal_v", "1"),
            ("cino", cino),
            ("state_code", self.state_code),
            ("flag", "nojudgement"),
        ]
        return f"{base}?{'&'.join([f'{k}={v}' for k, v in params if v])}"

    def parse_results(self, response):
        bench_name = response.meta["bench_name"]
        bench_code = response.meta["bench_code"]

        if "invalid captcha" in response.text.lower():
            self.logger.error(f"[{bench_name}] Invalid captcha")
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"[{bench_name}] Not JSON response: {response.text[:200]}")
            return

        if not data.get("con"):
            self.logger.warning(f"[{bench_name}] No records found")
            return

        records = json.loads(data["con"][0])

        for rec in records:
            case_no = rec.get("case_no")
            order_date = rec.get("order_dt")

            pdf_link = None
            if rec.get("orderurlpath"):
                pdf_link = self.build_valid_pdf_url(rec, bench_code)

            yield {
                "bench": bench_name,
                "case_no": case_no or "",
                "date": order_date or "",
                "party":None,
                "pdf_link": pdf_link or "",
            }

    def closed(self, reason):
        """Save cookies to a file when spider finishes."""
        cookies = {}

        # find the cookies middleware object in the stack
        cookies_mw = None
        for mw in self.crawler.engine.downloader.middleware.middlewares:
            if isinstance(mw, CookiesMiddleware):
                cookies_mw = mw
                break

        if not cookies_mw:
            self.logger.error("❌ CookiesMiddleware not found")
            return

        # extract cookies per bench_code
        for bench_code in self.benches.keys():
            cj = cookies_mw.jars.get(str(bench_code))
            if cj:
                cookies[bench_code] = {c.name: c.value for c in cj}

        with open("cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        self.logger.info("✅ Cookies saved to cookies.json")