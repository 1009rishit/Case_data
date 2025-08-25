import requests
import pandas as pd
import json
import os

# Load cookies from spider output
with open("cookies.json", "r") as f:
    cookies_data = json.load(f)

# Load scraped CSV
df = pd.read_csv("results.csv")

# Common headers
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://hcservices.ecourts.gov.in/hcservices/main.php",
}

output_folder = "pdfs"
os.makedirs(output_folder, exist_ok=True)

# Bench code mapping
bench_map = {
    "1": "Principal Bench at Bengaluru",
    "2": "Bench at Dharwad",
    "3": "Bench at Kalburagi",
}

for idx, row in df.iterrows():
    pdf_url = row["pdf_link"]
    case_no = str(row["case_no"]).replace("/", "_")
    date = str(row["date"]).replace("-", "")
    bench = str(row["bench"]).replace(" ", "_")

    if not pdf_url or pdf_url == "nan":
        continue

    # Find correct bench_code for cookies
    bench_code = None
    for code, name in bench_map.items():
        if row["bench"] == name:
            bench_code = code
            break

    if not bench_code or bench_code not in cookies_data:
        print(f"❌ No cookies found for {row['bench']}, skipping {case_no}")
        continue

    cookies = cookies_data[bench_code]

    # Download PDF
    r = requests.get(pdf_url, headers=headers, cookies=cookies)
    if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("application/pdf"):
        filename = f"{output_folder}/{bench}_{case_no}_{date}.pdf"
        with open(filename, "wb") as f:
            f.write(r.content)
        print(f"📄 Saved {filename}")
    else:
        print(f"⚠️ Failed {case_no}: {r.status_code}, {r.text[:200]}")

