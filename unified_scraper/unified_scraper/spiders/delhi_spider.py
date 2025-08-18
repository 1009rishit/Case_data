import scrapy
from bs4 import BeautifulSoup
import re
import math
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def clean_date(raw_date: str):
    """Parse and clean date strings like '01-01-2025 (pdf)' -> datetime.date"""
    if pd.isna(raw_date) or not str(raw_date).strip():
        return None
    try:
        cleaned = str(raw_date).replace("(pdf)", "").strip().split()[0]
        return datetime.strptime(cleaned, '%d-%m-%Y').date()
    except ValueError:
        return None
    
class DelhiJudgmentsSpider(scrapy.Spider):
    name = "delhi_spider"
    allowed_domains = ["delhihighcourt.nic.in"]
    start_url_str = os.getenv("DELHI_START_URL")  
    if start_url_str:
        start_urls = [start_url_str]  # wrap string in a list
    else:
        start_urls = []
        
    def parse(self, response):

        token = response.css('input[name="_token"]::attr(value)').get()
        captcha = response.css('span#captcha-code::text').get()

        self.token = token
        self.captcha = captcha
        today = datetime.today()
        self.from_date = (today - timedelta(days=5)).strftime("%d-%m-%Y")
        self.to_date = today.strftime("%d-%m-%Y")

      
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
        rows = soup.select("#registrarsTableValue tr")[1:]  

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            case_no = cols[1].get_text(strip=True).replace('\xa0', ' ')
            party = cols[3].get_text(strip=True).replace('\xa0', ' ')

            # Extract all <a> tags in the 3rd column (date column)
            links = cols[2].find_all("a", href=True)
            pdf_link = ""
            txt_link = ""
            date = ""

            for link_tag in links:
                href = link_tag["href"]
                text = link_tag.get_text(strip=True)
                if date:
                    date=clean_date(date)
                if not date:
                    date = text

                if href.lower().endswith(".pdf"):
                    pdf_link = response.urljoin(href)
                
                elif href.lower().endswith(".txt"):
                    txt_link = response.urljoin(href)

            yield {
                "case_no": case_no,
                "date": date,
                "party": party,
                "pdf_link": pdf_link,
                "txt_link": txt_link
            }

      
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
