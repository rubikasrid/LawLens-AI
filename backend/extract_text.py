from pathlib import Path

def extract_text_from_pdf(file_path: str) -> str:
    text = ""

    # Method 1: Try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception:
        pass

    if text.strip():
        return text.strip()

    # Method 2: Fallback to pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception:
        pass

    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    text = ""
    try:
        import docx
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
    except Exception:
        pass
    return text.strip()


def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        extracted = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        extracted = extract_text_from_docx(file_path)
    else:
        extracted = ""

    # Fallback message for scanned/image PDFs to avoid HTTP 400 crashes
    if not extracted.strip():
        return (
            "This document appears to be an image or scanned document without selectable text. "
            "Please upload a document with embedded text (or convert the file using OCR)."
        )

    return extracted