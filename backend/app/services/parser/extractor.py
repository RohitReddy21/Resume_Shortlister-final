import os
import hashlib
from typing import Tuple


try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import docx
except Exception:
    docx = None


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text_from_pdf(path: str) -> Tuple[str, dict]:
    """Extract textual content from a PDF using PyMuPDF and return metadata.

    Returns (text, metadata) where metadata contains `pages` and an optional
    `extraction_notes` field describing issues or features.
    """
    metadata = {"pages": 0, "method": "pymupdf"}
    if fitz is None:
        metadata["method"] = "pymupdf_missing"
        return "", metadata

    doc = fitz.open(path)
    text_chunks = []
    try:
        page_count = doc.page_count
        for page in doc:
            text = page.get_text("text")
            if text:
                text_chunks.append(text)
    finally:
        try:
            doc.close()
        except Exception:
            pass

    metadata["pages"] = page_count
    metadata["chars_extracted"] = sum(len(t) for t in text_chunks)
    return "\n".join(text_chunks), metadata


def extract_text_from_docx(path: str) -> Tuple[str, dict]:
    metadata = {"method": "python-docx"}
    if docx is None:
        metadata["method"] = "python-docx_missing"
        return "", metadata
    d = docx.Document(path)
    texts = [p.text for p in d.paragraphs if p.text]
    metadata["paragraphs"] = len(texts)
    metadata["chars_extracted"] = sum(len(t) for t in texts)
    return "\n".join(texts), metadata


def extract_text(path: str) -> Tuple[str, dict]:
    """Generic extractor that picks a method based on file extension.

    Returns (text, metadata). If no native text is found, returns empty text
    and metadata describing available methods so the orchestrator can decide
    whether to run OCR.
    """
    _, ext = os.path.splitext(path.lower())
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    if ext in (".docx", ".docm", ".doc"):
        return extract_text_from_docx(path)
    # attempt to read plain text files
    if ext in (".txt",):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                data = fh.read()
            return data, {"method": "plain_text", "chars_extracted": len(data)}
        except Exception:
            return "", {"method": "plain_text_failed"}

    # unsupported extension - let orchestrator perform OCR if needed
    return "", {"method": "none"}
