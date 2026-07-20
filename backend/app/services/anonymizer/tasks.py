import os
import uuid
from typing import Dict

from celery_app import celery
from app.core.database import SessionLocal
from app.core.paths import get_resume_dir
from app.models.ats import Resume, ResumeVersion
from app.services.anonymizer import (
    generate_masked_candidate_id,
    mask_text_in_pdf,
    mask_text_in_docx,
    mask_images_in_pdf,
    mask_images_in_docx,
)

RESUME_DIR = get_resume_dir()


def _find_resume_file(resume_id: str) -> str | None:
    if not os.path.isdir(RESUME_DIR):
        return None
    for fn in os.listdir(RESUME_DIR):
        if fn.startswith(resume_id):
            return os.path.join(RESUME_DIR, fn)
    return None


@celery.task(name="anonymizer.anonymize_resume_task")
def anonymize_resume_task(resume_id: str, mask_policy: Dict) -> Dict:
    db = SessionLocal()
    try:
        resume = db.get(Resume, resume_id)
        if resume is None:
            raise ValueError("resume not found")

        src = _find_resume_file(resume_id)
        if src is None:
            raise ValueError("source file not found on disk")

        masked_id = generate_masked_candidate_id(resume.candidate_id or resume_id)
        base = os.path.splitext(src)[0]
        masked_pdf = base + ".masked.pdf"
        masked_docx = base + ".masked.docx"

        # collect mask terms from parsed JSON if available (best-effort)
        parsed_json = None
        try:
            if os.path.exists(src + ".parsed.json"):
                import json

                with open(src + ".parsed.json", "r", encoding="utf-8") as fh:
                    parsed_json = json.load(fh)
        except Exception:
            parsed_json = None

        mask_terms = []
        pseudo_map = {}
        if parsed_json:
            # gather common PII
            name = parsed_json.get("full_name", {}).get("value")
            if name:
                mask_terms.append(name)
                pseudo_map[name] = f"CAND-{masked_id[:8]}"
            emails = parsed_json.get("emails") or []
            for e in emails:
                val = e.get("value") if isinstance(e, dict) else e
                if val:
                    mask_terms.append(val)
            phones = parsed_json.get("phones") or []
            for p in phones:
                val = p.get("value") if isinstance(p, dict) else p
                if val:
                    mask_terms.append(val)

        # perform masking for supported formats
        _, ext = os.path.splitext(src.lower())
        image_remove = mask_policy.get("image_remove", False)
        image_blur_radius = mask_policy.get("image_blur_radius", 12) if mask_policy.get("image_blur", True) else None

        if ext == ".pdf":
            mask_text_in_pdf(src, masked_pdf, mask_terms, pseudo_map if mask_policy.get("pseudonymize", True) else None)
            # post-process images in the masked PDF
            if image_remove or image_blur_radius is not None:
                mask_images_in_pdf(masked_pdf, masked_pdf, remove=image_remove, blur_radius=image_blur_radius)
        elif ext in (".docx", ".doc"):
            mask_text_in_docx(src, masked_docx, mask_terms, pseudo_map if mask_policy.get("pseudonymize", True) else None)
            if image_remove or image_blur_radius is not None:
                mask_images_in_docx(masked_docx, masked_docx, remove=image_remove, blur_radius=image_blur_radius)
        else:
            raise ValueError("unsupported file type for masking")

        # persist masked metadata to the current resume version if present
        try:
            if resume.current_version_id:
                version = db.get(ResumeVersion, resume.current_version_id)
                if version:
                    import json
                    from datetime import datetime

                    version.masked_candidate_id = masked_id
                    version.mask_policy = json.dumps(mask_policy, ensure_ascii=False)
                    version.masked_pdf = masked_pdf if os.path.exists(masked_pdf) else None
                    version.masked_docx = masked_docx if os.path.exists(masked_docx) else None
                    version.masked_at = datetime.utcnow()
                    db.add(version)
                    db.commit()
                    db.refresh(version)
        except Exception:
            db.rollback()

        return {"resume_id": resume_id, "masked_candidate_id": masked_id, "masked_pdf": masked_pdf, "masked_docx": masked_docx}
    finally:
        db.close()
