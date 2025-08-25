import os
import json
import requests
from datetime import datetime
import fitz  # PyMuPDF
import re

def sanitize_filename(name: str) -> str:
    """Remove invalid characters for filenames."""
    return re.sub(r'[\\/*?:"<>|]', '_', name)


# Common headers
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://hcservices.ecourts.gov.in/hcservices/main.php",
}

# Bench code mapping for Karnataka
bench_map = {
    "1": "Principal Bench at Bengaluru",
    "2": "Bench at Dharwad",
    "3": "Bench at Kalburagi",
}


def pdf_to_txt(pdf_path):
    """
    Convert a PDF file to TXT and save in the same directory.
    """
    txt_path = os.path.splitext(pdf_path)[0] + ".txt"
    try:
        with fitz.open(pdf_path) as pdf_doc:
            text_content = ""
            for page in pdf_doc:
                text_content += page.get_text()

        with open(txt_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(text_content)

    except Exception as e:
        print(f"❌ Failed to convert {pdf_path} to TXT: {e}")


def download_pdfs(pdf_items, root_folder):
    # Load cookies from spider output
    with open("cookies.json", "r") as f:
        cookies_data = json.load(f)
    today = datetime.today()
    month, day =  today.strftime("%m"), today.strftime("%d")

    downloaded_files = []

    for i, item in enumerate(pdf_items, start=1):
        pdf_url = item["document_link"]
        case_id = item["case_id"]
        bench = item.get("bench", "unknown").replace(" ", "_")
        date = str(item.get("date", "")).replace("-", "")

        # Find correct bench_code for cookies
        bench_code = None
        for code, name in bench_map.items():
            if bench.replace("_", " ") == name:
                bench_code = code
                break

        if not bench_code or bench_code not in cookies_data:
            print(f"[{i}] ❌ No cookies found for {bench}, skipping {case_id}")
            continue

        cookies = cookies_data[bench_code]

        # Create folder path: root/year/month/day/karhc/bench_name/
        folder_path = os.path.join(root_folder, month, day, "karhc", bench)
        os.makedirs(folder_path, exist_ok=True)

        try:
            r = requests.get(pdf_url, headers=headers, cookies=cookies, timeout=15)
            if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("application/pdf"):
                safe_filename = f"{sanitize_filename(case_id)}_{date}.pdf"
                file_path = os.path.join(folder_path, safe_filename)

                with open(file_path, "wb") as f:
                    f.write(r.content)

                print(f"[{i}] 📄 Saved {file_path}")

                # Convert to TXT
                pdf_to_txt(file_path)

                # Collect metadata
                downloaded_files.append({
                    "id": item.get("id"),
                    "case_id": case_id,
                    "pdf_path": file_path
                })

            else:
                print(f"[{i}] ⚠️ Failed {case_id}: {r.status_code}, {r.text[:200]}")

        except Exception as e:
            print(f"[{i}] ❌ Error downloading {case_id}: {e}")

    return downloaded_files
