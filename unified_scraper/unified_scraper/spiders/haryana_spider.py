import scrapy
import datetime
import re,time,requests
import base64
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

XEvil_CONFIG = {
    "baseUrl": os.getenv("BASE_URL_XEVIL"),
    "key" : os.getenv("CAPTCHA_KEY"), 
    "initialDelay": 5,
    "interval": 5,
    "retries": 6
}

class PHHCCaseSpider(scrapy.Spider):
    custom_settings = {
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'crawl.log',
        'LOG_STDOUT': True,
        'REDIRECT_ENABLED': False,
    }

    name = "phhc_case_form_dynamic"
    allowed_domains = ["phhc.gov.in"]
    start_url = os.getenv("HARYANA_START_URL")

    def date_range_last_two_months(self):
        today = datetime.datetime.today()  # Use fixed current time for reproducibility
        two_months_ago = today - datetime.timedelta(days=60)
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
                    cb_kwargs={'case_type': case_type, 'day': day.replace("/", "-")},
                    dont_filter=True
                )

    def save_response(self, response, case_type, day):
        from datetime import datetime
        import urllib.parse as up
        date_obj = datetime.strptime(day, "%d-%m-%Y")
        new_date = date_obj.strftime("%Y-%m-%d")
        if b'refine your query' in response.body.lower():
            self.logger.warning(f"'Refine your query' found for case_type={case_type}, date={day}, url={response.url}")

        table = response.css('table#tables11')
        headers = table.css('tr th::text').getall()
        rows = table.css('tr')[1:]

        if not rows:
            return
        for row in rows:
            cells = row.css('td')
            columns = {}
            pdf_link = []
            party = ''
            for i, cell in enumerate(cells):

                text = cell.css('::text').get(default='').strip()
                columns[headers[i] if i < len(headers) else f'col_{i}'] = text
                

                for a in cell.xpath('.//a[text()="View Order"]'):
                    onclick = a.attrib.get('OnClick') or a.attrib.get('onclick', '')
                    m = re.search(r"window\.open\('([^']+)'\)", onclick)
                    if m:
                        li=response.urljoin(m.group(1))
                        pdf_link.append(response.urljoin(m.group(1)))
                        
            if not pdf_link:
                continue

            if len(cells) > 1:
               
                href = cells[1].css('a::attr(href)').get(default='')
                if href:
                    import urllib.parse as up
                    parsed_qs = up.parse_qs(up.urlparse(href).query)
                    encoded_case_id = parsed_qs.get('case_id', [''])[0]

                
                case_no = cells[1].css('a b::text').get(default='').strip()

                
                party = cells[2].css('::text').get(default='').strip()
                
            yield{
                
                'date':new_date,
                'party':party,
                'case_no':case_no,
                'pdf_link':pdf_link

            }
            

        next_page = response.css('a:contains("Next")::attr(href), a[title="Next"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.save_response,
                cb_kwargs={'case_type': case_type, 'day': day},
                dont_filter=True
            )
    