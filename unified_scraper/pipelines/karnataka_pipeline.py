import subprocess
import os
import sys
import logging
import shutil
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from unified_scraper.utils.insert_csv_to_database import insert_judgments_from_csv_with_benches
from unified_scraper.utils.pdf_downloader import get_pending_pdfs
from Database.high_court_database import SessionLocal
from unified_scraper.unified_scraper.utils.downloader_for_karnataka import download_pdfs
from unified_scraper.utils.upload_to_azure import upload_to_azure
from unified_scraper.utils.upload_logs_to_azure import upload_crawl_log


# Configure logger once → all spider + bench logs go to crawl.log
logging.basicConfig(
    filename="crawl.log",
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)


def run_pdf_download(root_folder, high_court_name, bench_name):
    session = SessionLocal()
    try:
        pdf_items = get_pending_pdfs(session, high_court_name, bench_name)
        if not pdf_items:
            logging.info(f"No pending PDFs to download for {bench_name}.")
            return
        downloaded_files = download_pdfs(pdf_items, root_folder=root_folder)
        logging.info(f"Downloaded {len(downloaded_files)} PDFs for {bench_name}.")
        return downloaded_files
    except Exception as e:
        logging.exception(f"PDF download failed for {bench_name}: {e}")
    finally:
        session.close()


def run_upload(downloaded_files, root_folder):
    session = SessionLocal()
    try:
        upload_to_azure(session, downloaded_files, local_base=root_folder)
        logging.info(f"Uploaded {len(downloaded_files)} PDFs to Azure.")
    except Exception as e:
        logging.exception(f"Upload failed: {e}")
    finally:
        session.close()


def run_spider(spider_name, output_csv):
    logging.info(f"Running Scrapy spider: {spider_name}")
    try:
        subprocess.run(
            ["scrapy", "crawl", spider_name, "-o", output_csv],
            check=True
        )
        logging.info(f"Spider {spider_name} finished. Output saved to {output_csv}")
    except subprocess.CalledProcessError as e:
        logging.exception(f"Spider {spider_name} failed: {e}")
        raise


def main():
    high_court_name = "Karnataka High Court"
    bench_names = [
        "Bench at Kalburagi",
        "Bench at Dharwad",
        "Principal Bench at Bengaluru"
    ]
    output_csv = "karnataka_results.csv"
    root_folder = datetime.today().strftime("%Y")

    try:
        run_spider("karnataka_spider", output_csv)

        for bench_name in bench_names:
            logging.info(f" Processing {bench_name}...")

            try:
                insert_judgments_from_csv_with_benches(
                    csv_path=output_csv,
                    high_court_name=high_court_name,
                    base_link="https://hcservices.ecourts.gov.in/hcservices/main.php",
                    bench_name=bench_name,
                    pdf_folder="karhc"
                )
                logging.info(f"Database insertion completed for {bench_name}.")

                downloaded_files = run_pdf_download(root_folder, high_court_name, bench_name)

                if downloaded_files:
                    run_upload(downloaded_files, root_folder)
                else:
                    logging.warning(f"No files downloaded for {bench_name}, skipping upload.")

            except Exception as bench_err:
                logging.exception(f"Error while processing {bench_name}: {bench_err}")

            finally:
                temp_log = f"crawl_temp_{bench_name.replace(' ', '_')}.log"
                try:
                    if os.path.exists("crawl.log"):
                        shutil.copy("crawl.log", temp_log)
                        upload_crawl_log(
                            local_log_path=temp_log,
                            user_choice=f"karhc/{bench_name.replace(' ', '_')}"
                        )
                        logging.info(f"✅ Uploaded crawl.log for {bench_name}")
                    else:
                        logging.warning("⚠️ crawl.log not found for upload.")
                except Exception as log_err:
                    logging.error(f"Failed during upload for {bench_name}: {log_err}")
                finally:
                    if os.path.exists(temp_log):
                        os.remove(temp_log)

    except Exception as e:
        # If pipeline fails before benches
        logging.exception(f"Pipeline failed with error: {e}")
        try:
            temp_log = "crawl_temp_pipeline.log"
            shutil.copy("crawl.log", temp_log)

            upload_crawl_log(local_log_path=temp_log, user_choice="karhc/spider")

            os.remove(temp_log)
        except Exception as log_err:
            logging.error(f"Failed to upload crawl.log to spider folder: {log_err}")

    finally:
        # Cleanup always
        for file in ["cookies.json", output_csv, "results.xlsx","crawl.log"]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    logging.info(f"Deleted file: {file}")
                except Exception as e:
                    logging.info(f"Failed to delete {file}: {e}")


if __name__ == "__main__":
    main()
