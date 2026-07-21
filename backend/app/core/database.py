import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Support SQLite for local development (no Docker) and Postgres in production.
engine_kwargs = {"pool_pre_ping": True}
connect_args = {}
if settings.database_url.startswith("sqlite"):
    # SQLite needs check_same_thread for SQLAlchemy in many environments
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_schema_compatibility_migrations() -> None:
    """Patch older local databases that were created before the current models."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    def has_column(table_name: str, column_name: str) -> bool:
        return column_name in {column["name"] for column in inspector.get_columns(table_name)}

    with engine.begin() as connection:
        if "applications" in table_names:
            if not has_column("applications", "pipeline_order"):
                connection.execute(
                    text("ALTER TABLE applications ADD COLUMN pipeline_order INTEGER NOT NULL DEFAULT 0")
                )
            if not has_column("applications", "resume_id"):
                connection.execute(text("ALTER TABLE applications ADD COLUMN resume_id VARCHAR"))
            if not has_column("applications", "source"):
                connection.execute(text("ALTER TABLE applications ADD COLUMN source VARCHAR(100)"))
            if not has_column("applications", "notes"):
                connection.execute(text("ALTER TABLE applications ADD COLUMN notes TEXT"))
            if not has_column("applications", "match_score"):
                connection.execute(text("ALTER TABLE applications ADD COLUMN match_score FLOAT"))
            if not has_column("applications", "match_confidence"):
                connection.execute(text("ALTER TABLE applications ADD COLUMN match_confidence FLOAT"))
            if not has_column("applications", "shortlist_reason"):
                connection.execute(text("ALTER TABLE applications ADD COLUMN shortlist_reason TEXT"))

        if "candidates" in table_names:
            if not has_column("candidates", "current_package"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN current_package VARCHAR(100)"))
            if not has_column("candidates", "expected_package"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN expected_package VARCHAR(100)"))
            if not has_column("candidates", "notice_period"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN notice_period VARCHAR(100)"))
            if not has_column("candidates", "address"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN address VARCHAR(255)"))
            if not has_column("candidates", "linkedin"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN linkedin VARCHAR(255)"))
            if not has_column("candidates", "github"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN github VARCHAR(255)"))
            if not has_column("candidates", "portfolio"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN portfolio VARCHAR(255)"))
            if not has_column("candidates", "current_company"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN current_company VARCHAR(100)"))
            if not has_column("candidates", "current_designation"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN current_designation VARCHAR(100)"))
            if not has_column("candidates", "total_experience"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN total_experience VARCHAR(50)"))
            if not has_column("candidates", "relevant_experience"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN relevant_experience VARCHAR(50)"))
            if not has_column("candidates", "preferred_location"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN preferred_location VARCHAR(255)"))
            if not has_column("candidates", "employment_type"):
                connection.execute(text("ALTER TABLE candidates ADD COLUMN employment_type VARCHAR(50)"))

        if "interviews" in table_names:
            if not has_column("interviews", "interview_type"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN interview_type VARCHAR(50)"))
            if not has_column("interviews", "duration_minutes"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN duration_minutes INTEGER"))
            if not has_column("interviews", "duration_minutes_str"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN duration_minutes_str VARCHAR(50)"))
            if not has_column("interviews", "time_zone"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN time_zone VARCHAR(100)"))
            if not has_column("interviews", "meeting_link"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN meeting_link VARCHAR(500)"))
            if not has_column("interviews", "office_location"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN office_location VARCHAR(255)"))
            if not has_column("interviews", "interviewer_user_id"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN interviewer_user_id VARCHAR"))
            if not has_column("interviews", "rescheduled_from_id"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN rescheduled_from_id VARCHAR"))
            if not has_column("interviews", "created_by_id"):
                connection.execute(text("ALTER TABLE interviews ADD COLUMN created_by_id VARCHAR"))

        if "activity_logs" in table_names:
            if not has_column("activity_logs", "application_id"):
                connection.execute(text("ALTER TABLE activity_logs ADD COLUMN application_id VARCHAR"))
            if not has_column("activity_logs", "candidate_id"):
                connection.execute(text("ALTER TABLE activity_logs ADD COLUMN candidate_id VARCHAR"))
            if not has_column("activity_logs", "job_id"):
                connection.execute(text("ALTER TABLE activity_logs ADD COLUMN job_id VARCHAR"))

        if "comments" in table_names:
            if not has_column("comments", "mentions"):
                connection.execute(text("ALTER TABLE comments ADD COLUMN mentions TEXT"))

        if "notifications" in table_names:
            if not has_column("notifications", "link"):
                connection.execute(text("ALTER TABLE notifications ADD COLUMN link VARCHAR(255)"))
            if not has_column("notifications", "is_read"):
                connection.execute(
                    text("ALTER TABLE notifications ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0")
                )
            if not has_column("notifications", "level"):
                connection.execute(
                    text("ALTER TABLE notifications ADD COLUMN level VARCHAR(50) NOT NULL DEFAULT 'info'")
                )


def _ensure_admin_user() -> None:
    """Ensure an admin user exists based on environment variables."""
    from app.crud.user import get_user_by_email, create_user
    from app.core.security import get_password_hash

    admin_email = settings.admin_email
    admin_password = settings.admin_password

    if not admin_email or not admin_password:
        logger.warning("ADMIN_EMAIL or ADMIN_PASSWORD not set. Skipping admin user creation.")
        return

    db = SessionLocal()
    try:
        existing_admin = get_user_by_email(db, admin_email)
        if existing_admin:
            logger.info(f"Admin user already exists: {admin_email}")
            return

        admin_user = create_user(
            db,
            email=admin_email,
            full_name="Administrator",
            password=admin_password,
            role="Admin",
            auth_provider="local"
        )
        logger.info(f"Created admin user: {admin_email} (id={admin_user.id})")
    finally:
        db.close()


def init_db() -> None:
    # Import models to ensure they are registered on Base before create_all
    from app.models.user import User
    from app.models.refresh_token import RefreshToken
    from app.models.ats import (
        ActivityLog,
        AuditLog,
        Application,
        Candidate,
        CandidateSkill,
        Certification,
        Comment,
        Company,
        Department,
        Education,
        Experience,
        HiringManager,
        Interview,
        Job,
        JobSkill,
        Notification,
        Permission,
        Resume,
        ResumeVersion,
        Role,
        RolePermission,
        Session,
        Skill,
        UserCompany,
        ChatSession,
        ChatMessage,
    )

    Base.metadata.create_all(bind=engine)
    _run_schema_compatibility_migrations()
    _ensure_admin_user()
