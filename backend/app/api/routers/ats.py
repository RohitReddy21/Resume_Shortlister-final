import json
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.ats import Job, Resume, ResumeVersion
from app.schemas.ats import ATSScoreResponse
from app.services.ats.scoring import score_resume_against_job

router = APIRouter()


@router.get("/ats/score/{resume_id}/{job_id}", response_model=ATSScoreResponse)
def score_resume(resume_id: str, job_id: str, db: Session = Depends(get_db)) -> Dict:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="resume not found")

    if resume.current_version_id is None:
        raise HTTPException(status_code=400, detail="resume has not been parsed yet")

    version = db.get(ResumeVersion, resume.current_version_id)
    if version is None or not version.parsed_json:
        raise HTTPException(status_code=400, detail="parsed resume data is unavailable")

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    try:
        parsed_resume = json.loads(version.parsed_json)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not deserialize parsed resume JSON")

    score_data = score_resume_against_job(parsed_resume, job)
    return ATSScoreResponse(
        job_id=job_id,
        resume_id=resume_id,
        total_score=score_data["total_score"],
        score_percentage=score_data["score_percentage"],
        confidence_score=score_data.get("confidence_score", 0.0),
        weights=score_data["weights"],
        component_scores=score_data["component_scores"],
        score_breakdown=score_data.get("score_breakdown", {}),
        matched_skills=score_data["matched_skills"],
        missing_skills=score_data["missing_skills"],
        strengths=score_data["strengths"],
        weaknesses=score_data["weaknesses"],
        recommendations=score_data["recommendations"],
        explanation=score_data.get("explanation"),
    )
