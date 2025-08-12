from pathlib import Path
import os
import fitz  # PyMuPDF

def pdf_to_txt(pdf_path):
    """
    Converts a PDF to a TXT file in the same directory.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        return None

    # Open PDF
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()

    # Save TXT file
    txt_path = pdf_path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ TXT file saved: {txt_path}")
    return txt_path

# -----------------
# TEST FUNCTION
# -----------------
if __name__ == "__main__":
    # Give path to your sample PDF
    pdf_file_path = "sample.pdf"  # Change this to your test file
    pdf_to_txt(pdf_file_path)
