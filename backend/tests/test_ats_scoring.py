import json

from app.services.ats.scoring import score_resume_against_job


class DummyJob:
    def __init__(self, skills, description=None, title=None, requirements=None):
        self.skills = skills
        self.description = description
        self.title = title
        self.requirements = requirements


def test_score_resume_against_job_with_matching_and_missing_skills():
    parsed_resume = {
        "skills": [{"name": "Python"}, {"name": "Docker"}],
        "experiences": [{"raw": "Senior Engineer at Acme Corp 2019 - Present"}],
        "education": [{"raw": "Bachelor of Science in Computer Science"}],
        "certifications": [{"raw": "AWS Certified Solutions Architect"}],
        "parsed_text": "Python Docker AWS Acme Corp Senior Engineer",
    }
    job = DummyJob(
        skills=json.dumps(["Python", "AWS"]),
        description="Seeking a Python engineer with AWS experience.",
        title="Software Engineer",
        requirements="Python, AWS, cloud",
    )

    score_data = score_resume_against_job(parsed_resume, job)

    assert 0.0 <= score_data["total_score"] <= 1.0
    assert score_data["matched_skills"] == ["python"]
    assert score_data["missing_skills"] == ["aws"]
    assert score_data["component_scores"]["skills"] == 0.5
    assert score_data["score_percentage"] == round(score_data["total_score"] * 100.0, 2)
    assert "recommendations" in score_data
    assert "weaknesses" in score_data
    assert "score_breakdown" in score_data
    assert "confidence_score" in score_data
    assert score_data["confidence_score"] > 0.0
    assert "similarity" in score_data["score_breakdown"]
