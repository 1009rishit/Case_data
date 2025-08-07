import os
import base64
import requests
import time
import logging
from dotenv import load_dotenv

load_dotenv()

XEvil_CONFIG = {
    "baseUrl": "http://98.70.40.179/",
    "key": os.getenv("CAPTCHA_KEY"),
    "initialDelay": 5,
    "interval": 5,
    "retries": 6
}

class XevilCaptchaSolver:
    def __init__(self, config=XEvil_CONFIG):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def solve(self, captcha_bytes):
        try:
            base64_image = base64.b64encode(captcha_bytes).decode('utf-8')
            submit = requests.post(
                self.config["baseUrl"] + "in.php",
                data={
                    "key": self.config["key"],
                    "method": "base64",
                    "body": base64_image
                }
            )
            if "OK|" not in submit.text:
                self.logger.warning("❌ Failed to submit CAPTCHA to XEvil")
                return None

            captcha_id = submit.text.split("|")[1]
            time.sleep(self.config["initialDelay"])

            for _ in range(self.config["retries"]):
                poll = requests.get(
                    self.config["baseUrl"] + "res.php",
                    params={
                        "key": self.config["key"],
                        "action": "get",
                        "id": captcha_id
                    }
                )
                if "OK|" in poll.text:
                    captcha_text = poll.text.split("|")[1]
                    print(f"[XEvil Captcha Solved] => {captcha_text}")
                    return captcha_text
                time.sleep(self.config["interval"])

            self.logger.warning("⌛ CAPTCHA solving timed out.")
            return None

        except Exception as e:
            self.logger.error(f"❌ CAPTCHA solving failed: {str(e)}")
            return None
