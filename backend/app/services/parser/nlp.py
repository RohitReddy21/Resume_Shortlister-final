import re
from typing import Dict, List, Tuple

try:
    import spacy
    _nlp = None
except Exception:
    spacy = None
    _nlp = None

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3})?[\s.-]?(?:\(\d{2,4}\)|\d{2,4})[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
URL_RE = re.compile(r"https?://[\w./%#?=&+-]+|www\.[\w./%#?=&+-]+", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[A-Za-z0-9_-]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"github\.com/[A-Za-z0-9_-]+", re.IGNORECASE)

SKILL_KEYWORDS = {
    "Agile": [r"\bagile\b", r"\bscrum\b", r"\bkanban\b"],
    "Ansible": [r"\bansible\b"],
    "Application Insights": [r"\bapplication\s+insights\b", r"\bapp\s+insights\b"],
    "AWS": [r"\baws\b", r"\bamazon\s+web\s+services\b"],
    "Azure": [r"\bazure\b", r"\bmicrosoft\s+azure\b"],
    "Azure DevOps": [r"\bazure\s+devops\b", r"\bazure\s+pipelines\b"],
    "Azure Monitor": [r"\bazure\s+monitor\b"],
    "Azure Service Bus": [r"\bazure\s+service\s+bus\b", r"\bservice\s+bus\b"],
    "Bash": [r"\bbash\b", r"\bshell\s+scripting\b"],
    "Bitbucket": [r"\bbitbucket\b"],
    "C#": [r"\bc#\b", r"\bc\s*sharp\b"],
    "C++": [r"\bc\+\+\b"],
    "Cloudflare": [r"\bcloudflare\b"],
    "CI/CD": [r"\bci/cd\b", r"\bcicd\b", r"\bcontinuous\s+integration\b", r"\bcontinuous\s+delivery\b", r"\bcontinuous\s+deployment\b"],
    "Docker": [r"\bdocker\b", r"\bdockerfile\b"],
    "Django": [r"\bdjango\b"],
    "FastAPI": [r"\bfastapi\b"],
    "Flask": [r"\bflask\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "Google Cloud": [r"\bgcp\b", r"\bgoogle\s+cloud\b"],
    "Grafana": [r"\bgrafana\b"],
    "Infrastructure as Code": [r"\binfrastructure\s+as\s+code\b", r"\biac\b"],
    "Java": [r"\bjava\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "Jenkins": [r"\bjenkins\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Linux": [r"\blinux\b", r"\bubuntu\b", r"\bred\s*hat\b", r"\brhel\b"],
    "Microservices": [r"\bmicroservices?\b"],
    "MongoDB": [r"\bmongodb\b"],
    "MySQL": [r"\bmysql\b"],
    "Next.js": [r"\bnext\.?js\b"],
    "Node.js": [r"\bnode\.?js\b", r"\bnodejs\b"],
    "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
    "PowerShell": [r"\bpowershell\b"],
    "Prometheus": [r"\bprometheus\b"],
    "Python": [r"\bpython\b"],
    "React": [r"\breact\b", r"\breact\.?js\b"],
    "Redis": [r"\bredis\b"],
    "Security": [r"\bsecurity\b", r"\biam\b", r"\boauth\b", r"\bjwt\b", r"\bwaf\b"],
    "Selenium": [r"\bselenium\b"],
    "SQL": [r"\bsql\b", r"\bsql\s+server\b"],
    "Terraform": [r"\bterraform\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
}

NAME_LINE_BLOCKLIST = {
    "summary",
    "profile summary",
    "professional summary",
    "career summary",
    "objective",
    "experience",
    "professional experience",
    "work experience",
    "employment history",
    "education",
    "educational qualification",
    "educational qualifications",
    "certifications",
    "certification",
    "certificates",
    "contact",
    "contacts",
    "skills",
    "technical skills",
    "key skills",
    "core competencies",
    "projects",
    "languages",
    "phone",
    "email",
    "location",
}

NAME_TOKEN_BLOCKLIST = {
    "analyst",
    "engineer",
    "developer",
    "intern",
    "manager",
    "specialist",
    "consultant",
    "administrator",
    "associate",
    "office",
    "microsoft",
    "naukri",
    "candidate",
    "bachelor",
    "technology",
    "science",
    "institute",
    "university",
    "college",
    "google",
    "cybersecurity",
    "professional",
    "summary",
    "experience",
    "certified",
    "certification",
    "and",
    "or",
    "with",
    "using",
    "for",
    "in",
    "on",
    "of",
    "the",
    "azure",
    "aws",
    "devops",
    "powershell",
    "terraform",
    "docker",
    "kubernetes",
    "python",
    "bash",
    "git",
    "cloud",
    "tech",
    "mahindra",
    "technologies",
    "technology",
    "systems",
    "solutions",
    "services",
    "private",
    "limited",
    "pvt",
    "ltd",
    "inc",
    "corp",
    "corporation",
    "company",
    "iac",
    "governance",
    "standards",
    "standard",
    "enforced",
    "architected",
    "automated",
    "built",
    "configured",
    "deployed",
    "implemented",
    "managed",
    "migrated",
    "optimized",
    "provisioned",
}

NAME_CONNECTOR_TOKENS = {"and", "or", "with", "using", "for", "in", "on", "of", "the"}
NAME_SKILL_TOKENS = {
    token
    for skill_name in SKILL_KEYWORDS
    for token in re.findall(r"[A-Za-z]+", skill_name.lower())
}
NAME_SKILL_TOKENS.update(
    {
        "devops",
        "powershell",
        "terraform",
        "docker",
        "kubernetes",
        "azure",
        "cloud",
        "iac",
        "governance",
        "standards",
    }
)

FILENAME_NAME_BLOCKLIST = {
    "resume",
    "resumes",
    "cv",
    "curriculum",
    "vitae",
    "profile",
    "updated",
    "latest",
    "final",
    "copy",
    "new",
}

COMPANY_LINE_BLOCKLIST = re.compile(
    r"\b(certified|certification|certificate|summary|professional\s+summary|professional\s+experience|skills?|education|projects?|languages?)\b",
    re.IGNORECASE,
)
COMPANY_SENTENCE_START_RE = re.compile(
    r"^(specializing|specialising|proven|experienced|including|responsible|worked|working|hands[- ]on|cloud\s+and|azure\s+cloud)\b",
    re.IGNORECASE,
)
NAME_ACTION_START_RE = re.compile(
    r"^(architected|automated|built|configured|deployed|developed|enforced|implemented|improved|managed|migrated|optimized|provisioned|reduced|supported|worked)\b",
    re.IGNORECASE,
)
NAME_ORGANIZATION_RE = re.compile(
    r"\b(mahindra|technologies|technology|systems|solutions|services|private|limited|pvt|ltd|inc|corp|corporation|company)\b",
    re.IGNORECASE,
)


def _load_nlp():
    global _nlp
    if _nlp is None and spacy is not None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception:
            try:
                from spacy.cli import download
                download("en_core_web_sm")
                _nlp = spacy.load("en_core_web_sm")
            except Exception:
                _nlp = None
    return _nlp


def extract_contact_info(text: str) -> Dict[str, dict]:
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    urls = URL_RE.findall(text)
    linkedin = None
    github = None
    for u in urls:
        if LINKEDIN_RE.search(u):
            linkedin = u
        if GITHUB_RE.search(u):
            github = u
    if linkedin is None:
        match = LINKEDIN_RE.search(text)
        if match:
            linkedin = match.group(0)
    if github is None:
        match = GITHUB_RE.search(text)
        if match:
            github = match.group(0)
    return {
        "emails": [{"value": emails[0], "confidence": 0.99}] if emails else [],
        "phones": [{"value": phones[0], "confidence": 0.9}] if phones else [],
        "linkedin": linkedin,
        "github": github,
        "urls": urls,
    }


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip(" \t\r\n:|•-"))


def _normalized_line(line: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", line.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _format_person_name(line: str) -> str:
    tokens = [token for token in re.split(r"\s+", _clean_line(line)) if token]
    formatted = []
    for token in tokens:
        if token.isupper() and 1 < len(token) <= 3:
            formatted.append(token)
        else:
            formatted.append(token.title())
    return " ".join(formatted)


def name_value_looks_suspicious(value: str | None) -> bool:
    cleaned = _clean_line(value or "")
    if not cleaned:
        return False
    normalized = _normalized_line(cleaned)
    if normalized in NAME_LINE_BLOCKLIST:
        return True
    if NAME_ACTION_START_RE.search(cleaned) or NAME_ORGANIZATION_RE.search(cleaned):
        return True
    tokens = {token.lower() for token in re.findall(r"[A-Za-z]+", cleaned)}
    return bool(tokens.intersection(NAME_TOKEN_BLOCKLIST) or tokens.intersection(NAME_SKILL_TOKENS))


def _line_looks_like_person_name(line: str) -> bool:
    cleaned = _clean_line(line)
    if not cleaned:
        return False
    lower = cleaned.lower()
    if lower in NAME_LINE_BLOCKLIST:
        return False
    normalized = _normalized_line(cleaned)
    if normalized in NAME_LINE_BLOCKLIST:
        return False
    if NAME_ACTION_START_RE.search(cleaned) or NAME_ORGANIZATION_RE.search(cleaned):
        return False
    if any(char.isdigit() for char in cleaned) or "@" in cleaned or "/" in cleaned:
        return False
    if any(mark in cleaned for mark in [",", ":", "(", ")", "[", "]"]):
        return False
    tokens = [token for token in re.split(r"\s+", cleaned) if token]
    if not 2 <= len(tokens) <= 4:
        return False
    lowered_tokens = {token.lower() for token in tokens}
    if lowered_tokens.intersection(NAME_TOKEN_BLOCKLIST):
        return False
    if lowered_tokens.intersection(NAME_CONNECTOR_TOKENS):
        return False
    if lowered_tokens.intersection(NAME_SKILL_TOKENS):
        return False
    return all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", token) for token in tokens)


def _extract_name_prefix(line: str) -> str | None:
    cleaned = _clean_line(line)
    if not cleaned:
        return None
    parts = [part.strip() for part in re.split(r"\s+[-\u2013\u2014|]\s+", cleaned, maxsplit=1)]
    if len(parts) < 2:
        return None
    prefix = parts[0]
    return prefix if _line_looks_like_person_name(prefix) else None


def _extract_name_from_lines(text: str) -> str | None:
    lines = [_clean_line(line) for line in text.splitlines()[:80]]

    top_lines = [line for line in lines[:20] if line]
    top_candidates = [line for line in top_lines if _line_looks_like_person_name(line)]
    if top_candidates:
        for line in top_candidates:
            letters = re.sub(r"[^A-Za-z]", "", line)
            if letters and letters.upper() == letters:
                return _format_person_name(line)
        return _format_person_name(top_candidates[0])

    for line in lines[:12]:
        prefix = _extract_name_prefix(line)
        if prefix:
            return _format_person_name(prefix)

    candidates = [line for line in lines if _line_looks_like_person_name(line)]
    if not candidates:
        return None

    # Prefer all-uppercase name headers such as "RAJESH BURRA", but avoid role titles via blocklist.
    for line in candidates:
        letters = re.sub(r"[^A-Za-z]", "", line)
        if letters and letters.upper() == letters:
            return _format_person_name(line)
    return _format_person_name(candidates[0])


def _extract_name_from_email(text: str) -> str | None:
    emails = EMAIL_RE.findall(text)
    if not emails:
        return None
    local = emails[0].split("@", 1)[0]
    parts = [part for part in re.split(r"[._-]+", re.sub(r"\d+", "", local)) if len(part) > 1]
    if len(parts) >= 2:
        return " ".join(part.capitalize() for part in parts[:4])
    if len(parts) == 1 and len(parts[0]) >= 3 and parts[0].lower() not in NAME_TOKEN_BLOCKLIST:
        return parts[0].capitalize()
    return None


def extract_name_from_filename(filename: str) -> str | None:
    name = re.sub(r"^.*[\\/]", "", filename or "")
    name = re.sub(r"\.[^.]+$", "", name)
    name = re.sub(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"[_+.]+", " ", name)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    tokens = []
    for token in re.split(r"\s+", name):
        cleaned = re.sub(r"[^A-Za-z.'-]", "", token).strip(".'-")
        if not cleaned:
            continue
        if cleaned.lower() in FILENAME_NAME_BLOCKLIST:
            continue
        tokens.append(cleaned)

    candidate = " ".join(tokens[:4])
    if _line_looks_like_person_name(candidate):
        return _format_person_name(candidate)
    return None


def extract_name(text: str) -> dict:
    line_name = _extract_name_from_lines(text)
    if line_name:
        return {"value": line_name, "confidence": 0.75}

    nlp = _load_nlp()
    if nlp is not None:
        doc = nlp(text[:1000])
        for ent in doc.ents:
            candidate = ent.text.strip()
            if ent.label_ == "PERSON" and _line_looks_like_person_name(candidate):
                return {"value": candidate, "confidence": 0.85}

    email_name = _extract_name_from_email(text)
    if email_name:
        return {"value": email_name, "confidence": 0.55}

    return {"value": None, "confidence": 0.0}


def extract_skills(text: str) -> List[Dict]:
    found: dict[str, str] = {}
    for skill_name, patterns in SKILL_KEYWORDS.items():
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            found[skill_name.lower()] = skill_name
    return [{"name": s, "confidence": 0.8} for s in sorted(found.values(), key=str.lower)]


def extract_sections(text: str) -> Dict[str, str]:
    # Very simple section splitter by common headings
    headings = ["experience", "work experience", "professional experience", "education", "skills", "projects", "certifications", "languages"]
    lower = text.lower()
    sections = {}
    for h in headings:
        idx = lower.find(h)
        if idx != -1:
            snippet = text[idx: idx + 2000]
            sections[h] = snippet
    return sections


def extract_experiences(text: str) -> List[Dict]:
    # heuristic: find lines with years or 'Present'
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    exps = []
    for i, line in enumerate(lines):
        if re.search(r"\b(19|20)\d{2}\b", line) or "present" in line.lower():
            # take previous line as title/company
            title = lines[i-1] if i>0 else None
            exps.append({"raw": line, "title_company": title, "confidence": 0.6})
    return exps


def extract_education(text: str) -> List[Dict]:
    edu_keywords = ["bachelor", "b.sc", "b.s.", "msc", "m.sc", "master", "phd", "doctor"]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    eds = []
    for line in lines:
        low = line.lower()
        for kw in edu_keywords:
            if kw in low:
                eds.append({"raw": line, "confidence": 0.6})
                break
    return eds


def extract_certifications(text: str) -> List[Dict]:
    cert_keywords = ["certified", "certificate", "certification", "cisco", "aws certified", "azure"]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    certs = []
    for line in lines:
        low = line.lower()
        for kw in cert_keywords:
            if kw in low:
                certs.append({"raw": line, "confidence": 0.6})
                break
    return certs


def extract_projects(text: str) -> List[Dict]:
    sections = extract_sections(text)
    projects_text = sections.get("projects") or sections.get("project") or ""
    if not projects_text:
        # fallback: find "Project" lines
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        projs = [l for l in lines if l.lower().startswith("project") or "project:" in l.lower()]
        return [{"raw": p, "confidence": 0.6} for p in projs]
    # split by bullets or newlines
    items = re.split(r"\n\s*-\s+|\n\s*\d+\.\s+", projects_text)
    return [{"raw": i.strip(), "confidence": 0.6} for i in items if i.strip()]


def extract_languages(text: str) -> List[Dict]:
    lang_keywords = ["english", "hindi", "spanish", "french", "german", "chinese", "mandarin"]
    lower = text.lower()
    found = []
    for kw in lang_keywords:
        if kw in lower:
            found.append({"name": kw.capitalize(), "confidence": 0.8})
    return found


def extract_companies_and_designations(text: str) -> List[Dict]:
    nlp = _load_nlp()
    results = []
    if nlp is None:
        return results
    doc = nlp(text)
    # collect ORG and potential TITLE lines heuristically
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if not line or line[0].islower() or line.startswith(("-", "*", "•", "â€¢")) or len(line) > 100:
            continue
        if ":" in line:
            continue
        if "," in line:
            continue
        if COMPANY_LINE_BLOCKLIST.search(line):
            continue
        if COMPANY_SENTENCE_START_RE.search(line):
            continue
        previous_line = lines[i - 1] if i > 0 else ""
        if _normalized_line(previous_line) in {
            "skills",
            "technical skills",
            "key skills",
            "certifications",
            "certification",
            "certificates",
        }:
            continue
        if any(org.lower() in line.lower() for org in orgs):
            # look up/down for title and dates
            title = lines[i-1] if i>0 else None
            date_line = None
            for j in range(i, min(i+3, len(lines))):
                if re.search(r"\b(19|20)\d{2}\b", lines[j]) or "present" in lines[j].lower():
                    date_line = lines[j]
                    break
            results.append({"company_line": line, "title_line": title, "date_line": date_line, "confidence": 0.6})
    return results


def _normalize_money_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value.strip(" :-|\t\r\n"))
    cleaned = cleaned.rstrip(".,;")
    return cleaned or None


def _find_compensation_value(text: str, labels: list[str]) -> str | None:
    amount = r"(?:rs\.?|inr|₹)?\s*\d+(?:[,.]\d+)*(?:\s*(?:lpa|lakhs?|lacs?|pa|per\s+annum|p\.a\.|pm|per\s+month|monthly|k))?"
    negotiable = r"(?:negotiable|as\s+per\s+company\s+standard|open\s+to\s+discuss)"
    value_pattern = rf"({amount}|{negotiable})"

    for label in labels:
        pattern = rf"{label}\s*(?:ctc|package|salary|compensation)?\s*(?:is|was|:|-|=)?\s*{value_pattern}"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _normalize_money_text(match.group(1))
    return None


def extract_salary_info(text: str) -> Dict:
    current = _find_compensation_value(
        text,
        [
            r"current",
            r"present",
            r"current\s+annual",
            r"c\s*\.?\s*c\s*\.?\s*t\s*\.?\s*c",
            r"cctc",
        ],
    )
    expected = _find_compensation_value(
        text,
        [
            r"expected",
            r"desired",
            r"expecting",
            r"e\s*\.?\s*c\s*\.?\s*t\s*\.?\s*c",
            r"ectc",
        ],
    )

    # Fallback for compact forms like "CTC: 12 LPA" when no current value was found.
    if current is None:
        current = _find_compensation_value(text, [r"ctc", r"salary", r"package"])

    return {"current_ctc": current, "expected_ctc": expected}


def extract_notice_period(text: str) -> str | None:
    m = re.search(r"notice\s+period[:\s]*([0-9]+\s*(?:days?|months?|weeks?))", text, re.IGNORECASE)
    if m:
        return m.group(1)
    # common phrasing
    m2 = re.search(r"serving\s+notice\s+period\s+of\s+([0-9]+)\s+days", text, re.IGNORECASE)
    if m2:
        return m2.group(1) + " days"
    return None
