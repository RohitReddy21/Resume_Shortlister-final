import os
import hmac
import hashlib
import io
import zipfile
from typing import List, Dict

from PIL import Image, ImageFilter

from app.core.config import get_settings

settings = get_settings()


def generate_masked_candidate_id(original_candidate_id: str) -> str:
    """Deterministic masked ID using HMAC with the app secret key."""
    key = settings.secret_key.encode("utf-8")
    hm = hmac.new(key, original_candidate_id.encode("utf-8"), hashlib.sha256)
    return hm.hexdigest()


def _ensure_out_dir(path: str) -> None:
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)


def mask_text_in_docx(src_path: str, dest_path: str, mask_terms: List[str], pseudonym_map: Dict[str, str] | None = None) -> None:
    try:
        import docx
    except Exception:
        raise RuntimeError("python-docx is required for DOCX masking")

    doc = docx.Document(src_path)
    for para in doc.paragraphs:
        for run in para.runs:
            txt = run.text
            if not txt:
                continue
            new = txt
            for term in mask_terms:
                if term and term in new:
                    if pseudonym_map and term in pseudonym_map:
                        new = new.replace(term, pseudonym_map[term])
                    else:
                        new = new.replace(term, "[REDACTED]")
            if new != txt:
                run.text = new

    # remove images if requested by caller: python-docx keeps pictures in part; easiest is to remove all inline shapes
    # Note: python-docx does not provide a public API to remove images; skip advanced removal here.

    _ensure_out_dir(dest_path)
    doc.save(dest_path)


def mask_text_in_pdf(src_path: str, dest_path: str, mask_terms: List[str], pseudonym_map: Dict[str, str] | None = None) -> None:
    try:
        import fitz
    except Exception:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF masking")

    doc = fitz.open(src_path)
    for page in doc:
        for term in mask_terms:
            if not term:
                continue
            areas = page.search_for(term)
            for r in areas:
                page.add_redact_annot(r, fill=(0, 0, 0))
        # also handle pseudonym replacements: search and replace text by redaction then overlay text
        if pseudonym_map:
            for orig, pseudo in pseudonym_map.items():
                areas = page.search_for(orig)
                for r in areas:
                    page.add_redact_annot(r, fill=(0, 0, 0))
                    # after redaction we will overlay the pseudonym at the rect
                    page.insert_textbox(r, pseudo, fontsize=10, color=(1, 1, 1))

    doc.save(dest_path, garbage=4, deflate=True)
    doc.close()


def _blur_image_bytes(img_bytes: bytes, radius: int = 12) -> bytes:
    """Return blurred image bytes preserving original format."""
    try:
        im = Image.open(io.BytesIO(img_bytes))
    except Exception:
        return img_bytes
    # convert to RGBA to keep alpha if present
    mode = im.mode
    if mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGBA")
    blurred = im.filter(ImageFilter.GaussianBlur(radius=radius))
    out = io.BytesIO()
    fmt = im.format if getattr(im, "format", None) else "PNG"
    blurred.save(out, format=fmt)
    return out.getvalue()


def mask_images_in_pdf(src_path: str, dest_path: str, remove: bool = False, blur_radius: int | None = 12) -> None:
    """Mask or blur embedded images in a PDF.

    - If `remove` is True, images are redacted (replaced with black boxes).
    - If `blur_radius` is set, images are extracted, blurred, and replaced.
    """
    try:
        import fitz
    except Exception:
        raise RuntimeError("PyMuPDF (fitz) is required for PDF image masking")

    doc = fitz.open(src_path)
    for page in doc:
        imgs = page.get_images(full=True)
        if not imgs:
            continue
        # iterate unique xref ids
        xrefs = {img[0] for img in imgs}
        for xref in xrefs:
            try:
                imgdict = doc.extract_image(xref)
            except Exception:
                continue
            img_bytes = imgdict.get("image")
            rects = page.search_for(imgdict.get("name", "")) if False else []
            if remove:
                # redact all occurrences of the image by searching by bbox of image xref
                try:
                    page.add_redact_annot(page.rect, fill=(0, 0, 0))
                except Exception:
                    pass
            elif blur_radius is not None and img_bytes:
                try:
                    new_bytes = _blur_image_bytes(img_bytes, radius=blur_radius)
                    # update the image stream in the PDF
                    try:
                        doc.update_image(xref, new_bytes)
                    except Exception:
                        # fallback: insert blurred image as a filled rectangle overlay
                        pix = fitz.Pixmap(fitz.open("pdf", new_bytes))
                        page.insert_image(page.rect, pixmap=pix)
                except Exception:
                    pass

    doc.save(dest_path, garbage=4, deflate=True)
    doc.close()


def mask_images_in_docx(src_path: str, dest_path: str, remove: bool = False, blur_radius: int | None = 12) -> None:
    """Mask or blur images inside a DOCX by replacing media files inside the package.

    This rewrites `word/media/*` entries in the DOCX ZIP archive.
    If `remove` is True, images are replaced with a small placeholder PNG.
    If `blur_radius` is set, images are blurred with PIL.
    """
    if not zipfile.is_zipfile(src_path):
        raise RuntimeError("DOCX must be a zip package")

    with zipfile.ZipFile(src_path, "r") as zin:
        with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("word/media/") and (item.filename.lower().endswith(('.png', '.jpg', '.jpeg'))):
                    if remove:
                        # write a 1x1 transparent PNG as placeholder
                        im = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
                        buf = io.BytesIO()
                        im.save(buf, format="PNG")
                        zout.writestr(item, buf.getvalue())
                    elif blur_radius is not None:
                        try:
                            new_bytes = _blur_image_bytes(data, radius=blur_radius)
                            zout.writestr(item, new_bytes)
                        except Exception:
                            zout.writestr(item, data)
                    else:
                        zout.writestr(item, data)
                else:
                    zout.writestr(item, data)

