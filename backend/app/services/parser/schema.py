from typing import Any, Dict


def empty_output() -> Dict[str, Any]:
    return {
        "metadata": {},
        "full_name": {"value": None, "confidence": 0.0},
        "emails": [],
        "phones": [],
        "linkedin": None,
        "github": None,
        "skills": [],
        "experiences": [],
        "education": [],
        "certifications": [],
        "languages": [],
        "companies": [],
        "current_company": None,
        "current_ctc": None,
        "expected_ctc": None,
        "notice_period": None,
        "parsed_text": "",
    }
