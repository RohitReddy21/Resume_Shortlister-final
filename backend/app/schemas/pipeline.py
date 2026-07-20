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
    headline: Optional[str] = None
    current_package: Optional[str] = None
    expected_package: Optional[str] = None
    notice_period: Optional[str] = None
    summary: Optional[str] = None


class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    headline: Optional[str] = None
    current_package: Optional[str] = None
    expected_package: Optional[str] = None
    notice_period: Optional[str] = None
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
