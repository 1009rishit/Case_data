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
                        li=response.urljoin(m.group(1))
                        links.append(response.urljoin(m.group(1)))
                        # yield scrapy.Request(
                        #     url=li,
                        #     callback=self.solve_and_download_pdf,
                        #     cb_kwargs={'link': li},
                        #     dont_filter=True
                        #     )
            if not links:
                continue
            item = PhhcCrawlerItem(
                case_type=case_type,
                date=day,
                columns=columns,
                links=links
            )
            yield item

            

        #Pagination: look for a 'Next' button or link
        next_page = response.css('a:contains("Next")::attr(href), a[title="Next"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.save_response,
                cb_kwargs={'case_type': case_type, 'day': day},
                dont_filter=True
            )
                   

    # def solve_and_download_pdf(self, response, link):
    #     import requests
    #     from urllib.parse import urljoin
    #     import os
    #     import hashlib

    #     # Step 1: Extract form action and CAPTCHA image
    #     form_action = response.xpath('//form[@id="security_chaeck"]/@action').get()
    #     captcha_src = response.css('img#captchaimg::attr(src)').get()

    #     if not form_action or not captcha_src:
    #         self.logger.error("Could not extract CAPTCHA form or image.")
    #         return

    #     full_post_url = response.urljoin(form_action)
    #     captcha_url = response.urljoin(captcha_src)

    #     # Step 2: Transfer cookies from Scrapy to requests.Session
    #     session = requests.Session()
    #     for name, value in response.request.cookies.items():
    #         session.cookies.set(name, value)

    #     headers = {
    #         'User-Agent': 'Mozilla/5.0',
    #         'Referer': response.url,
    #         'Origin': 'https://www.phhc.gov.in',
    #         'Content-Type': 'application/x-www-form-urlencoded',
    #     }
    #     session.headers.update(headers)

    #     # Step 3: Download CAPTCHA image
    #     try:
    #         captcha_response = session.get(captcha_url)
    #         captcha_bytes = captcha_response.content
    #         with open('captcha.png', 'wb') as f:
    #             f.write(captcha_response.content)
    #         print("✅ CAPTCHA image saved as 'captcha.png'. Please open it and solve.")
    #     except Exception as e:
    #         self.logger.error(f"Failed to download CAPTCHA image: {e}")
    #         return

    #     # Step 4: Solve manually
    #     captcha_text = self.solve_captcha_xevil(captcha_bytes)
    #     if not captcha_text:
    #         self.logger.error(f"CAPTCHA solving failed for {link}")
    #         return

    #     # Step 5: POST the form to get PDF
    #     payload = {
    #         'vercode': captcha_text,
    #         'submit': 'Submit'
    #     }

    #     try:
    #         post_response = session.post(full_post_url, data=payload, allow_redirects=True)
    #     except Exception as e:
    #         self.logger.error(f"POST request failed: {e}")
    #         return

    #     # Step 6: Check response and save PDF
    #     content_type = post_response.headers.get("Content-Type", "")
    #     if content_type.startswith("application/pdf"):
    #         # Generate unique and safe filename using hash
    #         auth_token = link.split('auth=')[-1]
    #         filename_hash = hashlib.md5(auth_token.encode()).hexdigest()
    #         filename = f"{filename_hash}.pdf"

    #         folder = "2025/08/06/hppc"
    #         os.makedirs(folder, exist_ok=True)
    #         path = os.path.join(folder, filename)

    #         with open(path, "wb") as f:
    #             f.write(post_response.content)
    #         self.logger.info(f"✅ PDF downloaded and saved to {path}")
    #     else:
    #         # Save HTML for debugging
    #         debug_file = "captcha_failed_response.html"
    #         with open(debug_file, "w", encoding="utf-8") as f:
    #             f.write(post_response.text)
    #         self.logger.warning(f"Failed to download PDF for {link}. CAPTCHA likely failed. See '{debug_file}'")
                
    # def solve_captcha_xevil(self, captcha_bytes):
    #     try:
    #         base64_image = base64.b64encode(captcha_bytes).decode('utf-8')
    #         submit = requests.post(
    #         XEvil_CONFIG["baseUrl"] + "in.php",
    #         data={
    #                 "key": XEvil_CONFIG["key"],
    #                 "method": "base64",
    #                 "body": base64_image
    #             }
    #         )
    #         if "OK|" not in submit.text:
    #             self.logger.warning("Failed to submit CAPTCHA to XEvil")
    #             return

    #         captcha_id = submit.text.split("|")[1]
    #         time.sleep(XEvil_CONFIG["initialDelay"])

    #         # Poll for solved CAPTCHA
    #         captcha_text = None
    #         for _ in range(XEvil_CONFIG["retries"]):
    #             poll = requests.get(
    #                 XEvil_CONFIG["baseUrl"] + "res.php",
    #                 params={
    #                         "key": XEvil_CONFIG["key"],
    #                         "action": "get",
    #                         "id": captcha_id
    #                 }
    #             )
    #             if "OK|" in poll.text:
    #                 captcha_text = poll.text.split("|")[1]
    #                 print(f"\n{captcha_text}\n")
    #                 return captcha_text
    #             time.sleep(XEvil_CONFIG["interval"])

    #         if not captcha_text:
    #             self.logger.warning("CAPTCHA solving timed out.")
    #             return

    #     except Exception as e:
    #             self.logger.error(f"CAPTCHA solving failed: {str(e)}")
    #             return
    

    