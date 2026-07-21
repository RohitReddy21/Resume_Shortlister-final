import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.paths import get_resume_dir
from app.models.ats import (
    Application,
    Candidate,
    CandidateSkill,
    Certification,
    Comment,
    Education,
    Experience,
    Interview,
    Job,
    Notification,
    Resume,
    ResumeVersion,
)
from app.models.ats.v3_models import (
    InterviewFeedback,
    InterviewPanelMember,
    Offer,
    OfferDocument,
    JoiningRecord,
    CandidateCommunication,
    CandidateChecklistItem,
    RecruiterTask,
    CandidateDocumentVault,
)
from app.models.ats.activity_log import ActivityLog
from app.models.user import User
from app.schemas.pipeline import (
    ActivityOut,
    ApplicationCreate,
    ApplicationKanbanOut,
    ApplicationUpdate,
    ApplicationStageUpdate,
    CandidateCreate,
    CandidateCompensationUpdate,
    CandidateUpdate,
    CandidateSnippet,
    CommentCreate,
    CommentOut,
    CommentUpdate,
    KanbanBoardOut,
    NotificationOut,
    PIPELINE_STAGES,
    InterviewCreate,
    InterviewUpdate,
    InterviewOut,
)
from app.services.email_service import EmailService
from app.services.ats.scoring import score_resume_against_job

router = APIRouter(tags=["pipeline"])
settings = get_settings()
RESUME_DIR = get_resume_dir()

VALID_STAGES = set(PIPELINE_STAGES)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _app_to_kanban_out(app: Application) -> ApplicationKanbanOut:
    candidate_out = CandidateSnippet(
        id=app.candidate.id,
        first_name=app.candidate.first_name,
        last_name=app.candidate.last_name,
        email=app.candidate.email,
        headline=app.candidate.headline,
    )
    comment_count = len(app.comments) if app.comments else 0
    return ApplicationKanbanOut(
        id=app.id,
        status=app.status,
        pipeline_order=app.pipeline_order or 0,
        match_score=app.match_score,
        match_confidence=app.match_confidence,
        shortlist_reason=app.shortlist_reason,
        source=app.source,
        notes=app.notes,
        applied_at=app.applied_at,
        updated_at=app.updated_at,
        candidate=candidate_out,
        comment_count=comment_count,
    )


def _log_activity(
    db: Session,
    action: str,
    details: str,
    user_id: str | None,
    application_id: str,
    candidate_id: str | None = None,
    job_id: str | None = None,
) -> None:
    log = ActivityLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        application_id=application_id,
        candidate_id=candidate_id,
        job_id=job_id,
        action=action,
        details=details,
        source="pipeline",
    )
    db.add(log)


def _score_resume_for_job(db: Session, resume_id: str | None, job: Job) -> tuple[dict[str, Any], str, str]:
    if not resume_id:
        raise HTTPException(status_code=400, detail="Parsed resume is required for automated shortlisting")

    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.current_version_id is None:
        raise HTTPException(status_code=400, detail="Resume has not been parsed yet")

    version = db.get(ResumeVersion, resume.current_version_id)
    if version is None or not version.parsed_json:
        raise HTTPException(status_code=400, detail="Parsed resume data is unavailable")

    try:
        parsed_resume = json.loads(version.parsed_json)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not deserialize parsed resume JSON") from exc

    score_data = score_resume_against_job(parsed_resume, job)
    threshold = settings.ats_shortlist_threshold
    score_percentage = score_data["score_percentage"]
    if score_percentage >= threshold:
        return score_data, "Shortlisted", f"ATS score {score_percentage:.2f}% met the {threshold:.0f}% shortlist threshold."
    return score_data, "Screening", f"ATS score {score_percentage:.2f}% is below the {threshold:.0f}% shortlist threshold."


def _format_locations(locations: str | None, fallback: str | None) -> str:
    if not locations:
        return fallback or "No location set"
    try:
        parsed = json.loads(locations)
        if isinstance(parsed, list):
            values = [str(item) for item in parsed if item]
            return ", ".join(values) if values else (fallback or "No location set")
    except Exception:
        pass
    return locations


def _is_internal_candidate_email(email: str | None) -> bool:
    return bool(email and email.startswith("unknown+") and email.endswith("@resumeparser.ai"))


def _candidate_display_name(candidate: Candidate | None) -> str | None:
    if candidate is None:
        return None
    if (
        candidate.first_name == "Unknown"
        and candidate.last_name == "Candidate"
        and _is_internal_candidate_email(candidate.email)
    ):
        return None
    return f"{candidate.first_name} {candidate.last_name}".strip() or None


def _candidate_display_email(candidate: Candidate | None) -> str | None:
    if candidate is None or _is_internal_candidate_email(candidate.email):
        return None
    return candidate.email


def _find_saved_resume_path(resume: Resume) -> str | None:
    prefix = f"{resume.id}_"
    if not os.path.isdir(RESUME_DIR):
        return None
    for file_name in os.listdir(RESUME_DIR):
        if file_name.startswith(prefix):
            return os.path.join(RESUME_DIR, file_name)
    return None


def _remove_saved_resume_files(paths: list[str]) -> None:
    resume_root = os.path.abspath(RESUME_DIR)
    for path in paths:
        candidate_path = os.path.abspath(path)
        if candidate_path.startswith(resume_root) and os.path.exists(candidate_path):
            os.remove(candidate_path)


def _delete_resume_rows(db: Session, resume_ids: list[str]) -> None:
    if not resume_ids:
        return
    db.query(Application).filter(Application.resume_id.in_(resume_ids)).update({"resume_id": None}, synchronize_session=False)
    db.query(Resume).filter(Resume.id.in_(resume_ids)).update({"current_version_id": None}, synchronize_session=False)
    db.flush()
    db.query(ResumeVersion).filter(ResumeVersion.resume_id.in_(resume_ids)).delete(synchronize_session=False)
    db.query(Resume).filter(Resume.id.in_(resume_ids)).delete(synchronize_session=False)


def _delete_application_rows(db: Session, application_ids: list[str]) -> None:
    if not application_ids:
        return
    # First get all interviews linked to these applications
    interviews = db.query(Interview).filter(Interview.application_id.in_(application_ids)).all()
    interview_ids = [i.id for i in interviews]
    
    # Delete interview-related models first
    if interview_ids:
        db.query(InterviewFeedback).filter(InterviewFeedback.interview_id.in_(interview_ids)).delete(synchronize_session=False)
        db.query(InterviewPanelMember).filter(InterviewPanelMember.interview_id.in_(interview_ids)).delete(synchronize_session=False)
    
    # Then delete the rest
    db.query(Comment).filter(Comment.application_id.in_(application_ids)).delete(synchronize_session=False)
    db.query(Interview).filter(Interview.application_id.in_(application_ids)).delete(synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.application_id.in_(application_ids)).delete(synchronize_session=False)
    db.query(Application).filter(Application.id.in_(application_ids)).delete(synchronize_session=False)


def _delete_candidate_profile_rows(db: Session, candidate_id: str) -> None:
    # First get all offers and interviews linked to this candidate
    offers = db.query(Offer).filter(Offer.candidate_id == candidate_id).all()
    offer_ids = [o.id for o in offers]
    interviews = db.query(Interview).filter(Interview.candidate_id == candidate_id).all()
    interview_ids = [i.id for i in interviews]
    
    # Delete offer-related models first
    if offer_ids:
        db.query(OfferDocument).filter(OfferDocument.offer_id.in_(offer_ids)).delete(synchronize_session=False)
        db.query(JoiningRecord).filter(JoiningRecord.offer_id.in_(offer_ids)).delete(synchronize_session=False)
    
    # Delete interview-related models first
    if interview_ids:
        db.query(InterviewFeedback).filter(InterviewFeedback.interview_id.in_(interview_ids)).delete(synchronize_session=False)
        db.query(InterviewPanelMember).filter(InterviewPanelMember.interview_id.in_(interview_ids)).delete(synchronize_session=False)
    
    # Delete all other candidate-linked v3 models
    db.query(Offer).filter(Offer.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(JoiningRecord).filter(JoiningRecord.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(CandidateCommunication).filter(CandidateCommunication.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(CandidateChecklistItem).filter(CandidateChecklistItem.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(RecruiterTask).filter(RecruiterTask.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(CandidateDocumentVault).filter(CandidateDocumentVault.candidate_id == candidate_id).delete(synchronize_session=False)
    
    # Delete original models
    db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(Experience).filter(Experience.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(Education).filter(Education.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(Certification).filter(Certification.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(Interview).filter(Interview.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.candidate_id == candidate_id).delete(synchronize_session=False)
    db.query(Candidate).filter(Candidate.id == candidate_id).delete(synchronize_session=False)


def _remove_rejected_application_data(db: Session, app: Application) -> dict[str, Any]:
    candidate = app.candidate
    candidate_id = app.candidate_id
    application_id = app.id
    candidate_name = _candidate_display_name(candidate) or _candidate_display_email(candidate) or "Rejected candidate"

    other_applications = (
        db.query(Application.id)
        .filter(Application.candidate_id == candidate_id, Application.id != application_id)
        .all()
    )
    if other_applications:
        _delete_application_rows(db, [application_id])
        return {
            "deleted": True,
            "deleted_scope": "application",
            "application_id": application_id,
            "candidate_id": candidate_id,
            "message": f"{candidate_name}'s rejected application was removed. Other applications were kept.",
        }

    resumes = list(candidate.resumes or [])
    resume_ids = [resume.id for resume in resumes]
    resume_paths = [path for resume in resumes if (path := _find_saved_resume_path(resume))]
    application_ids = [row.id for row in db.query(Application.id).filter(Application.candidate_id == candidate_id).all()]

    _delete_application_rows(db, application_ids)
    _delete_resume_rows(db, resume_ids)
    _delete_candidate_profile_rows(db, candidate_id)
    _remove_saved_resume_files(resume_paths)

    return {
        "deleted": True,
        "deleted_scope": "candidate",
        "application_id": application_id,
        "candidate_id": candidate_id,
        "resume_ids": resume_ids,
        "message": f"{candidate_name} was rejected and removed with candidate, resume, and parsed data.",
    }


def _candidate_to_dict(candidate: Candidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "name": _candidate_display_name(candidate),
        "email": _candidate_display_email(candidate),
        "raw_email": candidate.email,
        "phone": candidate.phone,
        "address": candidate.address,
        "linkedin": candidate.linkedin,
        "github": candidate.github,
        "portfolio": candidate.portfolio,
        "headline": candidate.headline,
        "current_company": candidate.current_company,
        "current_designation": candidate.current_designation,
        "total_experience": candidate.total_experience,
        "relevant_experience": candidate.relevant_experience,
        "current_package": candidate.current_package,
        "expected_package": candidate.expected_package,
        "notice_period": candidate.notice_period,
        "preferred_location": candidate.preferred_location,
        "employment_type": candidate.employment_type,
        "summary": candidate.summary,
        "resume_count": len(candidate.resumes) if candidate.resumes else 0,
        "application_count": len(candidate.applications) if candidate.applications else 0,
        "created_at": candidate.created_at,
        "updated_at": candidate.updated_at,
    }


def _application_to_table_row(app: Application) -> dict[str, Any]:
    resume_status = None
    if app.resume is not None:
        resume_status = "parsed" if app.resume.current_version_id else "processing"

    return {
        "id": app.id,
        "status": app.status,
        "pipeline_order": app.pipeline_order or 0,
        "match_score": app.match_score,
        "match_confidence": app.match_confidence,
        "shortlist_reason": app.shortlist_reason,
        "source": app.source,
        "notes": app.notes,
        "applied_at": app.applied_at,
        "updated_at": app.updated_at,
        "candidate": {
            "id": app.candidate.id,
            "name": _candidate_display_name(app.candidate),
            "email": _candidate_display_email(app.candidate),
            "first_name": app.candidate.first_name,
            "last_name": app.candidate.last_name,
            "raw_email": app.candidate.email,
            "phone": app.candidate.phone,
            "headline": app.candidate.headline,
            "current_package": app.candidate.current_package,
            "expected_package": app.candidate.expected_package,
            "notice_period": app.candidate.notice_period,
        },
        "job": {
            "id": app.job.id,
            "title": app.job.title,
            "status": app.job.status,
        },
        "resume": {
            "id": app.resume.id if app.resume else None,
            "title": app.resume.title if app.resume else None,
            "status": resume_status,
        },
        "comment_count": len(app.comments) if app.comments else 0,
    }


def _comment_to_out(comment: Comment) -> CommentOut:
    mentions_list: List[str] = json.loads(comment.mentions or "[]")
    return CommentOut(
        id=comment.id,
        application_id=comment.application_id,
        author_id=comment.author_id,
        author_name=comment.author.full_name if comment.author else "Unknown",
        body=comment.body,
        mentions=mentions_list,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ── Board ─────────────────────────────────────────────────────────────────────

@router.post("/candidates", status_code=201)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> Any:
    email = payload.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="Candidate email is required")
    existing = db.query(Candidate).filter(func.lower(Candidate.email) == email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Candidate email already exists")

    candidate = Candidate(
        id=str(uuid.uuid4()),
        first_name=payload.first_name.strip() or "Unknown",
        last_name=(payload.last_name or "").strip(),
        email=email,
        phone=payload.phone.strip() if payload.phone else None,
        address=payload.address.strip() if payload.address else None,
        linkedin=payload.linkedin.strip() if payload.linkedin else None,
        github=payload.github.strip() if payload.github else None,
        portfolio=payload.portfolio.strip() if payload.portfolio else None,
        headline=payload.headline.strip() if payload.headline else None,
        current_company=payload.current_company.strip() if payload.current_company else None,
        current_designation=payload.current_designation.strip() if payload.current_designation else None,
        total_experience=payload.total_experience.strip() if payload.total_experience else None,
        relevant_experience=payload.relevant_experience.strip() if payload.relevant_experience else None,
        current_package=payload.current_package.strip() if payload.current_package else None,
        expected_package=payload.expected_package.strip() if payload.expected_package else None,
        notice_period=payload.notice_period.strip() if payload.notice_period else None,
        preferred_location=payload.preferred_location.strip() if payload.preferred_location else None,
        employment_type=payload.employment_type.strip() if payload.employment_type else None,
        summary=payload.summary.strip() if payload.summary else None,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return _candidate_to_dict(candidate)


@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db)) -> Any:
    candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).limit(500).all()
    return [_candidate_to_dict(candidate) for candidate in candidates]


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> Any:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_to_dict(candidate)


@router.patch("/candidates/{candidate_id}")
def update_candidate(candidate_id: str, payload: CandidateUpdate, db: Session = Depends(get_db)) -> Any:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"]:
        email = str(updates["email"]).strip()
        existing = (
            db.query(Candidate)
            .filter(func.lower(Candidate.email) == email.lower(), Candidate.id != candidate.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Candidate email already exists")
        candidate.email = email
        updates.pop("email")

    for field, value in updates.items():
        if value is None:
            setattr(candidate, field, None)
        elif isinstance(value, str):
            setattr(candidate, field, value.strip())
        else:
            setattr(candidate, field, value)

    if not candidate.first_name:
        candidate.first_name = "Unknown"
    if candidate.last_name is None:
        candidate.last_name = ""

    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return _candidate_to_dict(candidate)


@router.delete("/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: str, db: Session = Depends(get_db)) -> None:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.query(ActivityLog).filter(ActivityLog.candidate_id == candidate.id).delete(synchronize_session=False)
    db.delete(candidate)
    db.commit()
    return None


@router.post("/applications", response_model=ApplicationKanbanOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Attach a candidate/resume to a job and place it on the pipeline board."""
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_id = payload.resume_id
    resume = db.get(Resume, resume_id) if resume_id else None
    if not resume:
        raise HTTPException(status_code=400, detail="Parsed resume is required for automated shortlisting")
    if resume.candidate_id != candidate.id:
        raise HTTPException(status_code=400, detail="Resume does not belong to this candidate")

    score_data, decided_status, shortlist_reason = _score_resume_for_job(db, resume_id, job)

    existing = (
        db.query(Application)
        .filter(Application.candidate_id == candidate.id, Application.job_id == job.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Candidate already has an application for this job")

    next_order = (
        db.query(func.max(Application.pipeline_order))
        .filter(Application.job_id == job.id, Application.status == decided_status)
        .scalar()
    )
    notes = payload.notes
    score_note = (
        f"{shortlist_reason} Matched skills: {', '.join(score_data['matched_skills']) or 'none'}. "
        f"Missing skills: {', '.join(score_data['missing_skills']) or 'none'}."
    )
    notes = f"{notes}\n{score_note}" if notes else score_note

    application = Application(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        job_id=job.id,
        resume_id=resume_id,
        status=decided_status,
        pipeline_order=(next_order or 0) + 1,
        match_score=score_data["score_percentage"],
        match_confidence=score_data.get("confidence_score"),
        shortlist_reason=shortlist_reason,
        source=payload.source,
        notes=notes,
    )
    db.add(application)
    db.flush()

    _log_activity(
        db,
        action="automated_shortlist",
        details=f"{decided_status} for {job.title}: {shortlist_reason}",
        user_id=current_user.id,
        application_id=application.id,
        candidate_id=candidate.id,
        job_id=job.id,
    )

    if candidate.user_id:
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                user_id=candidate.user_id,
                title="Application scored",
                message=f"Your application for {job.title} is in {decided_status}. {shortlist_reason}",
                link=f"/dashboard/pipeline?job={job.id}&app={application.id}",
                level="info",
            )
        )

    db.commit()
    db.refresh(application)
    return _app_to_kanban_out(application)


@router.get("/applications")
def list_applications(db: Session = Depends(get_db)) -> Any:
    """Return application rows for the candidate reference table."""
    applications = (
        db.query(Application)
        .order_by(Application.applied_at.desc())
        .all()
    )

    return [_application_to_table_row(app) for app in applications]


@router.patch("/applications/{app_id}")
def update_application(
    app_id: str,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    app = db.get(Application, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")

    updates = payload.model_dump(exclude_unset=True)
    old_stage = app.status
    if "status" in updates and updates["status"]:
        new_stage = updates["status"]
        if new_stage not in VALID_STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {new_stage}")
        if new_stage != old_stage:
            _log_activity(
                db,
                action="stage_change",
                details=f"Moved from {old_stage} to {new_stage}",
                user_id=current_user.id,
                application_id=app.id,
                candidate_id=app.candidate_id,
                job_id=app.job_id,
            )
            if new_stage == "Rejected":
                result = _remove_rejected_application_data(db, app)
                db.commit()
                return result
        app.status = new_stage

    if "pipeline_order" in updates and updates["pipeline_order"] is not None:
        app.pipeline_order = updates["pipeline_order"]
    if "source" in updates:
        app.source = updates["source"].strip() if updates["source"] else None
    if "notes" in updates:
        app.notes = updates["notes"].strip() if updates["notes"] else None

    db.add(app)
    db.commit()
    db.refresh(app)
    return _application_to_table_row(app)


@router.delete("/applications/{app_id}", status_code=204)
def delete_application(app_id: str, db: Session = Depends(get_db)) -> None:
    app = db.get(Application, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    db.query(ActivityLog).filter(ActivityLog.application_id == app.id).delete(synchronize_session=False)
    db.delete(app)
    db.commit()
    return None


@router.patch("/candidates/{candidate_id}/compensation")
def update_candidate_compensation(
    candidate_id: str,
    payload: CandidateCompensationUpdate,
    db: Session = Depends(get_db),
) -> Any:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.current_package = payload.current_package.strip() if payload.current_package else None
    candidate.expected_package = payload.expected_package.strip() if payload.expected_package else None
    candidate.notice_period = payload.notice_period.strip() if payload.notice_period else None
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    return {
        "id": candidate.id,
        "current_package": candidate.current_package,
        "expected_package": candidate.expected_package,
        "notice_period": candidate.notice_period,
    }


@router.get("/pipeline/{job_id}", response_model=KanbanBoardOut)
def get_pipeline_board(job_id: str, db: Session = Depends(get_db)) -> Any:
    """Return all applications for a job grouped into Kanban columns."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applications = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.pipeline_order)
        .all()
    )

    columns: Dict[str, List[ApplicationKanbanOut]] = {stage: [] for stage in PIPELINE_STAGES}
    for app in applications:
        stage = app.status if app.status in VALID_STAGES else "Applied"
        columns[stage].append(_app_to_kanban_out(app))

    return KanbanBoardOut(job_id=job_id, job_title=job.title, columns=columns)


# ── Stage move ────────────────────────────────────────────────────────────────

@router.patch("/applications/{app_id}/stage")
def move_application_stage(
    app_id: str,
    payload: ApplicationStageUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Move a Kanban card to a new stage and record an activity log entry."""
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Guard against missing relationships (e.g., partially deleted candidate/job)
    if not app.candidate:
        raise HTTPException(status_code=422, detail="Application has no associated candidate")
    if not app.job:
        raise HTTPException(status_code=422, detail="Application has no associated job")

    old_stage = app.status
    new_stage = payload.stage

    if new_stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {new_stage}")

    try:
        _log_activity(
            db,
            action="stage_change",
            details=f"Moved from {old_stage} to {new_stage}",
            user_id=current_user.id,
            application_id=app_id,
            candidate_id=app.candidate_id,
            job_id=app.job_id,
        )

        app.status = new_stage
        if payload.pipeline_order is not None:
            app.pipeline_order = payload.pipeline_order

        if old_stage != new_stage and app.candidate.user_id:
            db.add(
                Notification(
                    id=str(uuid.uuid4()),
                    user_id=app.candidate.user_id,
                    title="Application status updated",
                    message=f"Your application for {app.job.title} moved to {new_stage}.",
                    link=f"/dashboard/pipeline?job={app.job_id}&app={app.id}",
                    level="info",
                )
            )

        db.commit()
        db.refresh(app)

        candidate_email = _candidate_display_email(app.candidate)
        if candidate_email:
            background_tasks.add_task(
                EmailService.send_stage_change_email,
                candidate_email=candidate_email,
                candidate_name=_candidate_display_name(app.candidate) or "Candidate",
                job_title=app.job.title,
                new_stage=new_stage,
            )

        return _app_to_kanban_out(app)

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logging.getLogger(__name__).error(
            "move_application_stage failed for app_id=%s new_stage=%s: %s",
            app_id, new_stage, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to update stage: {exc}") from exc


# ── Activity timeline ─────────────────────────────────────────────────────────

@router.get("/applications/{app_id}/activity", response_model=List[ActivityOut])
def get_activity(app_id: str, db: Session = Depends(get_db)) -> Any:
    """Return the full activity timeline for an application."""
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.application_id == app_id)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )

    result = []
    for log in logs:
        author_name = log.user.full_name if log.user else "System"
        result.append(
            ActivityOut(
                id=log.id,
                action=log.action,
                details=log.details,
                author_name=author_name,
                created_at=log.created_at,
            )
        )
    return result


# ── Comments ──────────────────────────────────────────────────────────────────

@router.post("/applications/{app_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    app_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Add a comment to an application and fire notifications for @mentions."""
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    comment = Comment(
        id=str(uuid.uuid4()),
        application_id=app_id,
        author_id=current_user.id,
        body=payload.body,
        mentions=json.dumps(payload.mentions),
    )
    db.add(comment)

    # Log activity
    _log_activity(
        db,
        action="comment",
        details=f"{current_user.full_name} commented",
        user_id=current_user.id,
        application_id=app_id,
        candidate_id=app.candidate_id,
        job_id=app.job_id,
    )

    # Fire in-app notifications for each mentioned user
    for mentioned_user_id in payload.mentions:
        mentioned_user = db.get(User, mentioned_user_id)
        if mentioned_user:
            notif = Notification(
                id=str(uuid.uuid4()),
                user_id=mentioned_user_id,
                title="You were mentioned in a comment",
                message=(
                    f"{current_user.full_name} mentioned you on "
                    f"{_candidate_display_name(app.candidate) or 'this candidate'}'s application."
                ),
                link=f"/dashboard/pipeline?app={app_id}",
                level="info",
            )
            db.add(notif)

    db.commit()
    db.refresh(comment)

    return _comment_to_out(comment)


@router.get("/applications/{app_id}/comments", response_model=List[CommentOut])
def get_comments(app_id: str, db: Session = Depends(get_db)) -> Any:
    """Return all comments for an application, oldest first."""
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    comments = (
        db.query(Comment)
        .filter(Comment.application_id == app_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return [_comment_to_out(comment) for comment in comments]


@router.patch("/applications/{app_id}/comments/{comment_id}", response_model=CommentOut)
def update_comment(
    app_id: str,
    comment_id: str,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    comment = db.get(Comment, comment_id)
    if comment is None or comment.application_id != app_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role not in {"Admin", "Recruiter"}:
        raise HTTPException(status_code=403, detail="You cannot edit this comment")

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment body is required")
    comment.body = body
    comment.mentions = json.dumps(payload.mentions)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_to_out(comment)


@router.delete("/applications/{app_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    app_id: str,
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    comment = db.get(Comment, comment_id)
    if comment is None or comment.application_id != app_id:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role not in {"Admin", "Recruiter"}:
        raise HTTPException(status_code=403, detail="You cannot delete this comment")

    db.delete(comment)
    db.commit()
    return None


# ── User search (for @mention autocomplete) ───────────────────────────────────

@router.get("/pipeline/users/search")
def search_users(q: str = "", db: Session = Depends(get_db)) -> Any:
    """Return a short list of users matching the query for @mention autocomplete."""
    users = (
        db.query(User)
        .filter(User.full_name.ilike(f"%{q}%"))
        .limit(10)
        .all()
    )
    return [{"id": u.id, "full_name": u.full_name, "email": u.email} for u in users]


@router.get("/notifications", response_model=List[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Return recent in-app notifications for the current user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)) -> Any:
    """Return live dashboard metrics from stored application data."""
    stage_counts = {stage: 0 for stage in PIPELINE_STAGES}
    for status, count in db.query(Application.status, func.count(Application.id)).group_by(Application.status).all():
        stage_counts[status if status in stage_counts else "Applied"] = count

    recent_applications = (
        db.query(Application)
        .order_by(Application.applied_at.desc())
        .limit(5)
        .all()
    )
    recent_candidates = [
        {
            "title": _candidate_display_name(app.candidate) or (app.resume.title if app.resume else "Name not detected"),
            "subtitle": app.candidate.headline or _candidate_display_email(app.candidate) or "Email not detected",
            "badge": app.status,
            "meta": f"{app.match_score:.0f}% match" if app.match_score is not None else "Not scored",
        }
        for app in recent_applications
    ]

    recent_jobs = [
        {
            "title": job.title,
            "subtitle": _format_locations(job.locations, job.remote_type),
            "badge": job.status or "draft",
            "meta": f"{len(job.applications)} application{'s' if len(job.applications) != 1 else ''}",
        }
        for job in db.query(Job).order_by(Job.title.asc()).limit(5).all()
    ]

    # Recent activities
    recent_activities = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(10)
        .all()
    )

    total_applications = db.query(Application).count()
    return {
        "stats": {
            "candidates": db.query(Candidate).count(),
            "open_jobs": db.query(Job).filter(Job.status != "closed").count(),
            "active_jobs": db.query(Job).filter(Job.status == "published").count(),
            "total_candidates": db.query(Candidate).count(),
            "shortlisted_candidates": stage_counts.get("Shortlisted", 0),
            "rejected_candidates": stage_counts.get("Rejected", 0),
            "hired_candidates": stage_counts.get("Hired", 0),
            "interviews_scheduled": db.query(Interview).count(),
            "applications": total_applications,
            "interviews": db.query(Interview).count(),
            "shortlisted": stage_counts.get("Shortlisted", 0),
        },
        "pipeline": [
            {
                "stage": stage,
                "count": count,
                "progress": round((count / total_applications) * 100) if total_applications else 0,
            }
            for stage, count in stage_counts.items()
            if count > 0
        ],
        "recent_candidates": recent_candidates,
        "recent_jobs": recent_jobs,
        "recent_activities": [
            {
                "id": act.id,
                "action": act.action,
                "details": act.details,
                "author_name": act.user.full_name if act.user else "System",
                "created_at": act.created_at,
            }
            for act in recent_activities
        ],
        "charts": {
            "hiring_funnel": [
                {"stage": stage, "count": stage_counts[stage]}
                for stage in PIPELINE_STAGES
                if stage_counts[stage] > 0
            ],
            "pipeline_distribution": [
                {"stage": stage, "count": count}
                for stage, count in stage_counts.items()
                if count > 0
            ],
        }
    }


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Mark one current-user notification as read."""
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.delete("/notifications/{notification_id}", status_code=204)
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notification)
    db.commit()
    return None


def _interview_to_out(interview: Interview) -> InterviewOut:
    interviewer_name = None
    if interview.interviewer_user:
        interviewer_name = interview.interviewer_user.full_name
    created_by_name = None
    if interview.created_by:
        created_by_name = interview.created_by.full_name
    candidate_name = interview.candidate.full_name if interview.candidate else None
    job_title = interview.job.title if interview.job else None
    return InterviewOut(
        id=interview.id,
        application_id=interview.application_id,
        candidate_id=interview.candidate_id,
        candidate_name=candidate_name,
        job_id=interview.job_id,
        job_title=job_title,
        interview_type=interview.interview_type,
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        duration_minutes_str=interview.duration_minutes_str,
        time_zone=interview.time_zone,
        meeting_link=interview.meeting_link,
        office_location=interview.office_location,
        location=interview.location,
        mode=interview.mode,
        interviewer=interview.interviewer,
        interviewer_user_id=interview.interviewer_user_id,
        interviewer_name=interviewer_name,
        created_by_id=interview.created_by_id,
        created_by_name=created_by_name,
        status=interview.status,
        rescheduled_from_id=interview.rescheduled_from_id,
        notes=interview.notes,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
    )


@router.get("/interviews", response_model=List[InterviewOut])
def list_interviews(
    job_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    query = db.query(Interview)
    if job_id:
        query = query.filter(Interview.job_id == job_id)
    if candidate_id:
        query = query.filter(Interview.candidate_id == candidate_id)
    if status:
        query = query.filter(Interview.status == status)
    interviews = query.order_by(Interview.scheduled_at.desc()).all()
    return [_interview_to_out(interview) for interview in interviews]


@router.get("/interviews/{interview_id}", response_model=InterviewOut)
def get_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return _interview_to_out(interview)


@router.post("/interviews", response_model=InterviewOut, status_code=201)
def create_interview(
    payload: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    # Verify candidate and job exist
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if payload.application_id:
        application = db.get(Application, payload.application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

    interview = Interview(
        id=str(uuid.uuid4()),
        application_id=payload.application_id,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        interview_type=payload.interview_type,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        duration_minutes_str=payload.duration_minutes_str,
        time_zone=payload.time_zone,
        meeting_link=payload.meeting_link,
        office_location=payload.office_location,
        location=payload.location,
        mode=payload.mode,
        interviewer=payload.interviewer,
        interviewer_user_id=payload.interviewer_user_id,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _interview_to_out(interview)


@router.put("/interviews/{interview_id}", response_model=InterviewOut)
def update_interview(
    interview_id: str,
    payload: InterviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(interview, field, value)
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _interview_to_out(interview)


@router.post("/interviews/{interview_id}/reschedule", response_model=InterviewOut, status_code=201)
def reschedule_interview(
    interview_id: str,
    payload: InterviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    original_interview = db.get(Interview, interview_id)
    if not original_interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    # Mark original as rescheduled
    original_interview.status = "Rescheduled"
    db.add(original_interview)

    # Create new interview
    new_interview = Interview(
        id=str(uuid.uuid4()),
        application_id=original_interview.application_id,
        candidate_id=original_interview.candidate_id,
        job_id=original_interview.job_id,
        interview_type=payload.interview_type or original_interview.interview_type,
        scheduled_at=payload.scheduled_at or original_interview.scheduled_at,
        duration_minutes=payload.duration_minutes or original_interview.duration_minutes,
        duration_minutes_str=payload.duration_minutes_str or original_interview.duration_minutes_str,
        time_zone=payload.time_zone or original_interview.time_zone,
        meeting_link=payload.meeting_link or original_interview.meeting_link,
        office_location=payload.office_location or original_interview.office_location,
        location=payload.location or original_interview.location,
        mode=payload.mode or original_interview.mode,
        interviewer=payload.interviewer or original_interview.interviewer,
        interviewer_user_id=payload.interviewer_user_id or original_interview.interviewer_user_id,
        notes=payload.notes or original_interview.notes,
        created_by_id=current_user.id,
        rescheduled_from_id=interview_id,
    )
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    return _interview_to_out(new_interview)


@router.post("/interviews/{interview_id}/cancel", response_model=InterviewOut)
def cancel_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    interview.status = "Cancelled"
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _interview_to_out(interview)


@router.delete("/interviews/{interview_id}", status_code=204, response_class=Response, response_model=None)
def delete_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    db.delete(interview)
    db.commit()
    return Response(status_code=204)
