import scrapy
from scrapy.http import FormRequest
from datetime import datetime, timedelta
import base64
import time
import requests


XEvil_CONFIG = {
    "baseUrl": "http://98.70.40.179/",
    "key": "anykey",  
    "initialDelay": 5,
    "interval": 5,
    "retries": 6
}


class BombayJudgmentSpider(scrapy.Spider):
    name = "bombay_judgments"
    allowed_domains = ["bombayhighcourt.nic.in"]
    start_urls = ["https://bombayhighcourt.nic.in/ord_qryrepact.php"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "RETRY_TIMES": 3,
        "ROBOTSTXT_OBEY": False,
        "FEEDS": {
            "bombay_judgments.csv": {"format": "csv", "overwrite": True},
        },
    }

    def start_requests(self):
        today = datetime.today()
        days_range = 1
        categories = ['C', 'CR', 'OS', 'NC', 'NR', 'AC', 'AR', 'GC', 'GR']

        for bench in categories:
            for day_offset in range(days_range):
                target_date = today - timedelta(days=day_offset)
                date_str = target_date.strftime("%d-%m-%Y")

                yield scrapy.Request(
                    url=self.start_urls[0],
                    callback=self.parse_main,
                    meta={
                        "m_sideflg": bench,
                        "frmdate": date_str,
                        "todate": date_str,
                        "pageno": 1
                    },
                    dont_filter=True
                )

    def parse_main(self, response):
        csrf_name = response.xpath('//input[@name="CSRFName"]/@value').get()
        csrf_token = response.xpath('//input[@name="CSRFToken"]/@value').get()
        captcha_url = response.urljoin(response.xpath('//img[@id="captchaimg"]/@src').get())

        yield scrapy.Request(
            url=captcha_url,
            callback=self.solve_and_submit,
            meta=response.meta | {
                "csrf_name": csrf_name,
                "csrf_token": csrf_token,
            },
            dont_filter=True
        )

    def solve_and_submit(self, response):
        captcha_bytes = response.body
        base64_image = base64.b64encode(captcha_bytes).decode('utf-8')

        # Send CAPTCHA to XEvil API
        try:
            submit = requests.post(
                XEvil_CONFIG["baseUrl"] + "in.php",
                data={
                    "key": XEvil_CONFIG["key"],
                    "method": "base64",
                    "body": base64_image
                }
            )

            if "OK|" not in submit.text:
                self.logger.warning("Failed to submit CAPTCHA to XEvil")
                return

            captcha_id = submit.text.split("|")[1]
            time.sleep(XEvil_CONFIG["initialDelay"])

            # Poll for solved CAPTCHA
            captcha_text = None
            for _ in range(XEvil_CONFIG["retries"]):
                poll = requests.get(
                    XEvil_CONFIG["baseUrl"] + "res.php",
                    params={
                        "key": XEvil_CONFIG["key"],
                        "action": "get",
                        "id": captcha_id
                    }
                )
                if "OK|" in poll.text:
                    captcha_text = poll.text.split("|")[1]
                    break
                time.sleep(XEvil_CONFIG["interval"])

            if not captcha_text:
                self.logger.warning("CAPTCHA solving timed out.")
                return

        except Exception as e:
            self.logger.error(f"CAPTCHA solving failed: {str(e)}")
            return

        formdata = {
            "CSRFName": response.meta["csrf_name"],
            "CSRFToken": response.meta["csrf_token"],
            "pageno": str(response.meta["pageno"]),
            "frmaction": "",
            "m_sideflg": response.meta["m_sideflg"],
            "actcode": "0",
            "frmdate": response.meta["frmdate"],
            "todate": response.meta["todate"],
            "captchaflg": "",
            "captcha_code": captcha_text,
            "submit1": "Submit"
        }

        yield FormRequest(
            url=self.start_urls[0],
            formdata=formdata,
            callback=self.parse_results,
            meta=response.meta,
            dont_filter=True
        )

    def parse_results(self, response):
        rows = response.xpath('//div[@class="table-responsive"]//tr[position()>1]')
        if not rows:
            return

        for row in rows:
            coram = row.xpath('./td[1]//text()').get(default='').strip()
            party = row.xpath('./td[2]//text()').get(default='').strip()
            judgement_info = row.xpath('./td[3]//text()').get(default='').strip()
            pdf_link = row.xpath('./td[4]//a/@href').get()
            if pdf_link:
                pdf_link = response.urljoin(pdf_link)

            yield {
                "coram": coram,
                "party": party,
                "judgement_info": judgement_info,
                "pdf_link": pdf_link,
                "bench_code": response.meta["m_sideflg"],
                "date": response.meta["frmdate"],
                "page": response.meta["pageno"]
            }

        # Pagination
        next_page = response.meta["pageno"] + 1
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_main,
            meta=response.meta | {"pageno": next_page},
            dont_filter=True
        )