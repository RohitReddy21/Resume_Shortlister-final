from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class InterviewFeedback(Base):
    __tablename__ = "interview_feedbacks"

    id = Column(String, primary_key=True, index=True)
    interview_id = Column(String, ForeignKey("interviews.id"), nullable=False, index=True)
    interviewer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    technical_skills = Column(Integer, nullable=True) # 1 to 5
    communication = Column(Integer, nullable=True)
    problem_solving = Column(Integer, nullable=True)
    teamwork = Column(Integer, nullable=True)
    leadership = Column(Integer, nullable=True)
    domain_knowledge = Column(Integer, nullable=True)
    coding_skills = Column(Integer, nullable=True)
    
    overall_rating = Column(Float, nullable=True)
    recommendation = Column(
        Enum("Strong Hire", "Hire", "Hold", "Reject", name="feedback_recommendation"),
        nullable=False,
        default="Hold"
    )
    remarks = Column(Text, nullable=True)
    attachment_path = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    interview = relationship("Interview", backref="feedbacks")
    interviewer = relationship("User")


class InterviewPanelMember(Base):
    __tablename__ = "interview_panel_members"

    id = Column(String, primary_key=True, index=True)
    interview_id = Column(String, ForeignKey("interviews.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role_name = Column(String(100), nullable=True) # HR, Technical Interviewer, Hiring Manager
    panel_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview = relationship("Interview", backref="panel_members")
    user = relationship("User")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(String, primary_key=True, index=True)
    offer_number = Column(String(50), nullable=False, unique=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    
    salary_offered = Column(Float, nullable=False, default=0.0)
    bonus = Column(Float, nullable=True, default=0.0)
    joining_bonus = Column(Float, nullable=True, default=0.0)
    joining_date = Column(DateTime(timezone=True), nullable=True)
    offer_expiry = Column(DateTime(timezone=True), nullable=True)
    
    offer_status = Column(
        Enum("Draft", "Sent", "Accepted", "Declined", "Expired", name="offer_status"),
        nullable=False,
        default="Draft"
    )
    notes = Column(Text, nullable=True)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="offers")
    job = relationship("Job", backref="offers")
    created_by = relationship("User")


class OfferDocument(Base):
    __tablename__ = "offer_documents"

    id = Column(String, primary_key=True, index=True)
    offer_id = Column(String, ForeignKey("offers.id"), nullable=False, index=True)
    document_type = Column(
        Enum("Offer Letter", "Compensation Letter", "Employment Agreement", "NDA", "Other", name="offer_doc_type"),
        nullable=False,
        default="Offer Letter"
    )
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    offer = relationship("Offer", backref="documents")


class JoiningRecord(Base):
    __tablename__ = "joining_records"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    offer_id = Column(String, ForeignKey("offers.id"), nullable=True, index=True)
    
    joining_date = Column(DateTime(timezone=True), nullable=False)
    joining_status = Column(
        Enum("Pending", "Joined", "Delayed", "Cancelled", name="joining_status"),
        nullable=False,
        default="Pending"
    )
    reporting_manager_id = Column(String, ForeignKey("users.id"), nullable=True)
    office_location = Column(String(255), nullable=True)
    employee_id = Column(String(100), nullable=True, unique=True)
    department = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="joining_records")
    offer = relationship("Offer", backref="joining_record")
    reporting_manager = relationship("User")


class CandidateCommunication(Base):
    __tablename__ = "candidate_communications"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    communication_type = Column(
        Enum("Email", "Phone Call", "SMS", "WhatsApp Note", "Meeting Note", name="communication_type"),
        nullable=False,
        default="Email"
    )
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="communications")
    user = relationship("User")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    template_type = Column(
        Enum("Interview Invitation", "Interview Reminder", "Interview Reschedule", "Offer Letter", "Joining Reminder", "Rejection", "Follow-up", name="email_template_type"),
        nullable=False
    )
    subject_template = Column(String(255), nullable=False)
    body_template = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CandidateDocumentVault(Base):
    __tablename__ = "candidate_document_vault"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    document_type = Column(
        Enum("Resume", "Cover Letter", "Offer Letter", "Educational Certificates", "Experience Certificates", "Salary Slips", "Government ID", "Other Documents", name="vault_doc_type"),
        nullable=False
    )
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    candidate = relationship("Candidate", backref="vault_documents")


class CandidateChecklistItem(Base):
    __tablename__ = "candidate_checklist_items"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    verified_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    candidate = relationship("Candidate", backref="checklist_items")
    verified_by = relationship("User")


class RecruiterTask(Base):
    __tablename__ = "recruiter_tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    task_type = Column(
        Enum("Call Candidate", "Verify Documents", "Schedule Interview", "Send Offer", "Follow Up", name="recruiter_task_type"),
        nullable=False,
        default="Follow Up"
    )
    status = Column(
        Enum("Pending", "Completed", "Cancelled", name="recruiter_task_status"),
        nullable=False,
        default="Pending"
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    assigned_to_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    assigned_to = relationship("User")
    candidate = relationship("Candidate", backref="tasks")


class SystemReminder(Base):
    __tablename__ = "system_reminders"

    id = Column(String, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    reminder_type = Column(
        Enum("Interview Reminder", "Offer Expiry Reminder", "Joining Reminder", "Document Reminder", "Task Reminder", name="system_reminder_type"),
        nullable=False
    )
    remind_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(
        Enum("Pending", "Triggered", "Dismissed", name="reminder_status"),
        nullable=False,
        default="Pending"
    )
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
