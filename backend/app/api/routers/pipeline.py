import json
import os
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
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
    db.query(Comment).filter(Comment.application_id.in_(application_ids)).delete(synchronize_session=False)
    db.query(Interview).filter(Interview.application_id.in_(application_ids)).delete(synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.application_id.in_(application_ids)).delete(synchronize_session=False)
    db.query(Application).filter(Application.id.in_(application_ids)).delete(synchronize_session=False)


def _delete_candidate_profile_rows(db: Session, candidate_id: str) -> None:
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
        "headline": candidate.headline,
        "current_package": candidate.current_package,
        "expected_package": candidate.expected_package,
        "notice_period": candidate.notice_period,
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
        headline=payload.headline.strip() if payload.headline else None,
        current_package=payload.current_package.strip() if payload.current_package else None,
        expected_package=payload.expected_package.strip() if payload.expected_package else None,
        notice_period=payload.notice_period.strip() if payload.notice_period else None,
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

    old_stage = app.status
    new_stage = payload.stage

    if new_stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {new_stage}")

    _log_activity(
        db,
        action="stage_change",
        details=f"Moved from {old_stage} to {new_stage}",
        user_id=current_user.id,
        application_id=app_id,
        candidate_id=app.candidate_id,
        job_id=app.job_id,
    )

    if new_stage == "Rejected":
        result = _remove_rejected_application_data(db, app)
        db.commit()
        return result

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

    total_applications = db.query(Application).count()
    return {
        "stats": {
            "candidates": db.query(Candidate).count(),
            "open_jobs": db.query(Job).filter(Job.status != "closed").count(),
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
