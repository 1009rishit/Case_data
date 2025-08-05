import scrapy
from bs4 import BeautifulSoup
import re
import math
from datetime import datetime, timedelta

class DelhiJudgmentsSpider(scrapy.Spider):
    name = "delhi_spider"
    allowed_domains = ["delhihighcourt.nic.in"]
    start_urls = ["https://delhihighcourt.nic.in/app/judgement-dates-wise"]

    def parse(self, response):
        # Extract CSRF token
        token = response.css('input[name="_token"]::attr(value)').get()
        captcha = response.css('span#captcha-code::text').get()

        self.token = token
        self.captcha = captcha
        today = datetime.today()
        self.from_date = (today - timedelta(days=60)).strftime("%d-%m-%Y")
        self.to_date = today.strftime("%d-%m-%Y")

        # First page POST
        yield scrapy.FormRequest(
            url=self.start_urls[0],
            method="POST",
            formdata={
                "_token": token,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "randomid": captcha,
                "captchaInput": captcha,
                "page": "1"
            },
            callback=self.parse_results,
            meta={"page": 1}
        )

    def parse_results(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("#registrarsTableValue tr")[1:]  # skip header

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            case_no = cols[1].get_text(strip=True).replace('\xa0', ' ')
            date_tag = cols[2].find("a", href=True)
            date = date_tag.get_text(strip=True) if date_tag else ""
            link = date_tag["href"] if date_tag else ""
            if not link.startswith("http"):
                link = response.urljoin(link)

            party = cols[3].get_text(strip=True).replace('\xa0', ' ')

            yield {
                "case_no": case_no,
                "date": date,
                "party": party,
                "pdf_link": link
            }

        # ➕ Pagination logic
        text = soup.find("div", string=re.compile("Showing"))
        if text:
            match = re.search(r"Showing \d+ to \d+ of (\d+)", text.get_text())
            if match:
                total_records = int(match.group(1))
                per_page = 50
                total_pages = math.ceil(total_records / per_page)

                current_page = response.meta["page"]
                if current_page < total_pages:
                    yield scrapy.FormRequest(
                        url=self.start_urls[0],
                        method="POST",
                        formdata={
                            "_token": self.token,
                            "from_date": self.from_date,
                            "to_date": self.to_date,
                            "randomid": self.captcha,
                            "captchaInput": self.captcha,
                            "page": str(current_page + 1)
                        },
                        callback=self.parse_results,
                        meta={"page": current_page + 1}
                    )
