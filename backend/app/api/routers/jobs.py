import json
import uuid
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.ats.job import Job
from app.models.ats.department import Department
from app.models.ats.hiring_manager import HiringManager
from app.schemas.jobs import JobCreate, JobOut, JobUpdate

router = APIRouter()


@router.post("/jobs", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobOut:
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        title=payload.title,
        description=payload.description,
        department_id=payload.department_id,
        hiring_manager_id=payload.hiring_manager_id,
        skills=json.dumps(payload.skills or []),
        locations=json.dumps(payload.locations or []),
        remote_type=payload.remote_type,
        status=payload.status or "draft",
        min_salary=payload.min_salary,
        max_salary=payload.max_salary,
        currency=payload.currency,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobOut.model_validate(job)


@router.put("/jobs/{job_id}", response_model=JobOut)
def update_job(job_id: str, payload: JobUpdate, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        if k in ("skills", "locations") and v is not None:
            setattr(job, k, json.dumps(v))
        else:
            setattr(job, k, v)

    db.add(job)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> None:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    db.delete(job)
    db.commit()
    return None


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(status: str | None = Query(None), db: Session = Depends(get_db)) -> Any:
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    items = q.all()
    results = []
    for it in items:
        results.append(JobOut.model_validate(it))
    return results
