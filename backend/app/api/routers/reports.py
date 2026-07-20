from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.ats import Job, Resume
from app.services.ats.masked_resume import MaskedResumeError, build_masked_resume_pdf, build_masked_resumes_zip, masked_resume_filename
from app.services.ats.screening_report import build_ats_report_xlsx, build_ats_screening_report, build_resume_data_xlsx

router = APIRouter()


def _get_report(job_id: str, db: Session) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    resumes = (
        db.query(Resume)
        .filter(Resume.current_version_id.isnot(None))
        .order_by(Resume.created_at.desc())
        .all()
    )
    return build_ats_screening_report(job, resumes)


@router.get("/reports/ats-screening/{job_id}")
def get_ats_screening_report(job_id: str, db: Session = Depends(get_db)) -> dict:
    return _get_report(job_id, db)


@router.get("/reports/ats-screening/{job_id}/excel")
def download_ats_screening_report(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    report = _get_report(job_id, db)
    content = build_ats_report_xlsx(report)
    safe_title = "".join(ch if ch.isalnum() else "_" for ch in report["job"].get("title", "ats_report")).strip("_")
    file_name = f"ats_screening_{safe_title or job_id}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/reports/resume-data/excel")
def download_resume_data_report(job_id: str | None = None, db: Session = Depends(get_db)) -> StreamingResponse:
    job = None
    if job_id:
        job = db.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

    resumes = (
        db.query(Resume)
        .filter(Resume.current_version_id.isnot(None))
        .order_by(Resume.created_at.desc())
        .all()
    )
    content = build_resume_data_xlsx(resumes, job)
    safe_title = "".join(ch if ch.isalnum() else "_" for ch in (getattr(job, "title", "") or "resume_data")).strip("_")
    file_name = f"resume_data_with_ats_{safe_title or 'report'}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/reports/masked-resumes/{resume_id}/pdf")
def download_masked_resume_pdf(resume_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    try:
        content = build_masked_resume_pdf(resume)
        file_name = masked_resume_filename(resume)
    except MaskedResumeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/reports/masked-resumes/zip")
def download_masked_resumes_zip(db: Session = Depends(get_db)) -> StreamingResponse:
    resumes = (
        db.query(Resume)
        .filter(Resume.current_version_id.isnot(None))
        .order_by(Resume.created_at.desc())
        .all()
    )
    if not resumes:
        raise HTTPException(status_code=404, detail="No parsed resumes found")

    content = build_masked_resumes_zip(resumes)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="masked_resumes.zip"'},
    )
