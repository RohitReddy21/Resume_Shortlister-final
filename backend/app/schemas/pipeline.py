from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict


PIPELINE_STAGES = [
    "Applied",
    "Screening",
    "Shortlisted",
    "Interview",
    "Technical",
    "HR",
    "Offer",
    "Hired",
    "Rejected",
]


# ── Stage move ────────────────────────────────────────────────────────────────

class ApplicationStageUpdate(BaseModel):
    stage: Literal[
        "Applied", "Screening", "Shortlisted", "Interview",
        "Technical", "HR", "Offer", "Hired", "Rejected"
    ]
    pipeline_order: Optional[int] = None


class ApplicationCreate(BaseModel):
    candidate_id: str
    job_id: str
    resume_id: Optional[str] = None
    status: Literal[
        "Applied", "Screening", "Shortlisted", "Interview",
        "Technical", "HR", "Offer", "Hired", "Rejected"
    ] = "Applied"
    source: Optional[str] = "resume_upload"
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[Literal[
        "Applied", "Screening", "Shortlisted", "Interview",
        "Technical", "HR", "Offer", "Hired", "Rejected"
    ]] = None
    pipeline_order: Optional[int] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class CandidateCreate(BaseModel):
    first_name: str
    last_name: Optional[str] = ""
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    headline: Optional[str] = None
    current_company: Optional[str] = None
    current_designation: Optional[str] = None
    total_experience: Optional[str] = None
    relevant_experience: Optional[str] = None
    current_package: Optional[str] = None
    expected_package: Optional[str] = None
    notice_period: Optional[str] = None
    preferred_location: Optional[str] = None
    employment_type: Optional[str] = None
    summary: Optional[str] = None


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    headline: Optional[str] = None
    current_company: Optional[str] = None
    current_designation: Optional[str] = None
    total_experience: Optional[str] = None
    relevant_experience: Optional[str] = None
    current_package: Optional[str] = None
    expected_package: Optional[str] = None
    notice_period: Optional[str] = None
    preferred_location: Optional[str] = None
    employment_type: Optional[str] = None
    summary: Optional[str] = None


class CandidateCompensationUpdate(BaseModel):
    current_package: Optional[str] = None
    expected_package: Optional[str] = None
    notice_period: Optional[str] = None


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body: str
    mentions: List[str] = []  # list of user_ids


class CommentUpdate(BaseModel):
    body: str
    mentions: List[str] = []


class CommentOut(BaseModel):
    id: str
    application_id: str
    author_id: str
    author_name: str
    body: str
    mentions: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Activity ──────────────────────────────────────────────────────────────────

class ActivityOut(BaseModel):
    id: str
    action: str
    details: Optional[str] = None
    author_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Kanban card ───────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    level: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateSnippet(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    headline: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationKanbanOut(BaseModel):
    id: str
    status: str
    pipeline_order: int
    match_score: Optional[float] = None
    match_confidence: Optional[float] = None
    shortlist_reason: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    applied_at: datetime
    updated_at: datetime
    candidate: CandidateSnippet
    comment_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class KanbanBoardOut(BaseModel):
    job_id: str
    job_title: str
    columns: dict[str, List[ApplicationKanbanOut]]


class InterviewCreate(BaseModel):
    candidate_id: str
    job_id: str
    application_id: Optional[str] = None
    interview_type: Optional[Literal[
        "HR Interview", "Technical Interview", "Manager Round", "Final Round", "Client Round"
    ]] = None
    scheduled_at: datetime
    duration_minutes: Optional[int] = None
    duration_minutes_str: Optional[str] = None
    time_zone: Optional[str] = None
    meeting_link: Optional[str] = None
    office_location: Optional[str] = None
    location: Optional[str] = None
    mode: Optional[str] = None
    interviewer: Optional[str] = None
    interviewer_user_id: Optional[str] = None
    notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    interview_type: Optional[Literal[
        "HR Interview", "Technical Interview", "Manager Round", "Final Round", "Client Round"
    ]] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    duration_minutes_str: Optional[str] = None
    time_zone: Optional[str] = None
    meeting_link: Optional[str] = None
    office_location: Optional[str] = None
    location: Optional[str] = None
    mode: Optional[str] = None
    interviewer: Optional[str] = None
    interviewer_user_id: Optional[str] = None
    status: Optional[Literal[
        "Scheduled", "Completed", "Cancelled", "No Show", "Rescheduled"
    ]] = None
    notes: Optional[str] = None


class InterviewOut(BaseModel):
    id: str
    application_id: Optional[str] = None
    candidate_id: str
    candidate_name: Optional[str] = None
    job_id: str
    job_title: Optional[str] = None
    interview_type: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: Optional[int] = None
    duration_minutes_str: Optional[str] = None
    time_zone: Optional[str] = None
    meeting_link: Optional[str] = None
    office_location: Optional[str] = None
    location: Optional[str] = None
    mode: Optional[str] = None
    interviewer: Optional[str] = None
    interviewer_user_id: Optional[str] = None
    interviewer_name: Optional[str] = None
    created_by_id: Optional[str] = None
    created_by_name: Optional[str] = None
    status: str
    rescheduled_from_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
