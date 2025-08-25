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
from unified_scraper.utils.upload_logs_to_azure import upload_crawl_log

def run_pdf_download(root_folder,high_court_name,bench_name):
    session = SessionLocal()
    try:
        pdf_items = get_pending_pdfs(session,high_court_name,bench_name)
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
    high_court_name = "Karnataka High Court"
    bench_name = None
    output_csv = "karanataka_result.csv"
    root_folder = datetime.today().strftime("%Y")

    try:
        # Step 1: Run spider
        run_spider("karnataka_spider", output_csv)

        # Step 2: Insert CSV into database
        print("\n Inserting records into database...")
        insert_judgments_from_csv("results.csv", "Karnataka High Court", base_link, "Dharwad", "dharwad_folder")
        print("Database insertion completed.")

        downloaded_files = run_pdf_download(root_folder, high_court_name, bench_name)

        if downloaded_files:
            run_upload(downloaded_files, root_folder)
        else:
            print("No files downloaded, skipping upload.")

    except Exception as e:
        print(f"Pipeline failed with error: {e}")

    finally:
        try:
            upload_crawl_log(local_log_path="crawl.log", user_choice="delhc")
        except Exception as log_err:
            print(f" Failed to upload crawl.log: {log_err}")


if __name__ == "__main__":
    main()