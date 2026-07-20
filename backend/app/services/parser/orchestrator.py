import os
import json
from typing import Dict

from .extractor import extract_text, file_hash
from .ocr import ocr_pdf, ocr_image
from .nlp import (
    extract_contact_info,
    extract_name,
    extract_name_from_filename,
    name_value_looks_suspicious,
    extract_skills,
    extract_experiences,
    extract_sections,
    extract_education,
    extract_certifications,
    extract_projects,
    extract_languages,
    extract_companies_and_designations,
    extract_salary_info,
    extract_notice_period,
)
from .openai_fallback import openai_extract


def parse_resume(path: str, use_ocr_if_needed: bool = True) -> Dict:
    """Main orchestrator that returns structured JSON for a resume file.

    Steps:
    - extract native text
    - if no text and OCR enabled, try OCR
    - run NLP extractors
    - assemble structured JSON with confidence indicators
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    text, meta = extract_text(path)
    ocr_used = False
    if (not text or len(text.strip()) < 100) and use_ocr_if_needed:
        # Try OCR fallback
        _, ext = os.path.splitext(path.lower())
        if ext == ".pdf":
            ocr_text, ocr_meta = ocr_pdf(path)
        else:
            ocr_text, ocr_meta = ocr_image(path)
        if ocr_text:
            text = ocr_text
            meta.update(ocr_meta)
            ocr_used = True

    # basic metadata
    fhash = file_hash(path)
    metadata = {"file_name": os.path.basename(path), "file_hash": fhash, "ocr_used": ocr_used}
    metadata.update(meta)

    # run NLP extractors
    contact = extract_contact_info(text)
    name = extract_name(text)
    filename_name = extract_name_from_filename(os.path.basename(path))
    if filename_name and (
        not name.get("value")
        or float(name.get("confidence") or 0) <= 0.55
        or name_value_looks_suspicious(name.get("value"))
    ):
        name = {"value": filename_name, "confidence": 0.6, "source": "filename"}
    skills = extract_skills(text)
    experiences = extract_experiences(text)
    sections = extract_sections(text)
    education = extract_education(text)
    certifications = extract_certifications(text)
    projects = extract_projects(text)
    languages = extract_languages(text)
    companies = extract_companies_and_designations(text)
    salary = extract_salary_info(text)
    notice_period = extract_notice_period(text)

    result = {
        "metadata": metadata,
        "full_name": {"value": name.get("value"), "confidence": name.get("confidence")},
        "emails": contact.get("emails", []),
        "phones": contact.get("phones", []),
        "linkedin": contact.get("linkedin"),
        "github": contact.get("github"),
        "skills": skills,
        "experiences": experiences,
        "sections": sections,
        "education": education,
        "certifications": certifications,
        "projects": projects,
        "languages": languages,
        "companies": companies,
        "current_company": None,
        "current_ctc": salary.get("current_ctc"),
        "expected_ctc": salary.get("expected_ctc"),
        "notice_period": notice_period,
        "parsed_text": text,
    }

    # Determine if OpenAI fallback is needed: missing critical fields or low confidence
    need_fallback = False
    if not result["full_name"]["value"]:
        need_fallback = True
    if not result["emails"]:
        need_fallback = True
    if not result["skills"]:
        need_fallback = True

    if need_fallback:
        try:
            oa = openai_extract(text)
            if isinstance(oa, dict):
                # Merge simple scalar/list fields if missing
                if not result["full_name"]["value"] and oa.get("full_name"):
                    result["full_name"] = {"value": oa.get("full_name"), "confidence": 0.7, "source": "openai"}
                if (not result["emails"]) and oa.get("emails"):
                    # OA may return list of emails or single
                    emails = oa.get("emails")
                    if isinstance(emails, list):
                        result["emails"] = [{"value": e, "confidence": 0.7, "source": "openai"} for e in emails]
                    else:
                        result["emails"] = [{"value": emails, "confidence": 0.7, "source": "openai"}]
                if (not result["phones"]) and oa.get("phones"):
                    phones = oa.get("phones")
                    if isinstance(phones, list):
                        result["phones"] = [{"value": p, "confidence": 0.6, "source": "openai"} for p in phones]
                    else:
                        result["phones"] = [{"value": phones, "confidence": 0.6, "source": "openai"}]
                if (not result.get("skills")) and oa.get("skills"):
                    sks = oa.get("skills")
                    if isinstance(sks, list):
                        result["skills"] = [{"name": s, "confidence": 0.65, "source": "openai"} for s in sks]
                if (not result.get("experiences")) and oa.get("experiences"):
                    exps = oa.get("experiences")
                    result["experiences"] = exps
                # Merge other helpful fields
                for fld in ("linkedin", "github", "current_company", "current_ctc", "expected_ctc", "notice_period"):
                    if not result.get(fld) and oa.get(fld):
                        result[fld] = oa.get(fld)
        except Exception:
            pass

    # try to infer current company from companies list
    if not result.get("current_company") and companies:
        # pick company with 'present' in nearby date_line if available
        for c in companies:
            dl = c.get("date_line")
            if dl and ("present" in str(dl).lower() or "current" in str(dl).lower()):
                result["current_company"] = c.get("company_line")
                break

    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <resume-file>")
        sys.exit(2)
    path = sys.argv[1]
    out = parse_resume(path)
    print(json.dumps(out, indent=2))
