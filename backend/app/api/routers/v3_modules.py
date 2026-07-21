import os
import uuid
import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.ats import (
    Interview,
    Candidate,
    Job,
    InterviewFeedback,
    InterviewPanelMember,
    Offer,
    OfferDocument,
    JoiningRecord,
    CandidateCommunication,
    EmailTemplate,
    CandidateDocumentVault,
    CandidateChecklistItem,
    RecruiterTask,
    SystemReminder,
    AuditLog,
)

router = APIRouter(tags=["v3-modules"])


# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    technical_skills: Optional[int] = 3
    communication: Optional[int] = 3
    problem_solving: Optional[int] = 3
    teamwork: Optional[int] = 3
    leadership: Optional[int] = 3
    domain_knowledge: Optional[int] = 3
    coding_skills: Optional[int] = 3
    overall_rating: Optional[float] = 3.0
    recommendation: str = "Hold" # Strong Hire, Hire, Hold, Reject
    remarks: Optional[str] = None

class FeedbackOut(BaseModel):
    id: str
    interview_id: str
    interviewer_id: str
    interviewer_name: Optional[str] = None
    technical_skills: Optional[int] = None
    communication: Optional[int] = None
    problem_solving: Optional[int] = None
    teamwork: Optional[int] = None
    leadership: Optional[int] = None
    domain_knowledge: Optional[int] = None
    coding_skills: Optional[int] = None
    overall_rating: Optional[float] = None
    recommendation: str
    remarks: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PanelMemberCreate(BaseModel):
    user_id: str
    role_name: Optional[str] = "Technical Interviewer" # HR, Technical Interviewer, Hiring Manager
    panel_notes: Optional[str] = None

class PanelMemberOut(BaseModel):
    id: str
    interview_id: str
    user_id: str
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    panel_notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OfferCreate(BaseModel):
    candidate_id: str
    job_id: str
    salary_offered: float
    bonus: Optional[float] = 0.0
    joining_bonus: Optional[float] = 0.0
    joining_date: Optional[datetime] = None
    offer_expiry: Optional[datetime] = None
    notes: Optional[str] = None

class OfferUpdate(BaseModel):
    salary_offered: Optional[float] = None
    bonus: Optional[float] = None
    joining_bonus: Optional[float] = None
    joining_date: Optional[datetime] = None
    offer_expiry: Optional[datetime] = None
    offer_status: Optional[str] = None # Draft, Sent, Accepted, Declined, Expired
    notes: Optional[str] = None

class OfferOut(BaseModel):
    id: str
    offer_number: str
    candidate_id: str
    candidate_name: Optional[str] = None
    job_id: str
    job_title: Optional[str] = None
    salary_offered: float
    bonus: Optional[float] = None
    joining_bonus: Optional[float] = None
    joining_date: Optional[datetime] = None
    offer_expiry: Optional[datetime] = None
    offer_status: str
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JoiningCreate(BaseModel):
    candidate_id: str
    offer_id: Optional[str] = None
    joining_date: datetime
    joining_status: Optional[str] = "Pending" # Pending, Joined, Delayed, Cancelled
    reporting_manager_id: Optional[str] = None
    office_location: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None

class JoiningUpdate(BaseModel):
    joining_date: Optional[datetime] = None
    joining_status: Optional[str] = None
    reporting_manager_id: Optional[str] = None
    office_location: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None

class JoiningOut(BaseModel):
    id: str
    candidate_id: str
    candidate_name: Optional[str] = None
    offer_id: Optional[str] = None
    joining_date: datetime
    joining_status: str
    reporting_manager_id: Optional[str] = None
    reporting_manager_name: Optional[str] = None
    office_location: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CommunicationCreate(BaseModel):
    communication_type: str # Email, Phone Call, SMS, WhatsApp Note, Meeting Note
    summary: str

class CommunicationOut(BaseModel):
    id: str
    candidate_id: str
    user_id: str
    user_name: Optional[str] = None
    communication_type: str
    summary: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EmailTemplateCreate(BaseModel):
    name: str
    template_type: str # Interview Invitation, Interview Reminder, Interview Reschedule, Offer Letter, Joining Reminder, Rejection, Follow-up
    subject_template: str
    body_template: str

class EmailTemplateOut(BaseModel):
    id: str
    name: str
    template_type: str
    subject_template: str
    body_template: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: Optional[str] = "Follow Up"
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[str] = None
    candidate_id: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None # Pending, Completed, Cancelled
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[str] = None

class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    task_type: str
    status: str
    due_date: Optional[datetime] = None
    assigned_to_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReminderCreate(BaseModel):
    title: str
    reminder_type: str # Interview Reminder, Offer Expiry Reminder, Joining Reminder, Document Reminder, Task Reminder
    remind_at: datetime

class ReminderOut(BaseModel):
    id: str
    title: str
    reminder_type: str
    remind_at: datetime
    status: str
    user_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _log_audit(db: Session, action: str, entity_type: str, entity_id: str, details: str, user_id: str):
    log = AuditLog(
        id=str(uuid.uuid4()),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        user_id=user_id,
    )
    db.add(log)


# ------------------------------------------------------------------------------
# MODULE 3 – Interview Feedback
# ------------------------------------------------------------------------------

@router.post("/interviews/{interview_id}/feedback", response_model=FeedbackOut, status_code=201)
def submit_interview_feedback(
    interview_id: str,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    fb = InterviewFeedback(
        id=str(uuid.uuid4()),
        interview_id=interview_id,
        interviewer_id=current_user.id,
        technical_skills=payload.technical_skills,
        communication=payload.communication,
        problem_solving=payload.problem_solving,
        teamwork=payload.teamwork,
        leadership=payload.leadership,
        domain_knowledge=payload.domain_knowledge,
        coding_skills=payload.coding_skills,
        overall_rating=payload.overall_rating,
        recommendation=payload.recommendation,
        remarks=payload.remarks,
    )
    db.add(fb)

    # Mark interview as completed
    interview.status = "Completed"
    db.add(interview)

    _log_audit(db, "submit_feedback", "InterviewFeedback", fb.id, f"Feedback submitted for interview {interview_id}", current_user.id)
    db.commit()
    db.refresh(fb)

    out = FeedbackOut.model_validate(fb)
    out.interviewer_name = current_user.full_name
    return out


@router.get("/interviews/{interview_id}/feedback", response_model=List[FeedbackOut])
def get_interview_feedbacks(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedbacks = db.query(InterviewFeedback).filter(InterviewFeedback.interview_id == interview_id).all()
    results = []
    for f in feedbacks:
        out = FeedbackOut.model_validate(f)
        out.interviewer_name = f.interviewer.full_name if f.interviewer else None
        results.append(out)
    return results


# ------------------------------------------------------------------------------
# MODULE 4 – Interview Panel
# ------------------------------------------------------------------------------

@router.post("/interviews/{interview_id}/panel", response_model=PanelMemberOut, status_code=201)
def add_panel_member(
    interview_id: str,
    payload: PanelMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    member = InterviewPanelMember(
        id=str(uuid.uuid4()),
        interview_id=interview_id,
        user_id=payload.user_id,
        role_name=payload.role_name,
        panel_notes=payload.panel_notes,
    )
    db.add(member)
    _log_audit(db, "add_panel_member", "InterviewPanelMember", member.id, f"Added user {payload.user_id} to interview {interview_id}", current_user.id)
    db.commit()
    db.refresh(member)

    out = PanelMemberOut.model_validate(member)
    out.user_name = member.user.full_name if member.user else None
    return out


@router.get("/interviews/{interview_id}/panel", response_model=List[PanelMemberOut])
def list_panel_members(
    interview_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    members = db.query(InterviewPanelMember).filter(InterviewPanelMember.interview_id == interview_id).all()
    results = []
    for m in members:
        out = PanelMemberOut.model_validate(m)
        out.user_name = m.user.full_name if m.user else None
        results.append(out)
    return results


# ------------------------------------------------------------------------------
# MODULE 5 – Offer Management
# ------------------------------------------------------------------------------

@router.post("/offers", response_model=OfferOut, status_code=201)
def create_offer(
    payload: OfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Offer).count() + 1
    now_str = datetime.now(timezone.utc).strftime("%Y%m")
    offer_number = f"OFF-{now_str}-{count:03d}"

    offer = Offer(
        id=str(uuid.uuid4()),
        offer_number=offer_number,
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        salary_offered=payload.salary_offered,
        bonus=payload.bonus,
        joining_bonus=payload.joining_bonus,
        joining_date=payload.joining_date,
        offer_expiry=payload.offer_expiry,
        notes=payload.notes,
        created_by_id=current_user.id,
    )
    db.add(offer)
    _log_audit(db, "create_offer", "Offer", offer.id, f"Created offer {offer_number} for candidate {payload.candidate_id}", current_user.id)
    db.commit()
    db.refresh(offer)

    out = OfferOut.model_validate(offer)
    out.candidate_name = offer.candidate.full_name if offer.candidate else None
    out.job_title = offer.job.title if offer.job else None
    return out


@router.get("/offers", response_model=List[OfferOut])
def list_offers(
    candidate_id: Optional[str] = None,
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Offer)
    if candidate_id:
        query = query.filter(Offer.candidate_id == candidate_id)
    if job_id:
        query = query.filter(Offer.job_id == job_id)
    if status:
        query = query.filter(Offer.offer_status == status)

    offers = query.order_by(Offer.created_at.desc()).all()
    results = []
    for o in offers:
        out = OfferOut.model_validate(o)
        out.candidate_name = o.candidate.full_name if o.candidate else None
        out.job_title = o.job.title if o.job else None
        results.append(out)
    return results


@router.put("/offers/{offer_id}", response_model=OfferOut)
def update_offer(
    offer_id: str,
    payload: OfferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(offer, k, v)

    _log_audit(db, "update_offer", "Offer", offer.id, f"Updated offer {offer.offer_number}", current_user.id)
    db.commit()
    db.refresh(offer)

    out = OfferOut.model_validate(offer)
    out.candidate_name = offer.candidate.full_name if offer.candidate else None
    out.job_title = offer.job.title if offer.job else None
    return out


# ------------------------------------------------------------------------------
# MODULE 7 – Joining Management
# ------------------------------------------------------------------------------

@router.post("/joining", response_model=JoiningOut, status_code=201)
def create_joining_record(
    payload: JoiningCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = JoiningRecord(
        id=str(uuid.uuid4()),
        candidate_id=payload.candidate_id,
        offer_id=payload.offer_id,
        joining_date=payload.joining_date,
        joining_status=payload.joining_status or "Pending",
        reporting_manager_id=payload.reporting_manager_id,
        office_location=payload.office_location,
        employee_id=payload.employee_id,
        department=payload.department,
        notes=payload.notes,
    )
    db.add(rec)
    _log_audit(db, "create_joining", "JoiningRecord", rec.id, f"Created joining record for candidate {payload.candidate_id}", current_user.id)
    db.commit()
    db.refresh(rec)

    out = JoiningOut.model_validate(rec)
    out.candidate_name = rec.candidate.full_name if rec.candidate else None
    out.reporting_manager_name = rec.reporting_manager.full_name if rec.reporting_manager else None
    return out


@router.get("/joining", response_model=List[JoiningOut])
def list_joining_records(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(JoiningRecord)
    if status:
        query = query.filter(JoiningRecord.joining_status == status)

    records = query.order_by(JoiningRecord.joining_date.desc()).all()
    results = []
    for r in records:
        out = JoiningOut.model_validate(r)
        out.candidate_name = r.candidate.full_name if r.candidate else None
        out.reporting_manager_name = r.reporting_manager.full_name if r.reporting_manager else None
        results.append(out)
    return results


@router.put("/joining/{joining_id}", response_model=JoiningOut)
def update_joining_record(
    joining_id: str,
    payload: JoiningUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = db.get(JoiningRecord, joining_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Joining record not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rec, k, v)

    _log_audit(db, "update_joining", "JoiningRecord", rec.id, f"Updated joining record status to {rec.joining_status}", current_user.id)
    db.commit()
    db.refresh(rec)

    out = JoiningOut.model_validate(rec)
    out.candidate_name = rec.candidate.full_name if rec.candidate else None
    out.reporting_manager_name = rec.reporting_manager.full_name if rec.reporting_manager else None
    return out


# ------------------------------------------------------------------------------
# MODULE 8 – Candidate Communication
# ------------------------------------------------------------------------------

@router.post("/candidates/{candidate_id}/communications", response_model=CommunicationOut, status_code=201)
def add_candidate_communication(
    candidate_id: str,
    payload: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    comm = CandidateCommunication(
        id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        user_id=current_user.id,
        communication_type=payload.communication_type,
        summary=payload.summary,
    )
    db.add(comm)
    db.commit()
    db.refresh(comm)

    out = CommunicationOut.model_validate(comm)
    out.user_name = current_user.full_name
    return out


@router.get("/candidates/{candidate_id}/communications", response_model=List[CommunicationOut])
def list_candidate_communications(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comms = db.query(CandidateCommunication).filter(CandidateCommunication.candidate_id == candidate_id).order_by(CandidateCommunication.created_at.desc()).all()
    results = []
    for c in comms:
        out = CommunicationOut.model_validate(c)
        out.user_name = c.user.full_name if c.user else None
        results.append(out)
    return results


# ------------------------------------------------------------------------------
# MODULE 9 – Email Templates
# ------------------------------------------------------------------------------

@router.post("/email-templates", response_model=EmailTemplateOut, status_code=201)
def create_email_template(
    payload: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = EmailTemplate(
        id=str(uuid.uuid4()),
        name=payload.name,
        template_type=payload.template_type,
        subject_template=payload.subject_template,
        body_template=payload.body_template,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.get("/email-templates", response_model=List[EmailTemplateOut])
def list_email_templates(
    template_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(EmailTemplate)
    if template_type:
        query = query.filter(EmailTemplate.template_type == template_type)
    return query.all()


@router.post("/email-templates/preview")
def preview_email_template(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    subject = payload.get("subject_template", "")
    body = payload.get("body_template", "")
    sample_vars = {
        "candidate_name": "John Doe",
        "job_title": "Senior Software Engineer",
        "interview_date": "2026-07-25 10:00 AM",
        "interviewer_name": "Jane Smith",
    }
    for k, v in sample_vars.items():
        subject = subject.replace(f"{{{{{k}}}}}", v)
        body = body.replace(f"{{{{{k}}}}}", v)

    return {"subject": subject, "body": body}


# ------------------------------------------------------------------------------
# MODULE 11 – Candidate Checklist
# ------------------------------------------------------------------------------

DEFAULT_CHECKLIST = [
    "Resume Uploaded",
    "Documents Verified",
    "Interview Completed",
    "Offer Sent",
    "Offer Accepted",
    "Background Verification",
    "Joining Confirmed",
    "HR Approval",
    "Manager Approval",
]

@router.get("/candidates/{candidate_id}/checklist")
def get_candidate_checklist(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.query(CandidateChecklistItem).filter(CandidateChecklistItem.candidate_id == candidate_id).all()
    if not items:
        # Populate default checklist
        for name in DEFAULT_CHECKLIST:
            it = CandidateChecklistItem(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                item_name=name,
                is_completed=False,
            )
            db.add(it)
        db.commit()
        items = db.query(CandidateChecklistItem).filter(CandidateChecklistItem.candidate_id == candidate_id).all()

    completed_count = sum(1 for item in items if item.is_completed)
    percentage = round((completed_count / len(items)) * 100) if items else 0

    return {
        "candidate_id": candidate_id,
        "completion_percentage": percentage,
        "items": [
            {
                "id": it.id,
                "item_name": it.item_name,
                "is_completed": it.is_completed,
                "completed_at": it.completed_at,
            }
            for it in items
        ],
    }


@router.put("/candidates/{candidate_id}/checklist/{item_id}")
def update_checklist_item(
    candidate_id: str,
    item_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.get(CandidateChecklistItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    item.is_completed = payload.get("is_completed", True)
    item.completed_at = datetime.now(timezone.utc) if item.is_completed else None
    item.verified_by_id = current_user.id
    db.commit()

    return {"id": item.id, "is_completed": item.is_completed}


# ------------------------------------------------------------------------------
# MODULE 12 – Recruiter Tasks
# ------------------------------------------------------------------------------

@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_recruiter_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = RecruiterTask(
        id=str(uuid.uuid4()),
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type or "Follow Up",
        due_date=payload.due_date,
        assigned_to_id=payload.assigned_to_id or current_user.id,
        candidate_id=payload.candidate_id,
    )
    db.add(task)
    _log_audit(db, "create_task", "RecruiterTask", task.id, f"Created task '{task.title}'", current_user.id)
    db.commit()
    db.refresh(task)

    out = TaskOut.model_validate(task)
    out.assigned_to_name = task.assigned_to.full_name if task.assigned_to else None
    out.candidate_name = task.candidate.full_name if task.candidate else None
    return out


@router.get("/tasks", response_model=List[TaskOut])
def list_recruiter_tasks(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(RecruiterTask)
    if status:
        query = query.filter(RecruiterTask.status == status)

    tasks = query.order_by(RecruiterTask.created_at.desc()).all()
    results = []
    for t in tasks:
        out = TaskOut.model_validate(t)
        out.assigned_to_name = t.assigned_to.full_name if t.assigned_to else None
        out.candidate_name = t.candidate.full_name if t.candidate else None
        results.append(out)
    return results


@router.put("/tasks/{task_id}", response_model=TaskOut)
def update_recruiter_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.get(RecruiterTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(task, k, v)

    db.commit()
    db.refresh(task)

    out = TaskOut.model_validate(task)
    out.assigned_to_name = task.assigned_to.full_name if task.assigned_to else None
    out.candidate_name = task.candidate.full_name if task.candidate else None
    return out


# ------------------------------------------------------------------------------
# MODULE 13 – Reminders
# ------------------------------------------------------------------------------

@router.post("/reminders", response_model=ReminderOut, status_code=201)
def create_reminder(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rem = SystemReminder(
        id=str(uuid.uuid4()),
        title=payload.title,
        reminder_type=payload.reminder_type,
        remind_at=payload.remind_at,
        user_id=current_user.id,
    )
    db.add(rem)
    db.commit()
    db.refresh(rem)
    return rem


@router.get("/reminders", response_model=List[ReminderOut])
def list_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(SystemReminder).filter(SystemReminder.user_id == current_user.id, SystemReminder.status != "Dismissed").all()


@router.post("/reminders/{reminder_id}/dismiss")
def dismiss_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rem = db.get(SystemReminder, reminder_id)
    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found")

    rem.status = "Dismissed"
    db.commit()
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# MODULE 14 – Dashboard Improvements V3 Summary
# ------------------------------------------------------------------------------

@router.get("/dashboard/v3-summary")
def get_v3_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    today_end = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)

    todays_interviews = db.query(Interview).filter(Interview.scheduled_at >= today_start, Interview.scheduled_at <= today_end).count()
    upcoming_interviews = db.query(Interview).filter(Interview.scheduled_at > today_end, Interview.status == "Scheduled").count()
    
    offers_sent = db.query(Offer).filter(Offer.offer_status == "Sent").count()
    offers_accepted = db.query(Offer).filter(Offer.offer_status == "Accepted").count()
    
    joining_this_week = db.query(JoiningRecord).filter(JoiningRecord.joining_status == "Pending").count()
    pending_tasks = db.query(RecruiterTask).filter(RecruiterTask.status == "Pending").count()
    pending_feedback = db.query(Interview).filter(Interview.status == "Completed").count() # completed interviews awaiting feedback

    return {
        "todays_interviews": todays_interviews,
        "upcoming_interviews": upcoming_interviews,
        "offers_sent": offers_sent,
        "offers_accepted": offers_accepted,
        "joining_this_week": joining_this_week,
        "pending_tasks": pending_tasks,
        "pending_feedback": pending_feedback,
    }


# ------------------------------------------------------------------------------
# MODULE 16 – Audit Logs
# ------------------------------------------------------------------------------

@router.get("/audit-logs")
def list_audit_logs(
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details,
            "timestamp": l.timestamp,
        }
        for l in logs
    ]
