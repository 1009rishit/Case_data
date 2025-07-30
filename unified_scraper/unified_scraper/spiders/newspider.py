import scrapy
import os
import datetime
import re

class PHHCCaseSpider(scrapy.Spider):
    custom_settings = {
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'crawl.log',
        'LOG_STDOUT': True,
    }

    name = "phhc_case_form_dynamic"
    allowed_domains = ["phhc.gov.in"]
    start_url = "https://www.phhc.gov.in/home.php?search_param=free_text_search_judgment"

    def date_range_last_two_months(self):
        today = datetime.datetime.today()  # Use fixed current time for reproducibility
        two_months_ago = today - datetime.timedelta(days=61)
        for n in range((today - two_months_ago).days):
            day = two_months_ago + datetime.timedelta(days=n)
            yield day.strftime('%d/%m/%Y')

    def start_requests(self):
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse_case_types,
            dont_filter=True
        )

    def parse_case_types(self, response):
        # Restore logic to use all case types
        case_types = response.css('select[name="t_case_type"] option::attr(value)').getall()
        case_types = [ct for ct in case_types if ct.strip() != '']
        self.logger.info(f"Found {len(case_types)} case types: {case_types}")

        for case_type in case_types:
            for day in self.date_range_last_two_months():
                formdata = {
                    'from_date': day,
                    'to_date': day,
                    'pet_name': '',
                    'res_name': '',
                    'free_text': '',
                    't_case_type': case_type,
                    't_case_year': '',
                    'submit': 'Search Case',
                }
                yield scrapy.FormRequest(
                    url=self.start_url,
                    formdata=formdata,
                    callback=self.save_response,
                    cb_kwargs={'case_type': case_type, 'day': day},
                    dont_filter=True
                )

    def save_response(self, response, case_type, day):
        from ..items import PhhcCrawlerItem

        # Log if 'refine your query' appears in the response
        if b'refine your query' in response.body.lower():
            self.logger.warning(f"'Refine your query' found for case_type={case_type}, date={day}, url={response.url}")

        table = response.css('table#tables11')
        headers = table.css('tr th::text').getall()
        rows = table.css('tr')[1:]  # skip header row

        if not rows:
            return
        for row in rows:
            cells = row.css('td')
            columns = {}
            links = []
            for i, cell in enumerate(cells):
                # Get text
                text = cell.css('::text').get(default='').strip()
                columns[headers[i] if i < len(headers) else f'col_{i}'] = text
                # Extract only "View Order" links via onclick parsing
                for a in cell.xpath('.//a[text()="View Order"]'):
                    onclick = a.attrib.get('OnClick') or a.attrib.get('onclick', '')
                    m = re.search(r"window\.open\('([^']+)'\)", onclick)
                    if m:
                        links.append(response.urljoin(m.group(1)))
            if not links:
                continue
            item = PhhcCrawlerItem(
                case_type=case_type,
                date=day,
                columns=columns,
                links=links
            )
            yield item

        # Pagination: look for a 'Next' button or link
        next_page = response.css('a:contains("Next")::attr(href), a[title="Next"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.save_response,
                cb_kwargs={'case_type': case_type, 'day': day},
                dont_filter=True
            )