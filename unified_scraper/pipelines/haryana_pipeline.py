import subprocess
import os
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from unified_scraper.utils.upload_to_azure import upload_to_azure
from unified_scraper.utils.insert_csv_to_database import insert_judgments_from_csv
from Database.high_court_database import SessionLocal
from unified_scraper.spiders.link_to_pdf import SUCCESSFUL_PDFS

def run_upload(downloaded_files, root_folder):
    session = SessionLocal()
    try:
        upload_to_azure(session, downloaded_files,local_base=root_folder)
    finally:
        session.close()


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
def run_spider2(spider_name):
    print("downloading the pdfs")
    try:
        subprocess.run(
            ["scrapy","crawl",spider_name]
        )
        print(f"download successful")
    except subprocess.CalledProcessError as e:
        print(f"Spider failed: {e}")
        raise

def main():
    today_str = datetime.today().strftime("%Y%m%d")
    output_csv = f"haryana_result.csv"
    high_court_name="Punjab&Haryana High Court"
    run_spider("phhc_case_form_dynamic", output_csv)

    print("\n Inserting records into database...")
    insert_judgments_from_csv(
        csv_path=output_csv,
        high_court_name="Punjab&Haryana High Court",
        base_link="https://www.phhc.gov.in/home.php?search_param=free_text_search_judgment"
    )
    print("Database insertion completed.")

    print("\n downloading pdfs")
    run_spider2("general")
    root_folder = datetime.today().strftime("%Y")
    
    if SUCCESSFUL_PDFS:
        print(SUCCESSFUL_PDFS)
        run_upload(SUCCESSFUL_PDFS,root_folder=root_folder)
    else:
        print("No files downloaded, skipping upload.")
        


if __name__ == "__main__":
    main()