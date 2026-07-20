import json
import os
import sys
import zipfile
from io import BytesIO
from types import SimpleNamespace

import fitz

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ats.masked_resume import build_masked_resume_pdf, build_masked_resumes_zip, masked_resume_filename


def _sample_resume() -> SimpleNamespace:
    parsed = {
        "structured": {
            "name": "Jane Engineer",
            "email": "jane@example.com",
            "phone": "+1 555 123 4567",
            "location": "New York",
            "linkedin": "https://linkedin.com/in/jane-engineer",
            "summary": "Senior DevOps engineer with Azure, Terraform, Kubernetes, and automation experience.",
            "skills": ["Azure", "Terraform", "Kubernetes", "Python", "PowerShell"],
            "experience": [
                {
                    "company": "Cloud Co",
                    "title": "Senior DevOps Engineer",
                    "start_date": "Jan 2020",
                    "end_date": "Present",
                    "location": "New York",
                    "description": "Led platform delivery at Cloud Co using Terraform and Kubernetes for Jane Engineer.",
                }
            ],
            "education": [
                {
                    "institution": "Example University",
                    "degree": "Bachelor of Technology",
                    "field": "Computer Science",
                    "graduation_date": "May 2018",
                    "gpa": "",
                }
            ],
            "certifications": ["Microsoft Azure Administrator Associate AZ-104"],
        }
    }
    return SimpleNamespace(
        id="resume-1",
        candidate_id="candidate-1",
        title="Jane Engineer Resume.pdf",
        candidate=SimpleNamespace(
            first_name="Jane",
            last_name="Engineer",
            email="jane@example.com",
            phone="+1 555 123 4567",
        ),
        current_version=SimpleNamespace(parsed_json=json.dumps(parsed)),
    )


def _pdf_text(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def test_masked_resume_pdf_uses_anonymous_template_without_identity_leaks():
    resume = _sample_resume()

    content = build_masked_resume_pdf(resume)
    text = _pdf_text(content)

    assert content.startswith(b"%PDF")
    assert "MASKED CANDIDATE RESUME" in text
    assert "CAND-" in text
    assert "Senior DevOps Engineer" in text
    assert "Employer 1" in text
    assert "Institution withheld" in text

    assert "Jane Engineer" not in text
    assert "jane@example.com" not in text
    assert "+1 555" not in text
    assert "linkedin.com" not in text
    assert "New York" not in text
    assert "Cloud Co" not in text
    assert "Example University" not in text


def test_masked_resume_zip_uses_masked_pdf_names_only():
    resume = _sample_resume()

    file_name = masked_resume_filename(resume)
    archive_content = build_masked_resumes_zip([resume])

    assert file_name.startswith("masked_CAND-")
    assert "Jane" not in file_name
    assert "Engineer" not in file_name

    with zipfile.ZipFile(BytesIO(archive_content)) as archive:
        names = archive.namelist()
        assert names == [file_name]
        assert archive.read(file_name).startswith(b"%PDF")
