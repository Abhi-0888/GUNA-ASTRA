import os

import docx
import pdfplumber

from utils.logger import get_logger

logger = get_logger("DocReader")


def extract_text(file_path):
    """
    Extracts text from PDF, DOCX, or TXT files.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            return _extract_from_pdf(file_path)
        elif ext == ".docx":
            return _extract_from_docx(file_path)
        elif ext == ".txt":
            return _extract_from_txt(file_path)
        else:
            logger.warning(f"Unsupported file extension: {ext}")
            return None
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def _extract_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def _extract_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs]).strip()


def _extract_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()
