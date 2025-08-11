from pdf2image import convert_from_bytes
import pytesseract

def pdf_bytes_to_text(pdf_bytes):
    """
    Convert PDF bytes to extracted text using OCR.
    
    :param pdf_bytes: PDF content in bytes
    :return: Extracted text as a string
    """
    try:
        extracted_text = ""
        images = convert_from_bytes(pdf_bytes, dpi=300)
        for img in images:
            text = pytesseract.image_to_string(img)
            extracted_text += text + "\n"
        return extracted_text
    except Exception as e:
        return f"[OCR FAILED] {e}"
