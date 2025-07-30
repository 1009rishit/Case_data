import scrapy
from datetime import datetime, timedelta
import csv
import os

class PHHCJudgmentSpider(scrapy.Spider):
    name = "phhc_judgments_chunked"
    allowed_domains = ["phhc.gov.in"]
    start_urls = ["https://www.phhc.gov.in/home.php?search_param=free_text_search_judgment"]

    def __init__(self):
        super().__init__()
        self.items = []
        self.case_types = ["CRM-M"]  # Testing with only one case type
        self.days_per_chunk = 10
        self.date_format = "%d-%m-%Y"

    def start_requests(self):
        end_date = datetime.today()
        start_date = end_date - timedelta(days=60)

        for case_type in self.case_types:
            self.logger.info(f"Generating requests for CaseType={case_type}")
            chunk_start = start_date
            while chunk_start < end_date:
                chunk_end = min(chunk_start + timedelta(days=self.days_per_chunk - 1), end_date)
                formdata = {
                    'ctype': case_type,
                    'dfrom': chunk_start.strftime(self.date_format),
                    'dto': chunk_end.strftime(self.date_format),
                    'search_type': 'J'
                }
                yield scrapy.FormRequest(
                    url=self.start_urls[0],
                    formdata=formdata,
                    callback=self.parse_results,
                    cb_kwargs={
                        'case_type': case_type,
                        'from_date': chunk_start.strftime(self.date_format),
                        'to_date': chunk_end.strftime(self.date_format),
                        'page': 1
                    },
                    dont_filter=True
                )
                chunk_start += timedelta(days=self.days_per_chunk)

    def parse_results(self, response, case_type, from_date, to_date, page):
        rows = response.css('table#tables11 tr')[1:]  # skip header
        self.logger.info(f"Scraping: CaseType={case_type}, From={from_date}, To={to_date}, Page={page}, Rows={len(rows)}")

        for row in rows:
            cols = [td.xpath('string(.)').get().strip() for td in row.css('td')]
            if len(cols) >= 4:
                item = {
                    'Case Type': case_type,
                    'From Date': from_date,
                    'To Date': to_date,
                    'Case Title': cols[1],
                    'Case No': cols[2],
                    'Decision Date': cols[3],
                    'Judge': cols[4] if len(cols) > 4 else None
                }
                self.logger.info(f"Extracted row: {item}")
                self.items.append(item)

        # Handle pagination by simulating clicking next
        next_page_link = response.css("#tables11 > tbody > tr:last-child > td > a:contains('Next')::attr(href)").get()
        if next_page_link:
            next_formdata = {
                'ctype': case_type,
                'dfrom': from_date,
                'dto': to_date,
                'search_type': 'J'
            }
            yield scrapy.FormRequest(
                url=response.url,
                formdata=next_formdata,
                callback=self.parse_results,
                cb_kwargs={
                    'case_type': case_type,
                    'from_date': from_date,
                    'to_date': to_date,
                    'page': page + 1
                },
                dont_filter=True
            )

    def closed(self, reason):
        if not self.items:
            self.logger.warning("No items were scraped!")
            return

        output_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, "phhc_all_judgments_sorted.csv")

        sorted_items = sorted(self.items, key=lambda x: (x['Case Type'], x['Decision Date']))

        with open(file_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted_items[0].keys())
            writer.writeheader()
            writer.writerows(sorted_items)

        self.logger.info(f"CSV written with {len(sorted_items)} records to {file_path}.")
