from typing import Tuple

try:
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None


def ocr_image(path: str) -> Tuple[str, dict]:
    """Run OCR on an image file and return extracted text.
    If PaddleOCR not installed, returns empty string and notes.
    """
    metadata = {"ocr_engine": "paddleocr"}
    if PaddleOCR is None:
        return "", {"error": "paddleocr not installed"}
    ocr = PaddleOCR(lang='en')
    result = ocr.ocr(path, cls=True)
    lines = []
    for page in result:
        for box in page:
            lines.append(box[-1][0])
    return "\n".join(lines), metadata


def ocr_pdf(path: str) -> Tuple[str, dict]:
    # For multi-page PDFs, a proper implementation would rasterize pages to images.
    # Placeholder: not implemented here.
    return "", {"error": "ocr_pdf not implemented; rasterize pages first"}
