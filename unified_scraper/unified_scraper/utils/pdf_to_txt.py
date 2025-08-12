from pathlib import Path
import os
import fitz

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

        print(f"TXT saved: {txt_path}")
    except Exception as e:
        print(f" Failed to convert {pdf_path} to TXT: {e}")
