import subprocess
import os
from datetime import datetime
from pathlib import Path
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from unified_scraper.utils.pdf_downloader import get_pending_pdfs, download_and_update
from unified_scraper.utils.insert_csv_to_database import insert_judgments_from_csv
from Database.high_court_database import SessionLocal
from unified_scraper.utils.upload_to_azure import upload_to_azure

def run_pdf_download(root_folder):
    session = SessionLocal()
    try:
        pdf_items = get_pending_pdfs(session)
        if not pdf_items:
            print("No pending PDFs to download.")
            return
        downloaded_files = download_and_update(session, pdf_items,output_root_folder=root_folder)
        return downloaded_files
    finally:
        session.close()


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


def main():
    # File & folder setup
    today_str = datetime.today().strftime("%Y%m%d")
    output_csv = f"delhi_result.csv"

    run_spider("delhi_spider", output_csv)

    print("\n Inserting records into database...")
    insert_judgments_from_csv(
        csv_path=output_csv,
        high_court_name="Delhi High Court",
        base_link="https://delhihighcourt.nic.in"
    )
    print("Database insertion completed.")

    root_folder = datetime.today().strftime("%Y")

    downloaded_files = run_pdf_download(root_folder=root_folder)
    if downloaded_files:
        run_upload(downloaded_files,root_folder=root_folder)
    else:
        print("No files downloaded, skipping upload.")


if __name__ == "__main__":
    main()
