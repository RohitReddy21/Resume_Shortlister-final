import json
import re
import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ats import Candidate, CandidateSkill, Certification, Education, Experience, Resume, ResumeVersion, Skill
from app.services.parser.nlp import name_value_looks_suspicious
from app.services.parser.orchestrator import parse_resume
from app.services.parser.structured import build_structured_resume


MAX_TEXT_FIELD = 255


def _field_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("value") or "")
    if value is None:
        return ""
    return str(value)


def _clean_text(value: Any, max_length: int | None = None) -> str:
    text = _field_text(value).strip()
    text = re.sub(r"\s+", " ", text)
    if max_length is not None:
        return text[:max_length]
    return text


def _dict_text(item: Any, *keys: str, max_length: int | None = None) -> str:
    if isinstance(item, dict):
        for key in keys:
            value = item.get(key)
            if value:
                return _clean_text(value, max_length=max_length)
    return ""


def _iter_items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize_name(full_name: Any) -> tuple[str, str]:
    full_name = _field_text(full_name)
    if not full_name:
        return "Unknown", "Candidate"

    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _extract_primary_email(parsed: dict[str, Any]) -> str | None:
    structured = parsed.get("structured")
    if isinstance(structured, dict) and structured.get("email"):
        return _clean_text(structured.get("email"), 255)

    emails = parsed.get("emails") or []
    if isinstance(emails, list) and emails:
        first = emails[0]
        if isinstance(first, dict):
            return first.get("value")
        return first
    return None


def _extract_primary_phone(parsed: dict[str, Any]) -> str | None:
    structured = parsed.get("structured")
    if isinstance(structured, dict) and structured.get("phone"):
        return _clean_text(structured.get("phone"), 50)

    phones = parsed.get("phones") or []
    if isinstance(phones, list) and phones:
        first = phones[0]
        if isinstance(first, dict):
            return first.get("value")
        return first
    return None


def _split_title_company(value: str) -> tuple[str, str]:
    if not value:
        return "", ""

    match = re.match(r"(?P<title>.+?)\s+(?:at|@)\s+(?P<company>.+)$", value, re.IGNORECASE)
    if match:
        return _clean_text(match.group("title"), MAX_TEXT_FIELD), _clean_text(match.group("company"), MAX_TEXT_FIELD)

    parts = [part.strip() for part in re.split(r"\s+-\s+|\s+\|\s+", value, maxsplit=1) if part.strip()]
    if len(parts) == 2:
        return _clean_text(parts[0], MAX_TEXT_FIELD), _clean_text(parts[1], MAX_TEXT_FIELD)

    return _clean_text(value, MAX_TEXT_FIELD), ""


def _get_or_create_skill(db: Session, name: str) -> Skill:
    normalized = _clean_text(name, MAX_TEXT_FIELD).lower()
    skill = db.query(Skill).filter(func.lower(Skill.name) == normalized).first()
    if skill is not None:
        return skill

    skill = Skill(id=str(uuid.uuid4()), name=normalized)
    db.add(skill)
    db.flush()
    return skill


def _sync_candidate_skills(db: Session, candidate: Candidate, parsed: dict[str, Any]) -> None:
    for item in _iter_items(parsed.get("skills")):
        skill_name = _dict_text(item, "name", "skill", "value", max_length=MAX_TEXT_FIELD)
        if not skill_name and isinstance(item, str):
            skill_name = _clean_text(item, MAX_TEXT_FIELD)
        if not skill_name:
            continue

        skill = _get_or_create_skill(db, skill_name)
        existing = db.get(CandidateSkill, (candidate.id, skill.id))
        if existing is None:
            db.add(CandidateSkill(candidate_id=candidate.id, skill_id=skill.id))


def _sync_experiences(db: Session, candidate: Candidate, parsed: dict[str, Any]) -> None:
    fallback_company = _clean_text(parsed.get("current_company"), MAX_TEXT_FIELD)
    for item in _iter_items(parsed.get("experiences")):
        raw = _dict_text(item, "raw", "summary", "description")
        if not raw and isinstance(item, str):
            raw = _clean_text(item)

        title_company = _dict_text(item, "title_company", "title_line", max_length=MAX_TEXT_FIELD)
        title = _dict_text(item, "title", "designation", "role", "position", max_length=MAX_TEXT_FIELD)
        company = _dict_text(item, "company", "company_name", "organization", "employer", "company_line", max_length=MAX_TEXT_FIELD)

        if title_company and (not title or not company):
            parsed_title, parsed_company = _split_title_company(title_company)
            title = title or parsed_title
            company = company or parsed_company

        title = title or "Experience"
        company = company or fallback_company or "Unknown Company"
        description = raw or None

        exists = (
            db.query(Experience)
            .filter(
                Experience.candidate_id == candidate.id,
                Experience.title == title,
                Experience.company == company,
                Experience.description == description,
            )
            .first()
        )
        if exists is None:
            db.add(
                Experience(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate.id,
                    title=title,
                    company=company,
                    description=description,
                )
            )


def _sync_education(db: Session, candidate: Candidate, parsed: dict[str, Any]) -> None:
    for item in _iter_items(parsed.get("education")):
        raw = _dict_text(item, "raw", "description")
        if not raw and isinstance(item, str):
            raw = _clean_text(item)

        institution = _dict_text(item, "institution", "school", "university", "college", max_length=MAX_TEXT_FIELD)
        degree = _dict_text(item, "degree", "qualification", max_length=MAX_TEXT_FIELD)
        field_of_study = _dict_text(item, "field_of_study", "field", "major", max_length=MAX_TEXT_FIELD)

        if not institution:
            institution = raw[:MAX_TEXT_FIELD] if raw else "Unknown Institution"
        if not degree and raw:
            degree = raw[:MAX_TEXT_FIELD]

        exists = (
            db.query(Education)
            .filter(
                Education.candidate_id == candidate.id,
                Education.institution == institution,
                Education.degree == (degree or None),
            )
            .first()
        )
        if exists is None:
            db.add(
                Education(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate.id,
                    institution=institution,
                    degree=degree or None,
                    field_of_study=field_of_study or None,
                    description=raw or None,
                )
            )


def _sync_certifications(db: Session, candidate: Candidate, parsed: dict[str, Any]) -> None:
    for item in _iter_items(parsed.get("certifications")):
        raw = _dict_text(item, "raw", "description")
        if not raw and isinstance(item, str):
            raw = _clean_text(item)

        name = _dict_text(item, "name", "title", "certification", max_length=MAX_TEXT_FIELD)
        authority = _dict_text(item, "authority", "issuer", "organization", max_length=MAX_TEXT_FIELD)
        if not name:
            name = raw[:MAX_TEXT_FIELD] if raw else ""
        if not name:
            continue

        exists = (
            db.query(Certification)
            .filter(
                Certification.candidate_id == candidate.id,
                Certification.name == name,
                Certification.authority == (authority or None),
            )
            .first()
        )
        if exists is None:
            db.add(
                Certification(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate.id,
                    name=name,
                    authority=authority or None,
                    description=raw or None,
                )
            )


def _candidate_has_placeholder_identity(candidate: Candidate) -> bool:
    return (
        candidate.first_name == "Unknown"
        and candidate.last_name == "Candidate"
        and candidate.email.startswith("unknown+")
        and candidate.email.endswith("@resumeparser.ai")
    )


def _candidate_has_section_heading_identity(candidate: Candidate) -> bool:
    first = (candidate.first_name or "").strip().lower()
    last = (candidate.last_name or "").strip().lower()
    return (first, last) in {
        ("professional", "summary"),
        ("professional", "experience"),
        ("profile", "summary"),
        ("work", "experience"),
        ("and", "powershell"),
    }


def _candidate_has_bad_parsed_identity(candidate: Candidate) -> bool:
    full_name = " ".join(part for part in [candidate.first_name, candidate.last_name] if part)
    return name_value_looks_suspicious(full_name)


def _headline_is_bad_certification(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    after_prefix = re.sub(r"^current:\s*", "", normalized)
    if after_prefix and not after_prefix[0].isalnum():
        return True
    if normalized.startswith("current:"):
        words = re.findall(r"[a-z0-9+#.-]+", after_prefix)
        if len(words) > 6 and " at " not in normalized and "—" not in value and " - " not in value:
            return True
    if normalized.startswith(("current: certified", "current: infrastructure as code", "current: skills", "current: technical skills")):
        return True
    return bool(
        re.match(
            r"^current:\s*(specializing|specialising|proven|experienced|including|responsible|worked|working|hands[- ]on|cloud\s+and|azure\s+cloud)\b",
            normalized,
        )
    )


def _looks_like_headline_part(value: str) -> bool:
    cleaned = _clean_text(value, MAX_TEXT_FIELD)
    if not cleaned or len(cleaned) > 90:
        return False
    lowered = cleaned.lower()
    if cleaned[0].isdigit() or cleaned.startswith(("-", "*", "•", "â€¢")):
        return False
    if "%" in cleaned:
        return False
    if re.match(
        r"^(architected|automated|built|configured|deployed|developed|implemented|improved|integrated|managed|migrated|modernized|optimized|reduced|utilized|worked)\b",
        lowered,
    ):
        return False
    return True


def _sync_candidate_skills_from_structured(
    db: Session,
    candidate: Candidate,
    structured: dict[str, Any],
    replace_related: bool,
) -> None:
    if replace_related:
        db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate.id).delete(synchronize_session=False)

    for skill_name in structured.get("skills") or []:
        skill_name = _clean_text(skill_name, MAX_TEXT_FIELD)
        if not skill_name:
            continue
        skill = _get_or_create_skill(db, skill_name)
        existing = db.get(CandidateSkill, (candidate.id, skill.id))
        if existing is None:
            db.add(CandidateSkill(candidate_id=candidate.id, skill_id=skill.id))


def _sync_experiences_from_structured(
    db: Session,
    candidate: Candidate,
    structured: dict[str, Any],
    replace_related: bool,
) -> None:
    if replace_related:
        db.query(Experience).filter(Experience.candidate_id == candidate.id).delete(synchronize_session=False)

    for item in structured.get("experience") or []:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"), MAX_TEXT_FIELD)
        company = _clean_text(item.get("company"), MAX_TEXT_FIELD)
        location = _clean_text(item.get("location"), MAX_TEXT_FIELD)
        description = _clean_text(item.get("description")) or None
        if not any([title, company, location, description]):
            continue

        title = title or "Experience"
        company = company or "Unknown Company"
        exists = None
        if not replace_related:
            exists = (
                db.query(Experience)
                .filter(
                    Experience.candidate_id == candidate.id,
                    Experience.title == title,
                    Experience.company == company,
                    Experience.description == description,
                )
                .first()
            )
        if exists is None:
            db.add(
                Experience(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate.id,
                    title=title,
                    company=company,
                    location=location or None,
                    description=description,
                )
            )


def _sync_education_from_structured(
    db: Session,
    candidate: Candidate,
    structured: dict[str, Any],
    replace_related: bool,
) -> None:
    if replace_related:
        db.query(Education).filter(Education.candidate_id == candidate.id).delete(synchronize_session=False)

    for item in structured.get("education") or []:
        if not isinstance(item, dict):
            continue
        institution = _clean_text(item.get("institution"), MAX_TEXT_FIELD)
        degree = _clean_text(item.get("degree"), MAX_TEXT_FIELD)
        field = _clean_text(item.get("field") or item.get("field_of_study"), MAX_TEXT_FIELD)
        grade = _clean_text(item.get("gpa") or item.get("grade"), 50)
        description = _clean_text(item.get("description")) or None
        if not any([institution, degree, field, grade, description]):
            continue

        exists = None
        if not replace_related:
            exists = (
                db.query(Education)
                .filter(
                    Education.candidate_id == candidate.id,
                    Education.institution == (institution or "Unknown Institution"),
                    Education.degree == (degree or None),
                )
                .first()
            )
        if exists is None:
            db.add(
                Education(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate.id,
                    institution=institution or "Unknown Institution",
                    degree=degree or None,
                    field_of_study=field or None,
                    grade=grade or None,
                    description=description,
                )
            )


def _sync_certifications_from_structured(
    db: Session,
    candidate: Candidate,
    structured: dict[str, Any],
    replace_related: bool,
) -> None:
    if replace_related:
        db.query(Certification).filter(Certification.candidate_id == candidate.id).delete(synchronize_session=False)

    for cert_name in structured.get("certifications") or []:
        name = _clean_text(cert_name, MAX_TEXT_FIELD)
        if not name:
            continue
        exists = None
        if not replace_related:
            exists = (
                db.query(Certification)
                .filter(Certification.candidate_id == candidate.id, Certification.name == name)
                .first()
            )
        if exists is None:
            db.add(Certification(id=str(uuid.uuid4()), candidate_id=candidate.id, name=name))


def _sync_candidate_profile_from_structured(
    db: Session,
    candidate: Candidate,
    structured: dict[str, Any],
    replace_related: bool = False,
    force_identity: bool = False,
) -> None:
    name = _clean_text(structured.get("name"), MAX_TEXT_FIELD)
    if name and (
        force_identity
        or _candidate_has_placeholder_identity(candidate)
        or _candidate_has_section_heading_identity(candidate)
        or _candidate_has_bad_parsed_identity(candidate)
        or not candidate.first_name
    ):
        first_name, last_name = _normalize_name(name)
        candidate.first_name = first_name[:100] or candidate.first_name
        candidate.last_name = last_name[:100]

    email = _clean_text(structured.get("email"), 255)
    if email and (force_identity or candidate.email.startswith("unknown+")):
        candidate.email = email[:255]

    phone = _clean_text(structured.get("phone"), 50)
    if phone and (force_identity or not candidate.phone):
        candidate.phone = phone[:50]

    summary = _clean_text(structured.get("summary"))
    if summary and (force_identity or not candidate.summary):
        candidate.summary = summary

    headline = ""
    for item in structured.get("experience") or []:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"), 120)
        company = _clean_text(item.get("company"), 120)
        if title and not _looks_like_headline_part(title):
            title = ""
        if company and not _looks_like_headline_part(company):
            company = ""
        if title or company:
            headline = " at ".join(part for part in [title, company] if part)
            break
    if headline and (force_identity or not candidate.headline or _headline_is_bad_certification(candidate.headline)):
        candidate.headline = headline[:MAX_TEXT_FIELD]

    db.add(candidate)
    _sync_candidate_skills_from_structured(db, candidate, structured, replace_related)
    _sync_experiences_from_structured(db, candidate, structured, replace_related)
    _sync_education_from_structured(db, candidate, structured, replace_related)
    _sync_certifications_from_structured(db, candidate, structured, replace_related)


def _sync_candidate_profile(db: Session, candidate: Candidate, parsed: dict[str, Any]) -> None:
    current_company = _clean_text(parsed.get("current_company"), MAX_TEXT_FIELD)
    current_package = _clean_text(parsed.get("current_ctc"), 100)
    expected_package = _clean_text(parsed.get("expected_ctc"), 100)
    notice_period = _clean_text(parsed.get("notice_period"), 100)

    if current_company and (not candidate.headline or _headline_is_bad_certification(candidate.headline)):
        candidate.headline = f"Current: {current_company}"[:MAX_TEXT_FIELD]
        db.add(candidate)

    structured = build_structured_resume(parsed)
    parsed["structured"] = structured
    _sync_candidate_profile_from_structured(db, candidate, structured)
    if _headline_is_bad_certification(candidate.headline) or (
        candidate.headline and not _looks_like_headline_part(candidate.headline)
    ):
        candidate.headline = None
        db.add(candidate)

    if current_package and not candidate.current_package:
        candidate.current_package = current_package
        db.add(candidate)
    if expected_package and not candidate.expected_package:
        candidate.expected_package = expected_package
        db.add(candidate)
    if notice_period and not candidate.notice_period:
        candidate.notice_period = notice_period
        db.add(candidate)

    if not structured.get("skills"):
        _sync_candidate_skills(db, candidate, parsed)
    if not structured.get("experience"):
        _sync_experiences(db, candidate, parsed)
    if not structured.get("education"):
        _sync_education(db, candidate, parsed)
    if not structured.get("certifications"):
        _sync_certifications(db, candidate, parsed)


def _find_or_create_candidate(db: Session, parsed: dict[str, Any], candidate_id: str | None = None) -> Candidate:
    candidate = None
    if candidate_id:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

    if candidate is None:
        primary_email = _extract_primary_email(parsed)
        if primary_email:
            candidate = db.query(Candidate).filter(Candidate.email == primary_email).first()

    if candidate is None:
        structured = parsed.get("structured") if isinstance(parsed.get("structured"), dict) else {}
        full_name = _field_text(parsed.get("full_name")) or _clean_text(structured.get("name"))
        first_name, last_name = _normalize_name(full_name)
        email = _extract_primary_email(parsed) or f"unknown+{uuid.uuid4().hex}@resumeparser.ai"

        candidate = Candidate(
            id=str(uuid.uuid4()),
            first_name=first_name[:100] or "Unknown",
            last_name=last_name[:100] or "Candidate",
            email=email[:255],
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    # Update candidate with better parsed info if the candidate record is placeholder or incomplete.
    changed = False
    structured = parsed.get("structured") if isinstance(parsed.get("structured"), dict) else {}
    parsed_name = _field_text(parsed.get("full_name")) or _clean_text(structured.get("name"))
    if parsed_name and (
        (candidate.first_name == "Unknown" and candidate.last_name == "Candidate")
        or candidate.last_name == "Candidate"
        or _candidate_has_section_heading_identity(candidate)
        or _candidate_has_bad_parsed_identity(candidate)
    ):
        first_name, last_name = _normalize_name(parsed_name)
        candidate.first_name = first_name[:100] or candidate.first_name
        candidate.last_name = last_name[:100] or candidate.last_name
        changed = True

    parsed_phone = _extract_primary_phone(parsed)
    if parsed_phone and not candidate.phone:
        candidate.phone = parsed_phone[:50]
        changed = True

    parsed_email = _extract_primary_email(parsed)
    if parsed_email and candidate.email.startswith("unknown+"):
        existing = db.query(Candidate).filter(Candidate.email == parsed_email).first()
        if existing is not None:
            candidate = existing
        else:
            candidate.email = parsed_email[:255]
            changed = True

    if changed:
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    return candidate


def _create_version(db: Session, resume: Resume, parsed: dict[str, Any]) -> ResumeVersion:
    version_number = db.query(ResumeVersion).filter(ResumeVersion.resume_id == resume.id).count() + 1
    content = parsed.get("parsed_text") or ""
    parsed_json = json.dumps(parsed, ensure_ascii=False)

    version = ResumeVersion(
        id=str(uuid.uuid4()),
        resume_id=resume.id,
        version_number=version_number,
        content=content,
        parsed_json=parsed_json,
    )
    db.add(version)
    db.flush()
    resume.current_version_id = version.id
    db.add(resume)
    db.commit()
    db.refresh(version)
    return version


def parse_resume_task(resume_id: str, candidate_id: str | None, file_path: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        resume = db.get(Resume, resume_id)
        if resume is None:
            raise ValueError(f"Resume {resume_id} not found")

        parsed = parse_resume(file_path)
        parsed["structured"] = build_structured_resume(parsed)
        candidate = _find_or_create_candidate(db, parsed, candidate_id)

        if resume.candidate_id != candidate.id:
            resume.candidate_id = candidate.id
            db.add(resume)
            db.commit()
            db.refresh(resume)

        _sync_candidate_profile(db, candidate, parsed)
        version = _create_version(db, resume, parsed)
        return {"resume_id": resume.id, "version_id": version.id, "status": "completed"}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
