from datetime import datetime
from unified_scraper.utils.insert_csv_to_database import insert_judgments_from_csv_with_benches
from unified_scraper.utils.pdf_downloader import get_pending_pdfs
from Database.high_court_database import SessionLocal
from unified_scraper.utils.test import download_pdfs
import subprocess
def run_pdf_download(root_folder,high_court_name,bench_name):
    session = SessionLocal()
    try:
        pdf_items = get_pending_pdfs(session,high_court_name,bench_name)
        if not pdf_items:
            print("No pending PDFs to download.")
            return
        downloaded_files = download_pdfs(pdf_items,root_folder=root_folder)
        return downloaded_files
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
    bench_name = "Bench at Kalburagi"
    output_csv = "results.csv"
    root_folder = datetime.today().strftime("%Y")

    #     #Step 2: Insert CSV into database
    # run_spider("karnataka_spider", output_csv)    
    # print("\n Inserting records into database...")
    # insert_judgments_from_csv_with_benches( csv_path=output_csv,
    #         high_court_name=high_court_name,
    #         base_link="https://hcservices.ecourts.gov.in/hcservices/main.php",
    #         bench_name=bench_name,
    #         pdf_folder="karhc")
    # print("Database insertion completed.")

    downloaded_files = run_pdf_download(root_folder, high_court_name, bench_name)


if __name__ == "__main__":
    main()