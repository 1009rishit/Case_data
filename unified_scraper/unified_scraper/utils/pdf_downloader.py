import os
import requests
import pandas as pd
from datetime import datetime
import re

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def download_pdfs_from_csv(csv_file, output_root_folder="2025", limit=None):
    df = pd.read_csv(csv_file)

    required_columns = {'case_no', 'pdf_link'}
    if not required_columns.issubset(df.columns):
        print(f"CSV must contain columns: {', '.join(required_columns)}")
        return

    pdf_rows = df[['pdf_link', 'case_no']].dropna().head(limit)

    # Use today’s date
    today = datetime.today()
    year, month, day = today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")

    folder_path = os.path.join(output_root_folder, month, day, "delhc")
    os.makedirs(folder_path, exist_ok=True)

    for i, row in enumerate(pdf_rows.itertuples(index=False), start=1):
        try:
            response = requests.get(row.pdf_link, timeout=10)
            response.raise_for_status()

            safe_filename = sanitize_filename(row.case_no) + ".pdf"
            file_path = os.path.join(folder_path, safe_filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"[{i}] Downloaded: {row.pdf_link} → {file_path}")
        except Exception as e:
            print(f"[{i}] Failed: {row.pdf_link} ({e})")
