import re, time, requests, base64, hashlib, os, scrapy, datetime, pandas as pd
from pdf2image import convert_from_bytes
import pytesseract

XEvil_CONFIG = {
    "baseUrl": "http://98.70.40.179/",
    "key": os.getenv("CAPTCHA_KEY"),
    "initialDelay": 5,
    "interval": 5,
    "retries": 6
}

class PHHCCaseSpider(scrapy.Spider):
    name = "general"
    allowed_domains = ["phhc.gov.in"]

    custom_settings = {
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'crawl.log',
        'LOG_STDOUT': True,
        'REDIRECT_ENABLED': False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloaded_count = 0
        self.last_success_row = -1

    def start_requests(self):
        # Read crawl.log and get only successfully saved rows
        # processed_rows = set()
        # if os.path.exists('crawl11.log'):
        #     with open('crawl.log', 'r', encoding='utf-8', errors='ignore') as log_file:
        #         for line in log_file:
        #             match = re.search(r'✅ Row (\d+): PDF saved at', line)
        #             if match:
        #                 processed_rows.add(int(match.group(1)))

        self.df = pd.read_csv('result_haryana.csv')
        start_index = int(getattr(self, 'start_index', 0))

        for index, url in enumerate(self.df['links'][start_index:], start=start_index):
            # if index in processed_rows:
            #     self.logger.info(f"⏩ Skipping row {index} (already processed).")
            #     continue

            yield scrapy.Request(
                url=url,
                callback=self.solve_and_download_pdf,
                cb_kwargs={'link': url, 'row_index': index},
                dont_filter=True
            )

    def solve_and_download_pdf(self, response, link, row_index):
        from urllib.parse import urljoin

        form_action = response.xpath('//form[@id="security_chaeck"]/@action').get()
        captcha_src = response.css('img#captchaimg::attr(src)').get()

        if not form_action or not captcha_src:
            self.logger.error(f"[Row {row_index}] Could not extract CAPTCHA form or image.")
            return

        full_post_url = response.urljoin(form_action)
        captcha_url = response.urljoin(captcha_src)

        session = requests.Session()
        for name, value in response.request.cookies.items():
            session.cookies.set(name, value)

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': response.url,
            'Origin': 'https://www.phhc.gov.in',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        session.headers.update(headers)

        try:
            captcha_response = session.get(captcha_url)
            captcha_bytes = captcha_response.content
        except Exception as e:
            self.logger.error(f"[Row {row_index}] Failed to download CAPTCHA image: {e}")
            return

        captcha_text = self.solve_captcha_xevil(captcha_bytes)
        if not captcha_text:
            self.logger.error(f"[Row {row_index}] CAPTCHA solving failed for {link}")
            return

        payload = {'vercode': captcha_text, 'submit': 'Submit'}

        try:
            post_response = session.post(full_post_url, data=payload, allow_redirects=True)
        except Exception as e:
            self.logger.error(f"[Row {row_index}] POST request failed: {e}")
            return

        content_type = post_response.headers.get("Content-Type", "")
        if content_type.startswith("application/pdf"):
            auth_token = link.split('auth=')[-1]
            self.save_pdf_and_txt(post_response.content, auth_token, row_index)
            self.downloaded_count += 1
            self.last_success_row = max(self.last_success_row, row_index)
        else:
            debug_file = "captcha_failed_response.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(post_response.text)
            self.logger.warning(f"[Row {row_index}] CAPTCHA failed. See '{debug_file}'")

    def solve_captcha_xevil(self, captcha_bytes):
        try:
            base64_image = base64.b64encode(captcha_bytes).decode('utf-8')
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
                    self.logger.info(f"✅ CAPTCHA Solved: {captcha_text}")
                    return captcha_text
                time.sleep(XEvil_CONFIG["interval"])

            self.logger.warning("CAPTCHA solving timed out.")
            return

        except Exception as e:
            self.logger.error(f"CAPTCHA solving failed: {str(e)}")
            return

    def save_pdf_and_txt(self, pdf_bytes, auth_token, row_index):
        try:
            # Create hash-based filename
            filename_hash = hashlib.md5(auth_token.encode()).hexdigest()

            # Build directory structure: year/month/day/phhc
            today = datetime.datetime.now()
            dir_path = os.path.join(
                str(today.year),
                f"{today.month:02d}",
                f"{today.day:02d}",
                "phhc"
            )
            os.makedirs(dir_path, exist_ok=True)

            # Define file paths
            pdf_path = os.path.join(dir_path, f"{filename_hash}.pdf")
            txt_path = os.path.join(dir_path, f"{filename_hash}.txt")

            # Save the PDF file
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            # Convert PDF pages to images and extract text using OCR
            extracted_text = ""
            try:
                images = convert_from_bytes(pdf_bytes, dpi=300)
                for i, img in enumerate(images):
                    text = pytesseract.image_to_string(img)
                    extracted_text += text + "\n"
            except Exception as img_err:
                self.logger.error(f"[Row {row_index}] OCR failed: {img_err}")
                extracted_text = "[OCR FAILED]"

            # Save extracted text to TXT file
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)

            self.logger.info(f"✅ Row {row_index}: PDF saved at {pdf_path}")
            self.logger.info(f"📝 Row {row_index}: TXT saved at {txt_path}")

        except Exception as e:
            self.logger.error(f"[Row {row_index}] Failed during PDF/TXT save: {e}")
    def closed(self, reason):
        self.logger.info("\n📄 Crawl completed.")
        self.logger.info(f"✅ Total PDFs downloaded: {self.downloaded_count}")
        self.logger.info(f"📌 Last successfully downloaded row index: {self.last_success_row}")
