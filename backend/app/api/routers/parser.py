import os
import uuid
import json
from typing import Dict, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.paths import get_resume_dir
from app.models.ats import Application, Candidate, Resume, ResumeVersion
from app.services.parser.structured import build_structured_resume
from app.services.parser.tasks import _sync_candidate_profile_from_structured, parse_resume_task
from celery_app import celery

settings = get_settings()
router = APIRouter()

RESUME_DIR = get_resume_dir()

MAX_BYTES = 20 * 1024 * 1024  # 20 MB


class ResumeUpdatePayload(BaseModel):
    title: str | None = None
    source: str | None = None


class StructuredExperiencePayload(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    location: str = ""
    description: str = ""


class StructuredEducationPayload(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    graduation_date: str = ""
    gpa: str = ""


class StructuredResumePayload(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[StructuredExperiencePayload] = Field(default_factory=list)
    education: List[StructuredEducationPayload] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


def _use_celery_queue() -> bool:
    return os.getenv("RESUME_PARSER_USE_CELERY", "").lower() in {"1", "true", "yes"}


def _save_upload_stream(upload: UploadFile, dest_path: str) -> int:
    """Save UploadFile to disk and return total bytes written."""
    total = 0
    with open(dest_path, "wb") as out:
        while True:
            chunk = upload.file.read(8192)
            if not chunk:
                break
            out.write(chunk)
            total += len(chunk)
    return total


def _ensure_candidate(db: Session, candidate_id: str | None, upload_uid: str) -> Candidate:
    if candidate_id:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return candidate

    candidate = Candidate(
        id=str(uuid.uuid4()),
        first_name="Unknown",
        last_name="Candidate",
        email=f"unknown+{upload_uid}@resumeparser.ai",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def _is_internal_candidate_placeholder(candidate: Candidate) -> bool:
    return (
        candidate.first_name == "Unknown"
        and candidate.last_name == "Candidate"
        and candidate.email.startswith("unknown+")
        and candidate.email.endswith("@resumeparser.ai")
    )


def _candidate_display_name(candidate: Candidate | None) -> str | None:
    if candidate is None or _is_internal_candidate_placeholder(candidate):
        return None
    return f"{candidate.first_name} {candidate.last_name}".strip() or None


def _candidate_display_email(candidate: Candidate | None) -> str | None:
    if candidate is None or (
        candidate.email.startswith("unknown+") and candidate.email.endswith("@resumeparser.ai")
    ):
        return None
    return candidate.email


def _find_saved_resume_path(resume: Resume) -> str | None:
    prefix = f"{resume.id}_"
    for file_name in os.listdir(RESUME_DIR):
        if file_name.startswith(prefix):
            return os.path.join(RESUME_DIR, file_name)
    return None


def _load_current_parsed_resume(resume: Resume) -> dict:
    current_version = resume.current_version
    if current_version is None or not current_version.parsed_json:
        raise HTTPException(status_code=400, detail="Parsed resume data is unavailable")

    try:
        return json.loads(current_version.parsed_json)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not deserialize parsed resume JSON") from exc


def _parse_inline(resume: Resume, candidate: Candidate, dest_path: str, file_name: str, queue_error: Exception | None = None) -> Dict:
    try:
        result = parse_resume_task.run(resume.id, candidate.id, dest_path)
        warning = "Resume was parsed inline."
        if queue_error is not None:
            warning = "Celery broker was unavailable, so the resume was parsed inline."

        return {
            "upload_id": resume.id,
            "resume_id": resume.id,
            "task_id": None,
            "file_name": file_name,
            "saved_path": dest_path,
            "status": "completed",
            "parse_mode": "inline",
            "result": result,
            "warning": warning,
        }
    except Exception as parse_exc:
        warning = "Resume was uploaded, but inline parsing failed."
        if queue_error is not None:
            warning = f"Resume was uploaded, but parsing could not start: {queue_error}"

        return {
            "upload_id": resume.id,
            "resume_id": resume.id,
            "task_id": None,
            "file_name": file_name,
            "saved_path": dest_path,
            "status": "uploaded",
            "parse_mode": "not_parsed",
            "warning": warning,
            "error": str(parse_exc),
        }


@router.post("/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    candidate_id: str | None = Form(None),
    db: Session = Depends(get_db),
) -> Dict:
    """Accept a resume file, save it, create a resume record, and enqueue parsing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    upload_uid = str(uuid.uuid4())
    safe_name = f"{upload_uid}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(RESUME_DIR, safe_name)

    try:
        bytes_written = _save_upload_stream(file, dest_path)
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    if bytes_written > MAX_BYTES:
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    candidate = _ensure_candidate(db, candidate_id, upload_uid)
    resume = Resume(
        id=upload_uid,
        candidate_id=candidate.id,
        title=file.filename,
        source="upload",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    if not _use_celery_queue():
        return _parse_inline(resume, candidate, dest_path, file.filename)

    try:
        task_result = parse_resume_task.delay(resume.id, candidate.id, dest_path)
        return {
            "upload_id": resume.id,
            "resume_id": resume.id,
            "task_id": task_result.id,
            "file_name": file.filename,
            "saved_path": dest_path,
            "status": "processing",
            "parse_mode": "celery",
        }
    except Exception as queue_exc:
        return _parse_inline(resume, candidate, dest_path, file.filename, queue_exc)


@router.post("/resumes/{resume_id}/parse")
async def parse_existing_resume(resume_id: str, force: bool = False, db: Session = Depends(get_db)) -> Dict:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    candidate = resume.candidate
    if candidate is None:
        raise HTTPException(status_code=400, detail="Resume has no candidate record")

    if resume.current_version_id and not force:
        return {
            "upload_id": resume.id,
            "resume_id": resume.id,
            "task_id": None,
            "file_name": resume.title,
            "saved_path": _find_saved_resume_path(resume) or "",
            "status": "completed",
            "parse_mode": "existing",
            "result": {
                "resume_id": resume.id,
                "version_id": resume.current_version_id,
                "status": "completed",
            },
            "warning": "Resume was already parsed.",
        }

    saved_path = _find_saved_resume_path(resume)
    if saved_path is None:
        raise HTTPException(status_code=404, detail="Uploaded resume file was not found")

    response = _parse_inline(resume, candidate, saved_path, resume.title)
    if response.get("parse_mode") == "not_parsed":
        raise HTTPException(status_code=400, detail=response.get("error") or "Resume could not be parsed")
    return response


@router.patch("/resumes/{resume_id}")
async def update_resume(resume_id: str, payload: ResumeUpdatePayload, db: Session = Depends(get_db)) -> Dict:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is not None:
        title = updates["title"].strip()
        if not title:
            raise HTTPException(status_code=400, detail="Resume title is required")
        resume.title = title[:255]
    if "source" in updates:
        resume.source = updates["source"].strip()[:100] if updates["source"] else None

    db.add(resume)
    db.commit()
    db.refresh(resume)
    return {
        "id": resume.id,
        "resume_id": resume.id,
        "candidate_id": resume.candidate_id,
        "title": resume.title,
        "source": resume.source,
        "current_version_id": resume.current_version_id,
        "status": "parsed" if resume.current_version_id else "processing",
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
    }


@router.patch("/resumes/{resume_id}/structured")
async def update_structured_resume(
    resume_id: str,
    payload: StructuredResumePayload,
    db: Session = Depends(get_db),
) -> Dict:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.current_version is None:
        raise HTTPException(status_code=400, detail="Resume has not been parsed yet")
    if resume.candidate is None:
        raise HTTPException(status_code=400, detail="Resume has no candidate record")

    structured = payload.model_dump()
    email = structured.get("email", "").strip()
    if email:
        existing = (
            db.query(Candidate)
            .filter(Candidate.email == email, Candidate.id != resume.candidate_id)
            .first()
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="Another candidate already uses this email")

    parsed = _load_current_parsed_resume(resume)
    parsed["structured"] = structured
    resume.current_version.parsed_json = json.dumps(parsed, ensure_ascii=False)
    db.add(resume.current_version)
    _sync_candidate_profile_from_structured(
        db,
        resume.candidate,
        structured,
        replace_related=True,
        force_identity=True,
    )
    db.commit()
    db.refresh(resume)
    return {
        "resume_id": resume.id,
        "candidate_id": resume.candidate_id,
        "resume_title": resume.title,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
        "structured": build_structured_resume(parsed),
    }


@router.delete("/resumes/{resume_id}", status_code=204)
async def delete_resume(resume_id: str, db: Session = Depends(get_db)) -> None:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    saved_path = _find_saved_resume_path(resume)
    db.query(Application).filter(Application.resume_id == resume.id).update({"resume_id": None}, synchronize_session=False)
    resume.current_version_id = None
    db.add(resume)
    db.flush()
    db.query(ResumeVersion).filter(ResumeVersion.resume_id == resume.id).delete(synchronize_session=False)
    db.delete(resume)
    db.commit()

    if saved_path:
        resume_root = os.path.abspath(RESUME_DIR)
        candidate_path = os.path.abspath(saved_path)
        if candidate_path.startswith(resume_root) and os.path.exists(candidate_path):
            os.remove(candidate_path)
    return None


@router.get("/resumes")
async def list_resumes(db: Session = Depends(get_db)) -> List[Dict]:
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).limit(100).all()
    items = []
    for resume in resumes:
        candidate = resume.candidate

        items.append(
            {
                "id": resume.id,
                "resume_id": resume.id,
                "candidate_id": resume.candidate_id,
                "candidate_name": _candidate_display_name(candidate),
                "candidate_email": _candidate_display_email(candidate),
                "title": resume.title,
                "source": resume.source,
                "current_version_id": resume.current_version_id,
                "status": "parsed" if resume.current_version_id else "processing",
                "created_at": resume.created_at.isoformat() if resume.created_at else None,
            }
        )
    return items


@router.get("/resumes/structured")
async def list_structured_resumes(db: Session = Depends(get_db)) -> List[Dict]:
    resumes = (
        db.query(Resume)
        .filter(Resume.current_version_id.isnot(None))
        .order_by(Resume.created_at.desc())
        .limit(200)
        .all()
    )
    items = []
    for resume in resumes:
        parsed = _load_current_parsed_resume(resume)
        items.append(
            {
                "resume_id": resume.id,
                "candidate_id": resume.candidate_id,
                "resume_title": resume.title,
                "created_at": resume.created_at.isoformat() if resume.created_at else None,
                "structured": build_structured_resume(parsed),
            }
        )
    return items


@router.get("/resumes/status/{task_id}")
async def get_parse_status(task_id: str) -> Dict:
    result = AsyncResult(task_id, app=celery)
    response = {"task_id": task_id, "status": result.status}
    if result.successful():
        response["result"] = result.result
    elif result.failed():
        response["error"] = str(result.result)
    return response


@router.get("/resumes/parsed/{upload_id}")
async def get_parsed(upload_id: str, db: Session = Depends(get_db)):
    resume = db.get(Resume, upload_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="upload_id not found")

    if resume.current_version_id is None:
        return {"status": "processing"}

    current_version = resume.current_version
    if current_version is None:
        return {"status": "processing"}

    try:
        return json.loads(current_version.parsed_json or "{}")
    except Exception:
        raise HTTPException(status_code=500, detail="Could not deserialize parsed resume JSON")


@router.get("/resumes/{resume_id}/structured")
async def get_structured_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return build_structured_resume(_load_current_parsed_resume(resume))
