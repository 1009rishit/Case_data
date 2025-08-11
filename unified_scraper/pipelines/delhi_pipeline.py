import subprocess
import os
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from unified_scraper.utils.pdf_downloader import download_pdfs_from_csv
from unified_scraper.utils.insert_csv_to_database import insert_judgments_from_csv


def run_spider(spider_name, output_csv):
    print(" Running Scrapy spider...")
    try:
        subprocess.run(
            ["scrapy", "crawl", spider_name, "-o", output_csv],
            check=True
        )
        print(f"Spider finished. Output saved to {output_csv}")
    except subprocess.CalledProcessError as e:
        print(f"Spider failed: {e}")
        raise


def main():
    # File & folder setup
    today_str = datetime.today().strftime("%Y%m%d")
    output_csv = f"delhi_result.csv"

    run_spider("delhi_spider", output_csv)

    print("\nDownloading PDFs...")
    download_pdfs_from_csv(output_csv, output_root_folder="2025")
    print("PDF download step completed.")

    # STEP 3: Insert into DB
    print("\n Inserting records into database...")
    insert_judgments_from_csv(
        csv_path=output_csv,
        high_court_name="Delhi High Court",
        base_link="https://delhihighcourt.nic.in"
    )
    print("Database insertion completed.")



if __name__ == "__main__":
    main()
