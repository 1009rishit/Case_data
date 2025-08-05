# download_pdfs.py

from unified_scraper.utils.pdf_downloader import download_pdfs_from_csv

if __name__ == "__main__":
    csv_file = "delhi_result.csv"
    output_dir = "data/delhi_pdf"
    download_limit = None

    download_pdfs_from_csv(csv_file, output_dir, limit=download_limit)
