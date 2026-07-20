import json
import math
import re
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from app.services.parser.structured import build_structured_resume


NOT_FOUND = "Not Found"

def _repair_export_text(value: Any) -> str:
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    elif value is None:
        text = ""
    else:
        text = str(value)
    text = unicodedata.normalize("NFKC", text)
    if any(marker in text for marker in ("Ã", "â", "Â", "ð")):
        for source_encoding in ("cp1252", "latin-1"):
            try:
                repaired = text.encode(source_encoding).decode("utf-8")
            except Exception:
                continue
            if repaired and repaired.count("�") <= text.count("�"):
                text = repaired
                break
    replacements = {
        "\u00a0": " ",
        "•": "- ",
        "◦": "- ",
        "●": "- ",
        "▪": "- ",
        "–": "-",
        "—": "-",
        "−": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "…": "...",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ch.isprintable())
    return re.sub(r"[ \t]+", " ", text).strip()


REPORT_COLUMNS = [
    "Candidate Name",
    "Email",
    "Phone Number",
    "Location",
    "LinkedIn",
    "Portfolio/GitHub",
    "Current Company",
    "Designation",
    "Experience",
    "Relevant Experience",
    "Qualification",
    "Notice Period",
    "Current CTC",
    "Expected CTC",
    "Willing to Relocate",
    "Certifications",
    "Cloud Skills",
    "DevOps Skills",
    "Terraform",
    "Azure DevOps",
    "Bitbucket",
    "Docker",
    "Kubernetes",
    "Cloudflare",
    "Azure Service Bus",
    "Azure Monitor",
    "Application Insights",
    "Python",
    "PowerShell",
    "Bash",
    "Git",
    "Rating (/10)",
    "Recommendation",
    "Missing Skills",
    "Missing Certifications",
    "Missing Experience",
    "Reason",
    "Interview Questions",
]

FIXED_REQUIREMENTS = [
    "Azure DevOps",
    "Terraform",
    "Bitbucket",
    "Azure",
    "Azure Service Bus",
    "Docker",
    "Kubernetes",
    "Cloudflare",
    "Azure Monitor",
    "Application Insights",
    "PowerShell",
    "Python",
    "Bash",
    "CI/CD",
    "Infrastructure as Code",
    "Monitoring",
    "Security",
    "Git",
    "Microservices",
    "Azure Certifications",
    "Agile",
]

REQUIREMENT_SYNONYMS = {
    "Azure DevOps": ["azure devops", "azdo", "azure pipelines"],
    "Terraform": ["terraform"],
    "Bitbucket": ["bitbucket"],
    "Azure": ["azure", "microsoft azure"],
    "Azure Service Bus": ["azure service bus", "service bus"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s", "aks"],
    "Cloudflare": ["cloudflare"],
    "Azure Monitor": ["azure monitor"],
    "Application Insights": ["application insights", "app insights"],
    "PowerShell": ["powershell", "power shell"],
    "Python": ["python"],
    "Bash": ["bash", "shell scripting"],
    "CI/CD": ["ci cd", "ci/cd", "continuous integration", "continuous deployment", "pipeline", "pipelines"],
    "Infrastructure as Code": ["infrastructure as code", "iac", "terraform"],
    "Monitoring": ["monitoring", "observability", "alerts", "alerting"],
    "Security": ["security", "iam", "vulnerability", "threat", "compliance"],
    "Git": ["git", "github", "gitlab"],
    "Microservices": ["microservices", "micro services"],
    "Azure Certifications": ["azure certified", "az 900", "az-900", "az 104", "az-104", "az 400", "az-400"],
    "Agile": ["agile", "scrum", "kanban"],
}

SKILL_TAXONOMY = {
    "Programming Languages": ["Python", "Java", "JavaScript", "TypeScript", "C#", "C++", "Go", "Ruby", "PHP"],
    "Cloud Platforms": ["Azure", "AWS", "Google Cloud", "GCP", "Cloudflare"],
    "CI/CD Tools": ["Azure DevOps", "Azure Pipelines", "Jenkins", "GitHub Actions", "GitLab CI", "Bitbucket Pipelines"],
    "Infrastructure as Code": ["Terraform", "Bicep", "ARM Templates", "CloudFormation", "Pulumi", "Ansible"],
    "Containers": ["Docker", "Container Registry"],
    "Container Orchestration": ["Kubernetes", "AKS", "EKS", "GKE", "OpenShift"],
    "Monitoring Tools": ["Azure Monitor", "Application Insights", "Prometheus", "Grafana", "ELK", "Splunk", "Datadog"],
    "Databases": ["SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cosmos DB", "SQL Server"],
    "Version Control": ["Git", "GitHub", "GitLab", "Bitbucket"],
    "Scripting": ["PowerShell", "Bash", "Shell", "Python"],
    "Operating Systems": ["Linux", "Windows", "Ubuntu"],
    "Security": ["Security", "IAM", "Key Vault", "Firewall", "Vulnerability", "Compliance", "SOC"],
    "Networking": ["DNS", "TCP/IP", "HTTP", "HTTPS", "Load Balancer", "VPN", "VNet", "Subnet"],
    "DevOps Tools": ["Azure DevOps", "Jenkins", "Ansible", "ServiceNow", "Jira", "Maven", "Nexus"],
    "Build Tools": ["Maven", "Gradle", "npm", "Webpack", "MSBuild"],
    "Other Technologies": ["Microservices", "Agile", "REST", "API", "Selenium", "Postman"],
}


def parse_job_skills(job: Any) -> list[str]:
    raw_skills = getattr(job, "skills", None)
    skills: list[str] = []
    if isinstance(raw_skills, str):
        try:
            parsed = json.loads(raw_skills)
            if isinstance(parsed, list):
                skills.extend(str(item) for item in parsed if item)
        except Exception:
            skills.extend(part.strip() for part in re.split(r"[,;|\n]+", raw_skills) if part.strip())
    elif isinstance(raw_skills, list):
        skills.extend(str(item) for item in raw_skills if item)
    return _unique(skills)


def build_ats_screening_report(job: Any, resumes: list[Any]) -> dict[str, Any]:
    requirements = build_job_requirements(job)
    candidates = []

    for resume in resumes:
        current_version = getattr(resume, "current_version", None)
        if current_version is None or not getattr(current_version, "parsed_json", None):
            continue
        try:
            parsed = json.loads(current_version.parsed_json or "{}")
        except Exception:
            continue
        candidates.append(analyze_candidate(job, resume, parsed, requirements))

    candidates.sort(key=lambda item: item["rating"], reverse=True)
    dashboard = build_dashboard(candidates)
    return {
        "job": {
            "id": getattr(job, "id", ""),
            "title": getattr(job, "title", ""),
            "requirements": requirements,
        },
        "dashboard": dashboard,
        "candidates": candidates,
    }


def build_job_requirements(job: Any) -> list[str]:
    job_text = " ".join(
        part for part in [getattr(job, "title", "") or "", getattr(job, "description", "") or ""] if part
    )
    requirements = parse_job_skills(job)

    normalized_job_text = _normalize(job_text)
    for requirement in FIXED_REQUIREMENTS:
        synonyms = REQUIREMENT_SYNONYMS.get(requirement, [requirement])
        if any(_normalize(synonym) in normalized_job_text for synonym in synonyms):
            requirements.append(requirement)

    return _unique(requirements) or FIXED_REQUIREMENTS


def analyze_candidate(job: Any, resume: Any, parsed: dict[str, Any], requirements: list[str]) -> dict[str, Any]:
    structured = build_structured_resume(parsed)
    candidate = getattr(resume, "candidate", None)
    raw_text = str(parsed.get("parsed_text") or "")
    skills_by_category = categorize_skills(structured, raw_text)
    requirement_matches = match_requirements(requirements, structured, raw_text)
    fixed_matches = match_requirements(FIXED_REQUIREMENTS, structured, raw_text)

    current_company, current_designation = current_role(structured, parsed)
    total_experience = extract_total_experience(raw_text, structured)
    relevant_experience = extract_relevant_experience(total_experience, requirement_matches)
    qualification = extract_highest_qualification(structured)
    certifications = _join_or_not_found(structured.get("certifications", []))
    github_portfolio = extract_portfolio(parsed, raw_text)
    willing_to_relocate = extract_relocation(raw_text)
    notice_period = _first_found(
        getattr(candidate, "notice_period", None) if candidate else None,
        parsed.get("notice_period"),
    )
    current_ctc = _first_found(
        getattr(candidate, "current_package", None) if candidate else None,
        parsed.get("current_ctc"),
    )
    expected_ctc = _first_found(
        getattr(candidate, "expected_package", None) if candidate else None,
        parsed.get("expected_ctc"),
    )

    score = score_candidate(requirement_matches, fixed_matches, total_experience, structured, raw_text)
    recommendation = recommendation_from_rating(score["rating"])
    missing_skills = [requirement for requirement, value in requirement_matches.items() if value == "❌ Missing"]
    missing_certifications = missing_certification_text(requirements, structured, raw_text)
    missing_experience = missing_experience_text(total_experience, relevant_experience)
    reason = recommendation_reason(score["rating"], missing_skills, requirement_matches, relevant_experience)
    interview_questions = generate_interview_questions(requirement_matches, fixed_matches, current_designation)

    report_row = {
        "Candidate Name": _first_found(structured.get("name")),
        "Email": _first_found(structured.get("email")),
        "Phone Number": _first_found(structured.get("phone")),
        "Location": _first_found(structured.get("location")),
        "LinkedIn": _first_found(structured.get("linkedin")),
        "Portfolio/GitHub": github_portfolio,
        "Current Company": current_company,
        "Designation": current_designation,
        "Experience": total_experience,
        "Relevant Experience": relevant_experience,
        "Qualification": qualification,
        "Notice Period": notice_period,
        "Current CTC": current_ctc,
        "Expected CTC": expected_ctc,
        "Willing to Relocate": willing_to_relocate,
        "Certifications": certifications,
        "Cloud Skills": _join_or_not_found(skills_by_category["Cloud Platforms"]),
        "DevOps Skills": _join_or_not_found(
            _unique(
                skills_by_category["CI/CD Tools"]
                + skills_by_category["Infrastructure as Code"]
                + skills_by_category["Containers"]
                + skills_by_category["Container Orchestration"]
                + skills_by_category["Monitoring Tools"]
                + skills_by_category["DevOps Tools"]
            )
        ),
        "Terraform": fixed_matches["Terraform"],
        "Azure DevOps": fixed_matches["Azure DevOps"],
        "Bitbucket": fixed_matches["Bitbucket"],
        "Docker": fixed_matches["Docker"],
        "Kubernetes": fixed_matches["Kubernetes"],
        "Cloudflare": fixed_matches["Cloudflare"],
        "Azure Service Bus": fixed_matches["Azure Service Bus"],
        "Azure Monitor": fixed_matches["Azure Monitor"],
        "Application Insights": fixed_matches["Application Insights"],
        "Python": fixed_matches["Python"],
        "PowerShell": fixed_matches["PowerShell"],
        "Bash": fixed_matches["Bash"],
        "Git": fixed_matches["Git"],
        "Rating (/10)": score["rating"],
        "Recommendation": recommendation,
        "Missing Skills": _join_or_not_found(missing_skills),
        "Missing Certifications": missing_certifications,
        "Missing Experience": missing_experience,
        "Reason": reason,
        "Interview Questions": "\n".join(interview_questions),
    }

    return {
        "resume_id": getattr(resume, "id", ""),
        "resume_title": getattr(resume, "title", ""),
        "structured": {
            **structured,
            "portfolio_github": github_portfolio,
            "current_company": current_company,
            "current_designation": current_designation,
            "total_experience": total_experience,
            "relevant_experience": relevant_experience,
            "highest_qualification": qualification,
            "notice_period": notice_period,
            "current_ctc": current_ctc,
            "expected_ctc": expected_ctc,
            "willing_to_relocate": willing_to_relocate,
        },
        "skills_by_category": skills_by_category,
        "requirement_matches": requirement_matches,
        "rating": score["rating"],
        "score_breakdown": score["breakdown"],
        "recommendation": recommendation,
        "missing_skills": missing_skills,
        "missing_certifications": missing_certifications,
        "missing_experience": missing_experience,
        "reason": reason,
        "interview_questions": interview_questions,
        "report_row": report_row,
    }


def categorize_skills(structured: dict[str, Any], raw_text: str) -> dict[str, list[str]]:
    detected_text = _normalize(" ".join(structured.get("skills", [])) + " " + raw_text)
    categories: dict[str, list[str]] = {}
    for category, terms in SKILL_TAXONOMY.items():
        categories[category] = [term for term in terms if _normalize(term) in detected_text]
    return categories


def match_requirements(requirements: list[str], structured: dict[str, Any], raw_text: str) -> dict[str, str]:
    skill_text = _normalize(" ".join(structured.get("skills", [])))
    full_text = _normalize(skill_text + " " + raw_text)
    matches: dict[str, str] = {}
    for requirement in requirements:
        synonyms = REQUIREMENT_SYNONYMS.get(requirement, [requirement])
        normalized_synonyms = [_normalize(item) for item in synonyms if item]
        if any(synonym and synonym in skill_text for synonym in normalized_synonyms):
            matches[requirement] = "✅ Strong Match"
            continue
        if any(synonym and synonym in full_text for synonym in normalized_synonyms):
            matches[requirement] = "🟡 Partial Match"
            continue

        requirement_tokens = [token for token in _normalize(requirement).split() if len(token) > 2]
        token_matches = sum(1 for token in requirement_tokens if token in full_text)
        if requirement_tokens and token_matches >= max(1, math.ceil(len(requirement_tokens) / 2)):
            matches[requirement] = "🟡 Partial Match"
        else:
            matches[requirement] = "❌ Missing"
    return matches


def score_candidate(
    requirement_matches: dict[str, str],
    fixed_matches: dict[str, str],
    total_experience: str,
    structured: dict[str, Any],
    raw_text: str,
) -> dict[str, Any]:
    mandatory_score = _match_ratio(requirement_matches)
    azure_requirements = {
        key: value
        for key, value in fixed_matches.items()
        if "azure" in key.lower() or key in {"Application Insights"}
    }
    azure_score = _match_ratio(azure_requirements)
    devops_requirements = {
        key: value
        for key, value in fixed_matches.items()
        if key
        in {
            "Azure DevOps",
            "Terraform",
            "Docker",
            "Kubernetes",
            "CI/CD",
            "Infrastructure as Code",
            "Monitoring",
            "Security",
            "Git",
            "Agile",
            "Bash",
            "PowerShell",
        }
    }
    devops_score = _match_ratio(devops_requirements)
    experience_score = experience_score_from_text(total_experience, structured)
    certification_score = certification_score_from_text(structured, raw_text)

    rating = (
        experience_score * 0.20
        + mandatory_score * 0.40
        + azure_score * 0.20
        + devops_score * 0.10
        + certification_score * 0.10
    ) * 10

    return {
        "rating": round(min(10.0, rating), 1),
        "breakdown": {
            "Experience": round(experience_score * 10, 1),
            "Mandatory Skills": round(mandatory_score * 10, 1),
            "Azure Experience": round(azure_score * 10, 1),
            "DevOps Best Practices": round(devops_score * 10, 1),
            "Certifications": round(certification_score * 10, 1),
        },
    }


def _match_ratio(matches: dict[str, str]) -> float:
    if not matches:
        return 0.0
    score = 0.0
    for value in matches.values():
        if "Strong" in value:
            score += 1.0
        elif "Partial" in value:
            score += 0.5
    return score / len(matches)


def experience_score_from_text(total_experience: str, structured: dict[str, Any]) -> float:
    years = extract_years_number(total_experience)
    if years is None:
        experience_entries = structured.get("experience") or []
        if experience_entries:
            return 0.4
        return 0.0
    if years >= 5:
        return 1.0
    if years >= 3:
        return 0.8
    if years >= 1:
        return 0.5
    return 0.2


def certification_score_from_text(structured: dict[str, Any], raw_text: str) -> float:
    certifications = " ".join(structured.get("certifications", []))
    text = _normalize(certifications + " " + raw_text)
    if any(_normalize(term) in text for term in REQUIREMENT_SYNONYMS["Azure Certifications"]):
        return 1.0
    if certifications.strip():
        return 0.5
    return 0.0


def recommendation_from_rating(rating: float) -> str:
    if rating >= 8.5:
        return "Strong Hire"
    if rating >= 7.5:
        return "Hire"
    if rating >= 6.5:
        return "Consider"
    return "Reject"


def recommendation_reason(
    rating: float,
    missing_skills: list[str],
    requirement_matches: dict[str, str],
    relevant_experience: str,
) -> str:
    strong_count = sum(1 for value in requirement_matches.values() if "Strong" in value)
    partial_count = sum(1 for value in requirement_matches.values() if "Partial" in value)
    if rating >= 8.5:
        return f"Strong fit with {strong_count} strong JD requirement matches and relevant experience evidence."
    if rating >= 7.5:
        return f"Good fit with {strong_count} strong and {partial_count} partial JD requirement matches."
    if rating >= 6.5:
        return f"Consider only if gaps can be covered; missing skills include {_join_or_not_found(missing_skills[:4])}."
    if relevant_experience == NOT_FOUND:
        return "Reject because relevant experience for the JD was not found and mandatory skill coverage is low."
    return f"Reject because mandatory skill coverage is low; missing skills include {_join_or_not_found(missing_skills[:4])}."


def missing_certification_text(requirements: list[str], structured: dict[str, Any], raw_text: str) -> str:
    needs_azure_cert = any("cert" in requirement.lower() for requirement in requirements)
    if not needs_azure_cert:
        return NOT_FOUND
    if certification_score_from_text(structured, raw_text) >= 1.0:
        return NOT_FOUND
    return "Azure Certifications"


def missing_experience_text(total_experience: str, relevant_experience: str) -> str:
    if total_experience == NOT_FOUND:
        return "Total experience not found"
    if relevant_experience == NOT_FOUND:
        return "Relevant JD experience not found"
    return NOT_FOUND


def generate_interview_questions(
    requirement_matches: dict[str, str],
    fixed_matches: dict[str, str],
    designation: str,
) -> list[str]:
    missing_or_partial = [key for key, value in requirement_matches.items() if "Strong" not in value]
    strong = [key for key, value in requirement_matches.items() if "Strong" in value]
    focus = _unique(missing_or_partial + strong + list(fixed_matches.keys()))
    role = designation if designation != NOT_FOUND else "this role"
    questions = [
        f"Explain a recent {role} project where you designed or improved a CI/CD pipeline.",
        f"How would you implement Infrastructure as Code for Azure resources using {focus[0] if focus else 'Terraform'}?",
        f"Describe how you would troubleshoot a production issue using monitoring tools such as Azure Monitor or Application Insights.",
        f"What security controls would you apply for containerized workloads running on Kubernetes?",
        f"Walk through how you would manage source control, branching, and release governance with Git/Bitbucket/Azure DevOps.",
    ]
    return questions[:5]


def current_role(structured: dict[str, Any], parsed: dict[str, Any]) -> tuple[str, str]:
    for item in structured.get("experience") or []:
        end_date = str(item.get("end_date") or "").lower()
        if end_date in {"present", "current", "now"}:
            return _first_found(item.get("company")), _first_found(item.get("title"))
    first = (structured.get("experience") or [{}])[0] if structured.get("experience") else {}
    return _first_found(parsed.get("current_company"), first.get("company")), _first_found(first.get("title"))


def extract_total_experience(raw_text: str, structured: dict[str, Any]) -> str:
    patterns = [
        r"(?:total\s+)?experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*years?(?:\s*(\d+)\s*months?)?",
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience",
        r"(\d+)\s*years?\s*(\d+)\s*months?",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            years = match.group(1)
            months = match.group(2) if len(match.groups()) > 1 else None
            return f"{years} Years" + (f" {months} Months" if months else "")

    years = estimate_experience_from_ranges(structured.get("experience") or [])
    if years is not None:
        return f"{years:.1f} Years"
    return NOT_FOUND


def extract_relevant_experience(total_experience: str, requirement_matches: dict[str, str]) -> str:
    if total_experience == NOT_FOUND:
        return NOT_FOUND
    if any("Strong" in value or "Partial" in value for value in requirement_matches.values()):
        return total_experience
    return NOT_FOUND


def estimate_experience_from_ranges(experience: list[dict[str, Any]]) -> float | None:
    total_months = 0
    for item in experience:
        start = parse_year_month(item.get("start_date"))
        end = parse_year_month(item.get("end_date")) or current_year_month()
        if start and end and end >= start:
            total_months += (end[0] - start[0]) * 12 + (end[1] - start[1])
    if total_months <= 0:
        return None
    return round(total_months / 12, 1)


def parse_year_month(value: Any) -> tuple[int, int] | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"present", "current", "now"}:
        return None
    month_names = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    year_match = re.search(r"(19|20)\d{2}", text)
    if not year_match:
        return None
    month = 1
    month_match = re.search(r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", text, re.IGNORECASE)
    if month_match:
        month = month_names[month_match.group(0).lower()[:3]]
    return int(year_match.group(0)), month


def current_year_month() -> tuple[int, int]:
    today = datetime.utcnow()
    return today.year, today.month


def extract_years_number(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", value or "")
    return float(match.group(1)) if match else None


def extract_highest_qualification(structured: dict[str, Any]) -> str:
    education = structured.get("education") or []
    if not education:
        return NOT_FOUND
    ranked: list[tuple[int, str]] = []
    for item in education:
        degree = str(item.get("degree") or "")
        institution = str(item.get("institution") or "")
        text = " | ".join(part for part in [degree, institution] if part)
        lower = degree.lower()
        rank = 1
        if any(term in lower for term in ["phd", "doctor"]):
            rank = 5
        elif any(term in lower for term in ["master", "mca", "mba", "m.tech", "mtech"]):
            rank = 4
        elif any(term in lower for term in ["bachelor", "b.tech", "btech", "b.sc", "bsc", "degree"]):
            rank = 3
        elif any(term in lower for term in ["diploma", "intermediate"]):
            rank = 2
        ranked.append((rank, text))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] or NOT_FOUND


def extract_portfolio(parsed: dict[str, Any], raw_text: str) -> str:
    github = parsed.get("github")
    if github:
        return str(github)
    matches = re.findall(r"(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)/[A-Za-z0-9_.-]+/?", raw_text, re.IGNORECASE)
    if matches:
        return matches[0]
    portfolio = re.findall(r"https?://[^\s]+", raw_text)
    for url in portfolio:
        if "linkedin.com" not in url.lower():
            return url
    return NOT_FOUND


def extract_relocation(raw_text: str) -> str:
    match = re.search(r"(willing\s+to\s+relocate|relocation)\s*[:\-]?\s*(yes|no|open|not\s+open)?", raw_text, re.IGNORECASE)
    if not match:
        return NOT_FOUND
    return _first_found(match.group(2), match.group(1))


def build_dashboard(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    ratings = [candidate["rating"] for candidate in candidates]
    experience_values = [
        years
        for years in (extract_years_number(candidate["structured"]["total_experience"]) for candidate in candidates)
        if years is not None
    ]
    shortlisted = [candidate for candidate in candidates if candidate["recommendation"] in {"Strong Hire", "Hire", "Consider"}]
    rejected = [candidate for candidate in candidates if candidate["recommendation"] == "Reject"]
    skill_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    for candidate in candidates:
        for values in candidate["skills_by_category"].values():
            skill_counter.update(values)
        missing_counter.update(candidate["missing_skills"])

    return {
        "total_candidates": len(candidates),
        "shortlisted": len(shortlisted),
        "rejected": len(rejected),
        "average_experience": round(sum(experience_values) / len(experience_values), 1) if experience_values else 0,
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
        "top_10_candidates": [
            {
                "candidate_name": candidate["report_row"]["Candidate Name"],
                "rating": candidate["rating"],
                "recommendation": candidate["recommendation"],
            }
            for candidate in candidates[:10]
        ],
        "top_skills_found": [skill for skill, _ in skill_counter.most_common(15)],
        "missing_skills_across_candidates": [skill for skill, _ in missing_counter.most_common(15)],
    }


def build_ats_report_xlsx(report: dict[str, Any]) -> bytes:
    candidates = report["candidates"]
    dashboard = report["dashboard"]
    job = report["job"]

    report_rows = [REPORT_COLUMNS]
    for candidate in candidates:
        report_rows.append([candidate["report_row"].get(column, NOT_FOUND) for column in REPORT_COLUMNS])

    dashboard_rows = [
        ["ATS Screening Dashboard", ""],
        ["Job Title", job.get("title") or NOT_FOUND],
        ["Total Candidates", dashboard["total_candidates"]],
        ["Shortlisted", dashboard["shortlisted"]],
        ["Rejected", dashboard["rejected"]],
        ["Average Experience", dashboard["average_experience"]],
        ["Average Rating", dashboard["average_rating"]],
        [],
        ["Top 10 Candidates", "Rating", "Recommendation"],
    ]
    dashboard_rows.extend(
        [item["candidate_name"], item["rating"], item["recommendation"]]
        for item in dashboard["top_10_candidates"]
    )
    dashboard_rows.extend([[], ["Top Skills Found"], *[[skill] for skill in dashboard["top_skills_found"]]])
    dashboard_rows.extend([[], ["Missing Skills Across Candidates"], *[[skill] for skill in dashboard["missing_skills_across_candidates"]]])

    matrix_rows = [["Candidate Name", "Requirement", "Match"]]
    for candidate in candidates:
        name = candidate["report_row"]["Candidate Name"]
        for requirement, match in candidate["requirement_matches"].items():
            matrix_rows.append([name, requirement, match])

    category_headers = ["Candidate Name", *SKILL_TAXONOMY.keys()]
    category_rows = [category_headers]
    for candidate in candidates:
        category_rows.append(
            [
                candidate["report_row"]["Candidate Name"],
                *[_join_or_not_found(candidate["skills_by_category"][category]) for category in SKILL_TAXONOMY],
            ]
        )

    return create_xlsx(
        [
            ("Dashboard", dashboard_rows),
            ("Candidate Report", report_rows),
            ("Requirement Matrix", matrix_rows),
            ("Skill Categories", category_rows),
        ]
    )


RESUME_DATA_COLUMNS = [
    "Candidate Name",
    "Email",
    "Phone Number",
    "Experience",
    "Location",
    "Key Skills",
    "JD Rating (/10)",
]


def build_resume_data_xlsx(resumes: list[Any], job: Any | None = None) -> bytes:
    requirements = build_job_requirements(job) if job is not None else []
    items: list[dict[str, Any]] = []

    for resume in resumes:
        current_version = getattr(resume, "current_version", None)
        if current_version is None or not getattr(current_version, "parsed_json", None):
            continue
        try:
            parsed = json.loads(current_version.parsed_json or "{}")
        except Exception:
            continue

        analysis = analyze_candidate(job, resume, parsed, requirements) if job is not None else None
        row = build_resume_data_row(resume, parsed, analysis)
        items.append({"row": row, "analysis": analysis, "structured": build_structured_resume(parsed)})

    items.sort(
        key=lambda item: float(item["row"].get("JD Rating (/10)") or 0)
        if isinstance(item["row"].get("JD Rating (/10)"), (int, float))
        else -1,
        reverse=True,
    )

    data_rows = [RESUME_DATA_COLUMNS]
    data_rows.extend([[item["row"].get(column, NOT_FOUND) for column in RESUME_DATA_COLUMNS] for item in items])

    dashboard_rows = build_resume_data_dashboard(items, job)
    matrix_rows = [["Candidate Name", "Requirement", "Match"]]
    if job is not None:
        for item in items:
            analysis = item["analysis"]
            if not analysis:
                continue
            name = analysis["report_row"]["Candidate Name"]
            for requirement, match in analysis["requirement_matches"].items():
                matrix_rows.append([name, requirement, match])

    category_headers = ["Candidate Name", *SKILL_TAXONOMY.keys()]
    category_rows = [category_headers]
    for item in items:
        analysis = item["analysis"]
        if analysis:
            category_rows.append(
                [
                    analysis["report_row"]["Candidate Name"],
                    *[_join_or_not_found(analysis["skills_by_category"][category]) for category in SKILL_TAXONOMY],
                ]
            )
        else:
            structured = item["structured"]
            category_rows.append([structured.get("name") or NOT_FOUND, *["Not Scored" for _ in SKILL_TAXONOMY]])

    return create_xlsx(
        [
            ("Resume Data", data_rows),
            ("Dashboard", dashboard_rows),
            ("ATS Match Matrix", matrix_rows),
            ("Skill Categories", category_rows),
        ]
    )


def build_resume_data_row(resume: Any, parsed: dict[str, Any], analysis: dict[str, Any] | None) -> dict[str, Any]:
    structured = build_structured_resume(parsed)
    candidate = getattr(resume, "candidate", None)
    raw_text = str(parsed.get("parsed_text") or "")

    if analysis is not None:
        report_row = analysis["report_row"]
        total_experience = report_row.get("Experience", NOT_FOUND)
        rating = analysis["rating"]
    else:
        total_experience = extract_total_experience(raw_text, structured)
        rating = "Not Scored"

    return {
        "Candidate Name": _first_found(structured.get("name")),
        "Email": _first_found(structured.get("email")),
        "Phone Number": _first_found(structured.get("phone")),
        "Experience": total_experience,
        "Location": _first_found(structured.get("location")),
        "Key Skills": _join_or_not_found(structured.get("skills") or []),
        "JD Rating (/10)": rating,
    }


def build_resume_data_dashboard(items: list[dict[str, Any]], job: Any | None) -> list[list[Any]]:
    analyses = [item["analysis"] for item in items if item["analysis"]]
    ratings = [analysis["rating"] for analysis in analyses]
    experience_values = [
        years
        for years in (
            extract_years_number(str(item["row"].get("Experience") or ""))
            for item in items
        )
        if years is not None
    ]
    shortlisted = [
        analysis
        for analysis in analyses
        if analysis["recommendation"] in {"Strong Hire", "Hire", "Consider"}
    ]
    rejected = [analysis for analysis in analyses if analysis["recommendation"] == "Reject"]
    skill_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()
    for item in items:
        structured = item["structured"]
        skill_counter.update(structured.get("skills") or [])
        analysis = item["analysis"]
        if analysis:
            missing_counter.update(analysis["missing_skills"])

    rows = [
        ["Resume Data ATS Export", ""],
        ["Job Title", getattr(job, "title", None) if job is not None else "Not Scored"],
        ["Total Resumes", len(items)],
        ["Scored Resumes", len(analyses)],
        ["Shortlisted", len(shortlisted)],
        ["Rejected", len(rejected)],
        ["Average Experience", round(sum(experience_values) / len(experience_values), 1) if experience_values else 0],
        ["Average Rating", round(sum(ratings) / len(ratings), 1) if ratings else "Not Scored"],
        [],
        ["Top Candidates", "Rating", "Recommendation", "Email"],
    ]
    rows.extend(
        [
            analysis["report_row"]["Candidate Name"],
            analysis["rating"],
            analysis["recommendation"],
            analysis["report_row"]["Email"],
        ]
        for analysis in analyses[:10]
    )
    rows.extend([[], ["Top Skills Found"], *[[skill] for skill, _ in skill_counter.most_common(15)]])
    rows.extend([[], ["Missing Skills Across Candidates"], *[[skill] for skill, _ in missing_counter.most_common(15)]])
    return rows


def format_report_date(value: Any) -> str:
    if value is None:
        return NOT_FOUND
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def format_experience_details(items: list[dict[str, Any]]) -> str:
    details: list[str] = []
    for item in items:
        role = " at ".join(part for part in [item.get("title"), item.get("company")] if part)
        dates = " - ".join(part for part in [item.get("start_date"), item.get("end_date")] if part)
        description = str(item.get("description") or "").strip()
        detail = " | ".join(part for part in [role, dates, description] if part)
        if detail:
            details.append(detail)
    return "; ".join(details) if details else NOT_FOUND


def format_education_details(items: list[dict[str, Any]]) -> str:
    details: list[str] = []
    for item in items:
        detail = " | ".join(
            part
            for part in [
                item.get("degree"),
                item.get("field"),
                item.get("institution"),
                item.get("graduation_date"),
                item.get("gpa"),
            ]
            if part
        )
        if detail:
            details.append(detail)
    return "; ".join(details) if details else NOT_FOUND


def create_xlsx(sheets: list[tuple[str, list[list[Any]]]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, (name, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows, name))
    return output.getvalue()


def _worksheet_xml(rows: list[list[Any]], sheet_name: str = "") -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            if value is None:
                value = ""
            cell_ref = f"{_col_letter(col_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ' s="2"'
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{cell_ref}"{style}><v>{value}</v></c>')
            else:
                text = escape(_repair_export_text(value))
                # Preserve spaces and ensure proper XML handling
                cells.append(f'<c r="{cell_ref}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>')
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    max_cols = max((len(row) for row in rows), default=1)
    max_rows = max(len(rows), 1)
    # Improved column widths
    cols = "".join(f'<col min="{i}" max="{i}" width="{_column_width(i, sheet_name)}" customWidth="1"/>' for i in range(1, max_cols + 1))
    dimension = f"A1:{_col_letter(max_cols)}{max_rows}"
    auto_filter = ""
    if sheet_name != "Dashboard" and len(rows) > 1 and max_cols > 1:
        auto_filter = f'<autoFilter ref="A1:{_col_letter(max_cols)}{max_rows}"/>'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f"<cols>{cols}</cols><sheetData>{''.join(xml_rows)}</sheetData>{auto_filter}</worksheet>"
    )


def _content_types_xml(sheet_count: int) -> str:
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{sheets}</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheets: list[tuple[str, list[list[Any]]]]) -> str:
    sheet_xml = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_xml}</sheets></workbook>"
    )


def _workbook_rels_xml(sheet_count: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, sheet_count + 1)
    )
    rels += (
        f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="10"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Calibri"/></font></fonts>'
        '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF0F766E"/><bgColor indexed="64"/></patternFill></fill></fills>'
        '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFD9E2EC"/></left><right style="thin"><color rgb="FFD9E2EC"/></right><top style="thin"><color rgb="FFD9E2EC"/></top><bottom style="thin"><color rgb="FFD9E2EC"/></bottom><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="1" applyFill="1" applyFont="1" applyBorder="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="1" applyBorder="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>'
        "</styleSheet>"
    )


def _col_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _column_width(index: int, sheet_name: str = "") -> int:
    if sheet_name == "Resume Data":
        widths = {
            1: 24,
            2: 32,
            3: 20,
            4: 14,
            5: 22,
            6: 72,
            7: 14,
        }
        return widths.get(index, 20)
    if index in {25, 26, 27, 35, 36, 37, 38, 39}:  # Summary, Experience Details, Education, Reason, Interview Questions
        return 55
    if index in {15, 16, 17, 18, 19, 20, 21, 22, 23, 24}:
        return 45
    if index in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 34}:
        return 28
    if index in {28, 29, 30, 31, 32, 33}:
        return 35
    return 20


def _first_found(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = _repair_export_text(value)
        if text:
            return text
    return NOT_FOUND


def _join_or_not_found(values: list[str]) -> str:
    cleaned = _unique(values)
    return ", ".join(cleaned) if cleaned else NOT_FOUND


def _unique(values: list[str]) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        cleaned = _repair_export_text(value)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", " ", value.lower()).strip()
