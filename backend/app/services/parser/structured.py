import re
from copy import deepcopy
from typing import Any


STRUCTURED_RESUME_TEMPLATE: dict[str, Any] = {
    "name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "summary": "",
    "skills": [],
    "experience": [],
    "education": [],
    "certifications": [],
}

_MONTHS = {
    "jan": "Jan",
    "january": "Jan",
    "feb": "Feb",
    "february": "Feb",
    "mar": "Mar",
    "march": "Mar",
    "apr": "Apr",
    "april": "Apr",
    "may": "May",
    "jun": "Jun",
    "june": "Jun",
    "jul": "Jul",
    "july": "Jul",
    "aug": "Aug",
    "august": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "september": "Sep",
    "oct": "Oct",
    "october": "Oct",
    "nov": "Nov",
    "november": "Nov",
    "dec": "Dec",
    "december": "Dec",
}

_SECTION_ALIASES = {
    "summary": {
        "summary",
        "professional summary",
        "profile summary",
        "career summary",
        "career objective",
        "objective",
        "about me",
    },
    "skills": {
        "skills",
        "technical skills",
        "key skills",
        "core skills",
        "technical competencies",
        "tools and technologies",
        "technologies",
        "software tools",
        "software and tools",
        "software & tools",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "career experience",
        "internship experience",
    },
    "education": {
        "education",
        "academic qualification",
        "academic qualifications",
        "academics",
        "educational qualification",
        "educational qualifications",
    },
    "certifications": {
        "certifications",
        "certification",
        "certificates",
        "courses and certifications",
        "certifications and courses",
        "training and certifications",
    },
}

_ALL_ALIASES = {alias: key for key, aliases in _SECTION_ALIASES.items() for alias in aliases}
_COMPACT_ALIASES = {re.sub(r"[^a-z0-9]+", "", alias): key for alias, key in _ALL_ALIASES.items()}
_DATE_TOKEN_PATTERN = (
    r"(?:(?:(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\.?\s*|(?:0?[1-9]|1[0-2])[/.-]\s*)?(?:19|20)\d{2})"
)
_DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_TOKEN_PATTERN})"
    r"\s*(?:-|to|\u2013|\u2014)\s*"
    rf"(?P<end>present|current|now|{_DATE_TOKEN_PATTERN})",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", re.IGNORECASE)
_GPA_RE = re.compile(r"\b(?:gpa|cgpa)\s*[:\-]?\s*([0-9](?:\.[0-9]+)?(?:\s*/\s*(?:10|4(?:\.0)?|100))?)", re.IGNORECASE)
_DEGREE_RE = re.compile(
    r"\b(bachelor|master|b\.?\s*tech|m\.?\s*tech|b\.?\s*sc|m\.?\s*sc|bca|mca|mba|ph\.?\s*d|degree|diploma|intermediate|ssc|hsc)\b",
    re.IGNORECASE,
)
_INSTITUTION_RE = re.compile(r"\b(university|college|school|institute|academy|engineering)\b", re.IGNORECASE)
_FALSE_CERT_RE = re.compile(
    r"\b(secondary school certificate|bachelor|master|intermediate|degree college|university|college|school|ssc|hsc)\b",
    re.IGNORECASE,
)
_ACTION_START_RE = re.compile(
    r"^(led|drove|maintained|handled|contributed|managed|monitored|analyze|analyzed|analysed|investigate|investigated|created|create|collaborated|ensure|ensured|assisted|documented|reviewed|performed|installed|integrated|resolved|supported|prepared|improved)\b",
    re.IGNORECASE,
)
_ROLE_RE = re.compile(
    r"\b(analyst|engineer|developer|manager|lead|intern|associate|consultant|specialist|administrator|recruiter|operations|operation|human resource|soc|qa|tester)\b",
    re.IGNORECASE,
)
_CONTACT_LABELS = {"contact", "phone", "email", "location", "address", "linkdin", "linkedin"}
_SKILL_FRAGMENT_BLOCKLIST = {
    "and",
    "urls",
    "attachments",
    "endpoints",
    "servers",
    "positions",
    "diligence",
    "discrepancies",
    "mis reports",
    "oneisok",
    "supplements",
    "order",
    "processing",
    "inventory",
    "customer",
}


def build_structured_resume(parsed: dict[str, Any] | None) -> dict[str, Any]:
    """Return resume data in the exact JSON object shape used by the recruiter table."""
    parsed = parsed or {}
    existing = _existing_structured_resume(parsed.get("structured"))
    if existing is not None:
        return existing

    structured = deepcopy(STRUCTURED_RESUME_TEMPLATE)
    raw_text = _raw_text(parsed.get("parsed_text"))
    sections = _extract_sections(raw_text)

    structured["name"] = _text(parsed.get("full_name"))
    structured["email"] = _first_list_value(parsed.get("emails"))
    structured["phone"] = _first_list_value(parsed.get("phones"))
    structured["location"] = _extract_location(parsed, raw_text)
    structured["linkedin"] = _extract_linkedin(parsed, raw_text)
    structured["summary"] = _extract_summary(parsed, sections, raw_text)
    structured["skills"] = _extract_skills(parsed, sections)
    structured["experience"] = _extract_experience(parsed, sections)
    structured["education"] = _extract_education(parsed, sections)
    structured["certifications"] = _extract_certifications(parsed, sections)
    return structured


def _existing_structured_resume(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    structured = deepcopy(STRUCTURED_RESUME_TEMPLATE)
    for key in ("name", "email", "phone", "location", "linkedin", "summary"):
        structured[key] = _text(value.get(key))

    structured["skills"] = _unique([_text(item) for item in value.get("skills") or []])
    structured["experience"] = [_structured_experience(item) for item in value.get("experience") or [] if isinstance(item, dict)]
    structured["education"] = [_structured_education(item) for item in value.get("education") or [] if isinstance(item, dict)]
    structured["certifications"] = _unique([_text(item) for item in value.get("certifications") or []])
    return structured


def _structured_experience(item: dict[str, Any]) -> dict[str, str]:
    return {
        "company": _text(item.get("company")),
        "title": _text(item.get("title")),
        "start_date": _normalize_date_token(_text(item.get("start_date"))),
        "end_date": _normalize_date_token(_text(item.get("end_date"))),
        "location": _text(item.get("location")),
        "description": _condense_description(_text(item.get("description"))),
    }


def _structured_education(item: dict[str, Any]) -> dict[str, str]:
    return {
        "institution": _text(item.get("institution")),
        "degree": _text(item.get("degree")),
        "field": _text(item.get("field") or item.get("field_of_study")),
        "graduation_date": _normalize_date_token(_text(item.get("graduation_date"))),
        "gpa": _text(item.get("gpa") or item.get("grade")),
    }


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return _text(value.get("value") or value.get("name") or value.get("raw"))
    if value is None:
        return ""
    return _clean(str(value))


def _raw_text(value: Any) -> str:
    if isinstance(value, dict):
        return _raw_text(value.get("value") or value.get("raw"))
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n:-|")


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n:-|\u2022")


def _first_list_value(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    for item in value:
        candidate = _text(item)
        if candidate:
            return candidate
    return ""


def _field(item: Any, *keys: str) -> str:
    if not isinstance(item, dict):
        return _text(item)
    for key in keys:
        value = _text(item.get(key))
        if value:
            return value
    return ""


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = _clean(value)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _heading_key(line: str) -> tuple[str | None, str]:
    cleaned = _clean_line(line)
    if not cleaned:
        return None, ""

    match = re.match(r"^(?P<label>[A-Za-z &/]+?)\s*[:\-]\s*(?P<body>.+)$", cleaned)
    if match:
        label = re.sub(r"[^a-z0-9 ]+", " ", match.group("label").lower())
        label = re.sub(r"\s+", " ", label).strip()
        if label in _ALL_ALIASES:
            return _ALL_ALIASES[label], match.group("body").strip()

    normalized = re.sub(r"[^a-z0-9 ]+", " ", cleaned.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    key = _ALL_ALIASES.get(normalized)
    if key:
        return key, ""

    compact = re.sub(r"[^a-z0-9]+", "", cleaned.lower())
    return _COMPACT_ALIASES.get(compact), ""


def _extract_sections(raw_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {key: [] for key in _SECTION_ALIASES}
    current: str | None = None

    for line in raw_text.splitlines():
        key, inline_body = _heading_key(line)
        if key:
            current = key
            if inline_body:
                sections[current].append(inline_body)
            continue
        if current:
            sections[current].append(line)

    return {key: "\n".join(lines).strip() for key, lines in sections.items() if "\n".join(lines).strip()}


def _clean_location_text(value: str) -> str:
    cleaned = _clean(value)
    cleaned = re.sub(r"^[^A-Za-z0-9]+", "", cleaned)
    return cleaned.strip(" ,;|")


def _looks_like_location_candidate(value: str) -> bool:
    cleaned = _clean_location_text(value)
    if not cleaned:
        return False
    if _heading_key(cleaned)[0] or cleaned.lower() in _CONTACT_LABELS:
        return False
    compact = re.sub(r"[^a-z0-9]+", "", cleaned.lower())
    if compact in _COMPACT_ALIASES:
        return False
    if "@" in cleaned or _LINKEDIN_RE.search(cleaned) or _looks_like_date(cleaned):
        return False
    return bool(re.search(r"[A-Za-z]", cleaned))


def _extract_location(parsed: dict[str, Any], raw_text: str) -> str:
    explicit = _text(parsed.get("location"))
    if explicit:
        return _clean_location_text(explicit)

    lines = raw_text.splitlines()
    for index, line in enumerate(lines[:30]):
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if cleaned.lower() == "location" and index + 1 < len(lines):
            next_line = _clean_line(lines[index + 1])
            if _looks_like_location_candidate(next_line):
                return _clean_location_text(next_line)
        label_match = re.search(r"\blocation\s*[:\-]\s*(.+)$", cleaned, re.IGNORECASE)
        if label_match and _looks_like_location_candidate(label_match.group(1)):
            return _clean_location_text(label_match.group(1))
        address_match = re.search(r"\baddress\s*[:\-]\s*(.+)$", cleaned, re.IGNORECASE)
        if address_match and _looks_like_location_candidate(address_match.group(1)):
            return _clean_location_text(address_match.group(1))

        if "@" in cleaned or re.search(r"\d{5,}", cleaned):
            found_inline = ""
            for part in re.split(r"\s*[|;]\s*", cleaned):
                raw_part = _clean(part)
                if not raw_part or "@" in raw_part or _LINKEDIN_RE.search(raw_part) or re.search(r"\d{5,}", raw_part):
                    continue
                part = _clean_location_text(raw_part)
                if _looks_like_location_candidate(part) and len(part) <= 80:
                    found_inline = part
                    break
            if found_inline:
                return found_inline

            address_parts: list[str] = []
            if "@" not in cleaned:
                continue
            for candidate_line in lines[index + 1 : index + 3]:
                candidate = _clean_line(candidate_line)
                if not candidate or candidate.startswith(".") or "@" in candidate or _LINKEDIN_RE.search(candidate) or _looks_like_date(candidate):
                    break
                if not _looks_like_location_candidate(candidate) or len(candidate) > 80:
                    break
                address_parts.append(_clean_location_text(candidate))
            if address_parts:
                return ", ".join(address_parts)

        if "," in cleaned and "@" not in cleaned and not _LINKEDIN_RE.search(cleaned) and not re.search(r"\d{5,}", cleaned):
            candidate = _clean_location_text(cleaned)
            if "," not in candidate:
                continue
            left, right = [part.strip() for part in candidate.split(",", 1)]
            if (
                _looks_like_location_candidate(candidate)
                and re.fullmatch(r"[A-Za-z .'-]+,\s*[A-Za-z .'-]+", candidate)
                and len(left.split()) <= 3
                and len(right.split()) <= 3
            ):
                return candidate
    return ""


def _extract_linkedin(parsed: dict[str, Any], raw_text: str) -> str:
    explicit = _text(parsed.get("linkedin"))
    if explicit:
        return explicit
    match = _LINKEDIN_RE.search(raw_text)
    return match.group(0) if match else ""


def _extract_summary(parsed: dict[str, Any], sections: dict[str, str], raw_text: str) -> str:
    explicit = _text(parsed.get("summary"))
    if explicit:
        return explicit
    summary = _clean(sections.get("summary", ""))
    if not summary:
        summary = _extract_top_summary(raw_text)
    if len(summary) > 900:
        summary = summary[:900].rsplit(" ", 1)[0].rstrip(".,;") + "."
    return summary


def _extract_top_summary(raw_text: str) -> str:
    lines = [_clean_line(line) for line in raw_text.splitlines()[:35]]
    candidates: list[str] = []
    started = False
    for line in lines:
        if not line:
            if started:
                break
            continue
        if _heading_key(line)[0]:
            if started:
                break
            continue
        if "@" in line or _LINKEDIN_RE.search(line) or re.fullmatch(r"\+?\d[\d\s().-]{7,}", line):
            continue
        if not started and (
            len(line.split()) <= 4
            or "," in line
            or (re.search(r"\d", line) and not re.search(r"\b(years?|experience|specialist|professional|engineer|analyst|manager)\b", line, re.IGNORECASE))
        ):
            continue
        started = True
        candidates.append(line)
        if len(" ".join(candidates)) > 500:
            break

    summary = _clean(" ".join(candidates))
    if len(summary) >= 80:
        return summary

    paragraphs = [_clean(part) for part in re.split(r"\n\s*\n", raw_text) if _clean(part)]
    for paragraph in paragraphs:
        if len(paragraph) >= 140 and "." in paragraph and "\u2022" not in paragraph:
            return paragraph
    return ""


def _split_skill_text(value: str) -> list[str]:
    raw_lines = [_clean_line(line) for line in value.splitlines() if _clean_line(line)]
    lines: list[str] = []
    for line in raw_lines:
        if lines and (lines[-1].endswith("&") or (lines[-1].lower() == "windows" and re.match(r"^\d", line))):
            lines[-1] = f"{lines[-1]} {line}"
        else:
            lines.append(line)

    items: list[str] = []
    for line in lines:
        if _heading_key(line)[0]:
            continue
        if ":" in line:
            label, body = line.split(":", 1)
            if _looks_like_skill_item(label):
                items.append(label)
            line = body
        items.extend(re.split(r",|;|\||\u2022|\t", line))
    return [_clean(item) for item in items if _looks_like_skill_item(item)]


def _looks_like_skill_item(value: str) -> bool:
    item = _clean(value)
    if not item or len(item) > 80:
        return False
    if _LINKEDIN_RE.search(item) or "www." in item.lower() or ".com" in item.lower():
        return False
    if len(re.findall(r"\d", item)) >= 4:
        return False
    if re.fullmatch(r"\d+", item):
        return False
    if item.endswith(".") or _ACTION_START_RE.search(item):
        return False
    lower = item.lower()
    if lower in _SKILL_FRAGMENT_BLOCKLIST or lower.startswith("and "):
        return False
    words = re.findall(r"[A-Za-z0-9+#./&-]+", item)
    if len(words) > 7:
        return False
    if len(words) > 1 and item[0].islower():
        return False
    return bool(re.search(r"[A-Za-z+#]", item))


def _extract_skills(parsed: dict[str, Any], sections: dict[str, str]) -> list[str]:
    values: list[str] = []
    parsed_name = _text(parsed.get("full_name")).lower()
    for item in parsed.get("skills") or []:
        values.append(_field(item, "name", "skill", "value", "raw"))
    if sections.get("skills"):
        values.extend(_split_skill_text(sections["skills"]))
    return [value for value in _unique(values) if value.lower() != parsed_name]


def _normalize_date_token(value: str) -> str:
    token = _clean(value).replace(".", "")
    if not token:
        return ""
    lower = token.lower()
    if lower in {"present", "current", "now"}:
        return "Present"

    month_year = re.search(
        r"\b(?P<month>jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\.?\s*(?P<year>(?:19|20)\d{2})\b",
        token,
        re.IGNORECASE,
    )
    if month_year:
        return f"{_MONTHS[month_year.group('month').lower()]} {month_year.group('year')}"

    numeric_month_year = re.search(r"\b(?P<month>0?[1-9]|1[0-2])[/.-]\s*(?P<year>(?:19|20)\d{2})\b", token)
    if numeric_month_year:
        month = int(numeric_month_year.group("month"))
        month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month - 1]
        return f"{month_name} {numeric_month_year.group('year')}"

    year = _YEAR_RE.search(token)
    return year.group(0) if year else token


def _date_range(value: str) -> tuple[str, str]:
    match = _DATE_RANGE_RE.search(value)
    if match:
        return _normalize_date_token(match.group("start")), _normalize_date_token(match.group("end"))
    single_year = _YEAR_RE.search(value)
    if single_year:
        return "", _normalize_date_token(single_year.group(0))
    return "", ""


def _looks_like_date(value: str) -> bool:
    return bool(_DATE_RANGE_RE.search(value) or _YEAR_RE.search(value))


def _is_date_only(value: str) -> bool:
    cleaned = _clean(value)
    if not cleaned:
        return False
    return bool(_DATE_RANGE_RE.fullmatch(cleaned) or _YEAR_RE.fullmatch(cleaned))


def _split_title_company(value: str) -> tuple[str, str]:
    cleaned = _clean(value)
    if not cleaned:
        return "", ""
    match = re.match(r"(?P<title>.+?)\s+(?:at|@)\s+(?P<company>.+)$", cleaned, re.IGNORECASE)
    if match:
        return _clean(match.group("title")), _clean(match.group("company"))
    parts = [part.strip() for part in re.split(r"\s+-\s+|\s+\|\s+", cleaned, maxsplit=1) if part.strip()]
    if len(parts) == 2:
        return parts[0], parts[1]
    return cleaned, ""


def _experience_from_item(item: Any) -> dict[str, str] | None:
    raw = _field(item, "raw", "summary", "description")
    title_company = _field(item, "title_company", "title_line")
    title = _field(item, "title", "designation", "role", "position")
    company = _field(item, "company", "company_name", "organization", "employer", "company_line")
    location = _field(item, "location")
    start_date = _field(item, "start_date", "start")
    end_date = _field(item, "end_date", "end")

    if title_company and (not title or not company):
        parsed_title, parsed_company = _split_title_company(title_company)
        title = title or parsed_title
        company = company or parsed_company

    if not start_date and not end_date and raw:
        start_date, end_date = _date_range(raw)

    text_for_filter = f"{title_company} {title} {company} {raw}"
    if _DEGREE_RE.search(text_for_filter):
        return None
    if _looks_like_date(title) or _looks_like_date(company):
        return None
    if title.endswith("."):
        return None
    raw_was_date_only = _is_date_only(raw)
    if _is_date_only(raw):
        raw = ""

    if raw_was_date_only and not (title or company):
        return None
    if not any([raw, title, company, start_date, end_date]):
        return None

    return {
        "company": company,
        "title": title,
        "start_date": _normalize_date_token(start_date),
        "end_date": _normalize_date_token(end_date),
        "location": location,
        "description": _condense_description(raw),
    }


def _extract_experience(parsed: dict[str, Any], sections: dict[str, str]) -> list[dict[str, str]]:
    section_text = sections.get("experience", "")
    if section_text:
        section_rows = _parse_experience_section(section_text)
        if section_rows:
            return section_rows

    rows: list[dict[str, str]] = []
    for item in parsed.get("experiences") or []:
        row = _experience_from_item(item)
        if row:
            rows.append(row)
    return rows


def _parse_experience_section(value: str) -> list[dict[str, str]]:
    lines = [_clean_line(line) for line in value.splitlines() if _clean_line(line)]
    rows: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        if not _looks_like_date(line):
            continue

        start_date, end_date = _date_range(line)
        title = ""
        company = ""
        location = ""
        description_start = index + 1
        inline_title = _clean(_DATE_RANGE_RE.sub("", line).strip(" ,:-"))
        if inline_title and not _looks_like_date(inline_title):
            title = inline_title
            if index + 1 < len(lines):
                next_line = lines[index + 1]
                if not _looks_like_date(next_line) and not _heading_key(next_line)[0] and next_line != "\u2022":
                    company = next_line
                    description_start = index + 2

        previous = lines[index - 1] if index > 0 else ""
        previous_previous = lines[index - 2] if index > 1 else ""

        if not title and previous and not _looks_like_date(previous):
            title, company = _split_title_company(previous)
        if previous_previous and not _looks_like_date(previous_previous):
            if _ROLE_RE.search(previous_previous) and not _ROLE_RE.search(previous):
                title = previous_previous
                company = previous
            elif _ROLE_RE.search(previous) and not _ROLE_RE.search(previous_previous):
                title = previous
                company = previous_previous
            elif not company and not _DEGREE_RE.search(previous_previous):
                company = previous_previous

        if "|" in line:
            tail = line.split("|", 1)[1]
            if not _looks_like_date(tail):
                location = _clean(tail)

        description_lines: list[str] = []
        for candidate in lines[description_start : description_start + 7]:
            if _looks_like_date(candidate):
                break
            if _heading_key(candidate)[0]:
                break
            if candidate == "\u2022":
                continue
            if _DEGREE_RE.search(candidate) and _INSTITUTION_RE.search(candidate):
                break
            description_lines.append(candidate)
            if len(description_lines) == 3:
                break

        if title or company or start_date or end_date or description_lines:
            rows.append(
                {
                    "company": company,
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "location": location,
                    "description": _condense_description(" ".join(description_lines)),
                }
            )
    return rows


def _condense_description(value: str) -> str:
    cleaned = _clean(value)
    if not cleaned:
        return ""
    parts = [part.strip(" .;") for part in re.split(r"\.\s+|;\s+|\n+", cleaned) if part.strip(" .;")]
    if not parts:
        return cleaned
    return ". ".join(parts[:3]) + ("." if parts[:3] else "")


def _extract_education(parsed: dict[str, Any], sections: dict[str, str]) -> list[dict[str, str]]:
    rows = _parse_education_section(sections.get("education", ""))
    if rows:
        return rows

    fallback: list[dict[str, str]] = []
    for item in parsed.get("education") or []:
        raw = _field(item, "raw", "description")
        degree = _field(item, "degree", "qualification") or (raw if _DEGREE_RE.search(raw) else "")
        fallback.append(
            {
                "institution": _field(item, "institution", "school", "university", "college"),
                "degree": degree,
                "field": _extract_field_of_study(degree),
                "graduation_date": _extract_graduation_date(item, raw),
                "gpa": _extract_gpa(raw),
            }
        )
    return fallback


def _parse_education_section(value: str) -> list[dict[str, str]]:
    if not value:
        return []
    lines = [_clean_line(line) for line in value.splitlines() if _clean_line(line)]
    rows: list[dict[str, str]] = []
    used_indexes: set[int] = set()

    for index, line in enumerate(lines):
        if not _looks_like_date(line):
            continue
        degree_index = index - 1
        while degree_index >= 0 and degree_index in used_indexes:
            degree_index -= 1
        degree = lines[degree_index] if degree_index >= 0 and _DEGREE_RE.search(lines[degree_index]) else ""
        if not degree:
            continue

        institution = ""
        for candidate in lines[index + 1 : index + 4]:
            if _looks_like_date(candidate):
                break
            if _DEGREE_RE.search(candidate) and not _INSTITUTION_RE.search(candidate):
                break
            if _INSTITUTION_RE.search(candidate) or not institution:
                institution = candidate
                break

        _, graduation_date = _date_range(line)
        if not graduation_date:
            graduation_date = _normalize_date_token(line)

        rows.append(
            {
                "institution": institution,
                "degree": degree,
                "field": _extract_field_of_study(degree),
                "graduation_date": graduation_date,
                "gpa": _extract_gpa(" ".join(lines[max(0, index - 1) : index + 4])),
            }
        )
        used_indexes.add(degree_index)

    if rows:
        return rows

    for line in lines:
        if _DEGREE_RE.search(line):
            _, graduation_date = _date_range(line)
            graduation_date = graduation_date or _normalize_date_token(line)
            degree = _clean(re.sub(_DATE_TOKEN_PATTERN, "", _DATE_RANGE_RE.sub("", line), flags=re.IGNORECASE).strip(" ,:-"))
            if not degree:
                degree = line
            rows.append(
                {
                    "institution": "",
                    "degree": degree,
                    "field": _extract_field_of_study(degree),
                    "graduation_date": graduation_date if _YEAR_RE.search(line) else "",
                    "gpa": _extract_gpa(line),
                }
            )
    return rows


def _extract_field_of_study(value: str) -> str:
    match = re.search(r"\bin\s+(.+)$", value, re.IGNORECASE)
    if not match:
        return ""
    field = re.sub(r"\([^)]*\)", "", match.group(1))
    return _clean(field)


def _extract_graduation_date(item: Any, raw: str) -> str:
    explicit = _field(item, "graduation_date", "end_date", "year")
    if explicit:
        return _normalize_date_token(explicit)
    _, end_date = _date_range(raw)
    return end_date or (_normalize_date_token(raw) if _YEAR_RE.search(raw) else "")


def _extract_gpa(value: str) -> str:
    match = _GPA_RE.search(value or "")
    return _clean(match.group(1)) if match else ""


def _extract_certifications(parsed: dict[str, Any], sections: dict[str, str]) -> list[str]:
    values: list[str] = []
    cert_section = sections.get("certifications", "")
    if cert_section:
        values.extend(_split_certification_text(cert_section))
    else:
        for item in parsed.get("certifications") or []:
            cert = _field(item, "name", "title", "certification", "raw", "description")
            if cert and not _FALSE_CERT_RE.search(cert):
                values.append(cert)
    return _unique(values)


def _split_certification_text(value: str) -> list[str]:
    items: list[str] = []
    for line in value.splitlines():
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        items.extend(re.split(r";|\u2022|\t", cleaned))
    return [_clean(item) for item in items if _clean(item)]
