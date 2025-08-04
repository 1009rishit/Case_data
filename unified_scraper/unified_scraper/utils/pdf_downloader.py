# delhi_judgments/utils/pdf_downloader.py

import os
import requests
import pandas as pd

def download_pdfs_from_csv(csv_file, output_folder, limit=15):
    os.makedirs(output_folder, exist_ok=True)

    df = pd.read_csv(csv_file)
    pdf_links = df['pdf_link'].dropna().head(limit)

    for i, link in enumerate(pdf_links, start=1):
        try:
            response = requests.get(link, timeout=10)
            response.raise_for_status()

            filename = os.path.join(output_folder, f"document_{i}.pdf")
            with open(filename, 'wb') as f:
                f.write(response.content)

            print(f"[{i}] Downloaded: {link}")
        except Exception as e:
            print(f"[{i}] Failed: {link} ({e})")
