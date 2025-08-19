import os
import re
import requests
import fitz 
from datetime import datetime
from sqlalchemy.orm import Session
from Database.models import MetaData,HighCourt
import json


def sanitize_filename(name: str) -> str:
    """Remove invalid characters for filenames."""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

def parse_links(raw):
    if not raw:
        return []
    try:
        links = json.loads(raw)
        if isinstance(links, str):  
            return [links]
        if isinstance(links, list):
            return links
        return []
    except Exception:
        
        return [raw.strip()]

def get_pending_pdfs(session: Session, high_court_name: str, bench_name:str):
    """
    Retrieve all rows where is_downloaded = False for a specific High Court.
    Expands JSON document_link into multiple items (one per PDF link).
    """
    # Get HighCourt ID
    highcourt = (
    session.query(HighCourt)
    .filter(
        HighCourt.highcourt_name == high_court_name,
        HighCourt.bench == bench_name
    )
    .first()
)
    if not highcourt:
        return []
 
    pending = (
        session.query(MetaData)
        .filter(
            MetaData.is_downloaded == False,
            MetaData.high_court_id == highcourt.id
        )
        .all()
    ) 

    results = []
    for row in pending:
        links = parse_links(row.document_link)
        for link in links:
            results.append({
                "document_link": link,
                "case_id": row.case_id,
                "id": row.id
            })
    return results



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
        print(f"Failed to convert {pdf_path} to TXT: {e}")


def download_and_update(session: Session, pdf_items, output_root_folder):
    today = datetime.today()
    month, day = today.strftime("%m"), today.strftime("%d")

    folder_path = os.path.join(output_root_folder, month, day, "delhc")
    os.makedirs(folder_path, exist_ok=True)

    downloaded_files = []

    for i, item in enumerate(pdf_items, start=1):
        try:
            response = requests.get(item["document_link"], timeout=10)
            response.raise_for_status()

            safe_filename = sanitize_filename(item["case_id"]) + ".pdf"
            file_path = os.path.join(folder_path, safe_filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"[{i}] Downloaded: {item['document_link']} → {file_path}")

            pdf_to_txt(file_path)

            downloaded_files.append({
                "id": item["id"],
                "case_id": item["case_id"],
                "pdf_path": file_path
            })

        except Exception as e:
            print(f"[{i}] Failed: {item['document_link']} ({e})")

    return downloaded_files
