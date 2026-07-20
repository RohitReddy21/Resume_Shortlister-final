import os

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.paths import get_resume_dir
from app.models.ats import Resume
from app.services.anonymizer_tasks import anonymize_resume_task
from app.schemas.anonymize import MaskedMetadata, MaskPolicy, TaskResponse
from pydantic import ValidationError
import json

router = APIRouter()


@router.post("/resumes/{resume_id}/mask", response_model=TaskResponse, status_code=202)
async def mask_resume(resume_id: str, mask_policy: MaskPolicy, db: Session = Depends(get_db)) -> TaskResponse:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="resume not found")
    try:
        # ensure policy validation (root_validator may raise)
        mask_policy = MaskPolicy(**mask_policy.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    task = anonymize_resume_task.delay(resume_id, mask_policy.model_dump())
    return TaskResponse(task_id=task.id, status="enqueued")


@router.get("/resumes/masked/{resume_id}", response_model=MaskedMetadata)
async def get_masked(resume_id: str, db: Session = Depends(get_db)):
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="resume not found")

    # prefer DB-stored masked metadata on the current version
    version = None
    try:
        version = resume.current_version
    except Exception:
        version = None

    if version and (version.masked_candidate_id or version.masked_pdf or version.masked_docx):
        mask_policy = None
        try:
            if version.mask_policy:
                mask_policy = json.loads(version.mask_policy)
        except Exception:
            mask_policy = None

        return MaskedMetadata(
            masked_candidate_id=version.masked_candidate_id,
            masked_pdf=version.masked_pdf,
            masked_docx=version.masked_docx,
            mask_policy=mask_policy,
            masked_at=version.masked_at,
        )

    # fallback: find masked files on disk
    resumes_dir = get_resume_dir()
    if os.path.isdir(resumes_dir):
        for fn in os.listdir(resumes_dir):
            if fn.startswith(resume_id):
                base = os.path.join(resumes_dir, fn)
                return MaskedMetadata(
                    masked_candidate_id=None,
                    masked_pdf=base + ".masked.pdf" if os.path.exists(base + ".masked.pdf") else None,
                    masked_docx=base + ".masked.docx" if os.path.exists(base + ".masked.docx") else None,
                    mask_policy=None,
                    masked_at=None,
                )

    raise HTTPException(status_code=404, detail="masked files not found")
