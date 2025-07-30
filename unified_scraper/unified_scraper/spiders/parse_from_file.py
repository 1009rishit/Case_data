import scrapy
from bs4 import BeautifulSoup
import os

class FileJudgmentSpider(scrapy.Spider):
    name = "parse_from_file"

    def start_requests(self):
        # Use local result.html file
        filepath = os.path.join(os.getcwd(), "result.html")
        url = "file://" + filepath
        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "registrarsTableValue"})

        if not table:
            self.logger.warning("⚠️ Table not found.")
            return

        rows = table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                # Extract case number and judgment code
                case_no_block = cols[1].get_text(separator=" ", strip=True)
                case_no = case_no_block.split()[0] if case_no_block else ""

                # Extract PDF link and date
                date_col = cols[2]
                pdf_tag = date_col.find("a", href=True)
                pdf_link = pdf_tag['href'] if pdf_tag else ""
                date = pdf_tag.get_text(strip=True) if pdf_tag else ""

                # Extract party details
                party_raw = cols[3].decode_contents().replace("<br>", " ").replace("&nbsp;", " ")
                soup2 = BeautifulSoup(party_raw, "html.parser")
                party = soup2.get_text(" ", strip=True)

                yield {
                    "case_no": case_no,
                    "date": date,
                    "party": party,
                    "pdf_link": pdf_link
                }
