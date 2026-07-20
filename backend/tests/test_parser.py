import os
import sys
import tempfile

import pytest

# Ensure the backend project root is on sys.path so `app` package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.parser.extractor import file_hash, extract_text
from app.services.parser import nlp
from app.services.parser.structured import build_structured_resume


def test_file_hash_and_extract_text(tmp_path):
    p = tmp_path / "sample.txt"
    content = (
        "John Doe\n"
        "Email: john@example.com\n"
        "Phone: +1 555-123-4567\n"
        "Skills: Python, React\n"
        "Experience\n"
        "Company X 2018-2020\n"
    )
    p.write_text(content, encoding="utf-8")
    h = file_hash(str(p))
    assert isinstance(h, str) and len(h) == 64
    text, meta = extract_text(str(p))
    assert "John Doe" in text
    assert meta.get("method") == "plain_text"


def test_extract_text_from_pdf_keeps_page_count_before_close(tmp_path):
    fitz = pytest.importorskip("fitz")

    p = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Jane Doe Python Engineer")
    doc.save(str(p))
    doc.close()

    text, meta = extract_text(str(p))

    assert "Jane Doe" in text
    assert meta.get("pages") == 1


def test_extract_contact_info():
    text = (
        "Contact: john.doe@example.com, +44 20 7946 0958. "
        "LinkedIn: https://linkedin.com/in/johndoe. "
        "GitHub: https://github.com/johndoe"
    )
    c = nlp.extract_contact_info(text)
    assert c["emails"] and c["emails"][0]["value"] == "john.doe@example.com"
    assert c["linkedin"] is not None
    assert c["github"] is not None


def test_extract_name_from_resume_lines_and_email_fallback():
    text = (
        "SUMMARY\n"
        "Aspiring SOC Analyst with hands-on experience\n"
        "CONTACT\n"
        "Email: burrarajesh192@gmail.com\n"
        "RAJESH BURRA\n"
        "Skills\n"
    )
    assert nlp.extract_name(text)["value"] == "Rajesh Burra"

    email_only = "Contact\nEmail: adityakumar.sparda@gmail.com\nCore Competencies\nMicrosoft Office"
    assert nlp.extract_name(email_only)["value"] == "Adityakumar Sparda"


def test_extract_name_ignores_professional_section_headers():
    professional_summary = (
        "Professional Summary\n"
        "premkumar.tpk.2295@gmail.com\n"
        "DevOps Engineer with Azure and Terraform experience\n"
    )
    assert nlp.extract_name(professional_summary)["value"] == "Premkumar Tpk"

    professional_experience = (
        "Professional Experience\n"
        "itssabeeh@gmail.com\n"
        "Certified AZ-400 and AZ-104 Cloud Engineer\n"
    )
    assert nlp.extract_name(professional_experience)["value"] == "Itssabeeh"


def test_extract_name_from_title_line_and_ignores_skill_fragments():
    text = (
        "Shaju NV \u2013 Azure Cloud DevOps Engineer\n"
        "Bengaluru, Karnataka, India | email: shajuga110@gmail.com\n"
        "Experience\n"
        "Azure DevOps and Powershell\n"
    )
    assert nlp.extract_name(text)["value"] == "Shaju NV"

    skill_fragment = "Summary\nAzure DevOps and Powershell\nemail: shajuga110@gmail.com\n"
    assert nlp.extract_name(skill_fragment)["value"] == "Shajuga"


def test_extract_name_prefers_header_over_company_and_action_lines():
    prem_text = (
        "Prem Kumar\n"
        "DevOps Engineer | AWS | Azure | Kubernetes\n"
        "+91 9014235762 | premkumar.tpk.2295@gmail.com\n"
        "PROFESSIONAL SUMMARY\n"
        "DevOps Engineer with 4+ years of experience.\n"
        "Tech Mahindra — Software Engineer (DevOps)\n"
    )
    assert nlp.extract_name(prem_text)["value"] == "Prem Kumar"

    sathavahana_text = (
        "A. Sathavahana Reddy\n"
        "Senior Azure Cloud & DevOps Engineer\n"
        "asathavahanareddy24@gmail.com | +91-7989483911 | Bangalore, India\n"
        "PROFESSIONAL SUMMARY\n"
        "Senior Azure Cloud & DevOps Engineer with 6.3+ years of experience.\n"
        "Enforced IaC Governance Standards\n"
    )
    assert nlp.extract_name(sathavahana_text)["value"] == "A. Sathavahana Reddy"


def test_extract_name_from_filename_fallback():
    assert nlp.extract_name_from_filename("0486f493-2c0f-4d14-b679-ada77ed81d0f_ShajuNV.pdf") == "Shaju NV"
    assert nlp.extract_name_from_filename("resume_final.pdf") is None


def test_company_extraction_ignores_certification_headers():
    text = (
        "Professional Experience\n"
        "Certified AZ-400 and AZ-104 Cloud Engineer\n"
        "Skills\n"
        "Azure DevOps, Terraform, Kubernetes\n"
        "Infrastructure as Code: Terraform\n"
    )
    assert nlp.extract_companies_and_designations(text) == []


def test_extract_skills_and_languages():
    text = "Experienced with Python, JavaScript, Docker and AWS. Languages: English, Hindi"
    skills = nlp.extract_skills(text)
    names = [s["name"] for s in skills]
    assert any("python" in n.lower() for n in names)
    langs = nlp.extract_languages(text)
    assert any(l["name"] == "English" for l in langs)


def test_extract_experience_education_certification():
    text = (
        "Senior Engineer at Acme Corp\n"
        "2019 - Present\n"
        "Education\n"
        "Bachelor of Science in Computer Science\n"
        "Certifications\n"
        "AWS Certified Solutions Architect\n"
    )
    exps = nlp.extract_experiences(text)
    assert exps
    eds = nlp.extract_education(text)
    assert any("Bachelor" in e["raw"] for e in eds)
    certs = nlp.extract_certifications(text)
    assert any("AWS" in c["raw"] or "aws" in c["raw"].lower() for c in certs)


def test_salary_and_notice():
    text = "Current CTC: 12,00,000 Expected CTC: 15,00,000 Notice period: 2 months"
    s = nlp.extract_salary_info(text)
    assert s.get("current_ctc") is not None
    assert s.get("expected_ctc") is not None
    np = nlp.extract_notice_period(text)
    assert np is not None


def test_salary_package_variants():
    text = "Current Package - 6.5 LPA\nExpected Package: 8 LPA\nNotice Period: 30 days"
    s = nlp.extract_salary_info(text)
    assert s["current_ctc"] == "6.5 LPA"
    assert s["expected_ctc"] == "8 LPA"

    compact = "CCTC: INR 45,000 per month | ECTC - negotiable"
    compact_salary = nlp.extract_salary_info(compact)
    assert compact_salary["current_ctc"] == "INR 45,000 per month"
    assert compact_salary["expected_ctc"] == "negotiable"


def test_build_structured_resume_exact_shape_from_parsed_text():
    parsed = {
        "full_name": {"value": "Mettu Vaishnavi", "confidence": 0.75},
        "emails": [{"value": "mettuvaishnavi22@gmail.com"}],
        "phones": [{"value": "+91-9515422701"}],
        "skills": [{"name": "java"}, {"name": "sql"}],
        "parsed_text": (
            "METTU VAISHNAVI\n"
            "Quality Assurance & Software Testing | Fresher\n"
            "mettuvaishnavi22@gmail.com | +91-9515422701 | Hyderabad, India\n"
            "PROFESSIONAL SUMMARY\n"
            "Detail-oriented fresher with a strong foundation in Manual Testing, Java, and SQL.\n"
            "TECHNICAL SKILLS\n"
            "Manual Testing: Test Case Design, Functional Testing\n"
            "Automation Testing: Selenium WebDriver (Java), TestNG Framework\n"
            "EDUCATION\n"
            "Master of Computer Applications (MCA)\n"
            "2024 - 2026\n"
            "Megha College of Engineering\n"
            "Bachelor of Computer Science (B.Sc. CS)\n"
            "2021 - 2024\n"
            "Megha Women's Degree College, Hyderabad\n"
            "CERTIFICATIONS\n"
            "Manual Testing and SQL Certification\n"
        ),
    }

    structured = build_structured_resume(parsed)

    assert list(structured.keys()) == [
        "name",
        "email",
        "phone",
        "location",
        "linkedin",
        "summary",
        "skills",
        "experience",
        "education",
        "certifications",
    ]
    assert structured["name"] == "Mettu Vaishnavi"
    assert structured["email"] == "mettuvaishnavi22@gmail.com"
    assert structured["phone"] == "+91-9515422701"
    assert structured["location"] == "Hyderabad, India"
    assert structured["summary"].startswith("Detail-oriented fresher")
    assert "Manual Testing" in structured["skills"]
    assert structured["education"][0] == {
        "institution": "Megha College of Engineering",
        "degree": "Master of Computer Applications (MCA)",
        "field": "",
        "graduation_date": "2026",
        "gpa": "",
    }
    assert structured["certifications"] == ["Manual Testing and SQL Certification"]


def test_structured_location_ignores_spaced_headings_and_cleans_icons():
    no_location = build_structured_resume(
        {
            "full_name": {"value": "Nagarjuna Reddy", "confidence": 0.75},
            "emails": [{"value": "nagarjunareddym4@gmail.com"}],
            "phones": [{"value": "+91-9347205416"}],
            "parsed_text": (
                "Nagarjuna Reddy\n"
                "Azure Cloud & Infrastructure Engineer | 3+ Years Experience\n"
                "+91-9347205416 | nagarjunareddym4@gmail.com | linkedin.com/in/nagarjuna-reddy-93497818b\n"
                "S U M M A R Y\n"
                "Cloud Engineer & Infrastructure Engineer with 3+ years of experience.\n"
            ),
        }
    )
    assert no_location["location"] == ""
    assert no_location["summary"].startswith("Cloud Engineer")

    icon_location = build_structured_resume(
        {
            "full_name": {"value": "A. Sathavahana Reddy", "confidence": 0.75},
            "emails": [{"value": "asathavahanareddy24@gmail.com"}],
            "phones": [{"value": "+91-7989483911"}],
            "parsed_text": (
                "A. Sathavahana Reddy\n"
                "Senior Azure Cloud & DevOps Engineer\n"
                "📧 asathavahanareddy24@gmail.com | 📧 +91-7989483911 | 📧 Bangalore, India\n"
                "PROFESSIONAL SUMMARY\n"
                "Senior Azure Cloud & DevOps Engineer with 6.3+ years of experience.\n"
            ),
        }
    )
    assert icon_location["location"] == "Bangalore, India"
