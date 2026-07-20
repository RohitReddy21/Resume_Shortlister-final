import json
import os
import sys
import zipfile
from io import BytesIO
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ats.screening_report import build_ats_report_xlsx, build_ats_screening_report, build_resume_data_xlsx


def test_ats_screening_report_scores_and_exports_xlsx():
    job = SimpleNamespace(
        id="job-1",
        title="Azure DevOps Engineer",
        description="Need Azure DevOps, Terraform, Docker, Kubernetes, Azure Monitor, PowerShell, Python, Git, Agile.",
        skills=json.dumps(["Azure DevOps", "Terraform", "Docker", "Kubernetes", "Python", "Git"]),
    )
    parsed = {
        "full_name": {"value": "Jane Engineer"},
        "emails": [{"value": "jane@example.com"}],
        "phones": [{"value": "+1 555 123 4567"}],
        "linkedin": "https://linkedin.com/in/jane",
        "skills": [
            {"name": "Azure DevOps"},
            {"name": "Terraform"},
            {"name": "Docker"},
            {"name": "Python"},
            {"name": "Git"},
            {"name": "PowerShell"},
        ],
        "experiences": [
            {"title": "DevOps Engineer", "company": "Cloud Co", "start_date": "Jan 2021", "end_date": "Present"}
        ],
        "education": [{"raw": "Bachelor of Technology"}],
        "certifications": [{"raw": "Microsoft Azure Administrator Associate AZ-104"}],
        "parsed_text": (
            "Jane Engineer\n"
            "jane@example.com\n"
            "Experience: 4 Years\n"
            "DevOps Engineer at Cloud Co\n"
            "Built Azure DevOps pipelines using Terraform, Docker, Python, PowerShell and Git.\n"
            "Microsoft Azure Administrator Associate AZ-104\n"
        ),
    }
    resume = SimpleNamespace(
        id="resume-1",
        title="jane.pdf",
        candidate=None,
        current_version=SimpleNamespace(parsed_json=json.dumps(parsed)),
    )

    report = build_ats_screening_report(job, [resume])

    assert report["dashboard"]["total_candidates"] == 1
    assert report["candidates"][0]["report_row"]["Candidate Name"] == "Jane Engineer"
    assert report["candidates"][0]["rating"] >= 7.0
    assert report["candidates"][0]["report_row"]["Recommendation"] in {"Strong Hire", "Hire", "Consider"}

    workbook = build_ats_report_xlsx(report)
    with zipfile.ZipFile(BytesIO(workbook)) as archive:
        names = set(archive.namelist())
    assert "xl/workbook.xml" in names
    assert "xl/worksheets/sheet1.xml" in names
    assert "xl/worksheets/sheet2.xml" in names

    resume_data_workbook = build_resume_data_xlsx([resume], job)
    with zipfile.ZipFile(BytesIO(resume_data_workbook)) as archive:
        names = set(archive.namelist())
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        sheet1 = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "xl/worksheets/sheet4.xml" in names
    assert "Resume Data" in workbook_xml
    assert 'sheet name="Resume Data" sheetId="1"' in workbook_xml
    assert "Jane Engineer" in sheet1
    assert "JD Rating (/10)" in sheet1
