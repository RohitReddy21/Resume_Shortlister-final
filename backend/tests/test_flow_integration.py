import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import BackgroundTasks
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers.pipeline import create_application, list_applications, move_application_stage
from app.core.database import Base
from app.models.ats import ActivityLog, Application, Candidate, CandidateSkill, Experience, Job, Notification, Resume, ResumeVersion, Skill
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.pipeline import ApplicationCreate, ApplicationStageUpdate
from app.services.parser.tasks import _sync_candidate_profile


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def test_parsed_resume_sections_sync_to_candidate_profile_tables():
    db = make_session()
    try:
        candidate = Candidate(
            id="candidate-1",
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        parsed = {
            "current_company": "Acme Corp",
            "skills": [{"name": "Python"}, {"name": "Docker"}],
            "experiences": [{"title_company": "Senior Engineer at Acme Corp", "raw": "2019 - Present"}],
            "education": [{"raw": "Bachelor of Science in Computer Science"}],
            "certifications": [{"raw": "AWS Certified Solutions Architect"}],
        }

        _sync_candidate_profile(db, candidate, parsed)
        db.commit()

        assert db.query(Skill).count() == 2
        assert db.query(CandidateSkill).count() == 2
        assert db.query(Experience).one().title == "Senior Engineer"
        assert candidate.headline == "Current: Acme Corp"
    finally:
        db.close()


def test_create_application_adds_pipeline_activity_and_notification():
    db = make_session()
    try:
        user = User(
            id="user-1",
            email="recruiter@example.com",
            full_name="Recruiter One",
            role="Recruiter",
        )
        candidate = Candidate(
            id="candidate-1",
            user_id=user.id,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
        )
        job = Job(id="job-1", title="Frontend Engineer", description="Python frontend role", skills='["Python"]', status="published")
        resume = Resume(id="resume-1", candidate_id=candidate.id, title="jane.pdf", source="upload")
        db.add_all([user, candidate, job, resume])
        db.commit()
        version = ResumeVersion(
            id="version-1",
            resume_id=resume.id,
            version_number=1,
            content="Python frontend engineer",
            parsed_json='{"skills":[{"name":"Python"}],"parsed_text":"Python frontend engineer","experiences":[{"raw":"Frontend Engineer"}],"education":[{"raw":"BS"}],"emails":[{"value":"jane@example.com"}],"phones":[{"value":"555"}]}',
        )
        db.add(version)
        resume.current_version_id = version.id
        db.add(resume)
        db.commit()

        result = create_application(
            ApplicationCreate(candidate_id=candidate.id, job_id=job.id, resume_id=resume.id),
            db=db,
            current_user=user,
        )

        assert result.status in {"Screening", "Shortlisted"}
        assert result.match_score is not None
        assert result.candidate.id == candidate.id
        rows = list_applications(db=db)
        assert len(rows) == 1
        assert rows[0]["candidate"]["name"] == "Jane Doe"
        assert rows[0]["job"]["title"] == "Frontend Engineer"
        assert rows[0]["status"] == result.status
        assert db.query(Application).count() == 1
        assert db.query(ActivityLog).filter(ActivityLog.action == "automated_shortlist").count() == 1
        assert db.query(Notification).filter(Notification.user_id == user.id).count() == 1
    finally:
        db.close()


def test_rejected_application_removes_candidate_resume_and_parsed_data():
    db = make_session()
    try:
        user = User(
            id="user-1",
            email="recruiter@example.com",
            full_name="Recruiter One",
            role="Recruiter",
        )
        candidate = Candidate(
            id="candidate-1",
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
        )
        job = Job(id="job-1", title="Frontend Engineer", description="Python frontend role", skills='["Python"]', status="published")
        resume = Resume(id="resume-1", candidate_id=candidate.id, title="jane.pdf", source="upload")
        db.add_all([user, candidate, job, resume])
        db.commit()
        version = ResumeVersion(
            id="version-1",
            resume_id=resume.id,
            version_number=1,
            content="Python frontend engineer",
            parsed_json='{"skills":[{"name":"Python"}],"parsed_text":"Python frontend engineer","experiences":[{"raw":"Frontend Engineer"}],"education":[{"raw":"BS"}],"emails":[{"value":"jane@example.com"}],"phones":[{"value":"555"}]}',
        )
        db.add(version)
        resume.current_version_id = version.id
        db.add(resume)
        db.commit()

        created = create_application(
            ApplicationCreate(candidate_id=candidate.id, job_id=job.id, resume_id=resume.id),
            db=db,
            current_user=user,
        )
        candidate_id = candidate.id

        result = move_application_stage(
            created.id,
            ApplicationStageUpdate(stage="Rejected"),
            BackgroundTasks(),
            db=db,
            current_user=user,
        )

        assert result["deleted"] is True
        assert result["deleted_scope"] == "candidate"
        assert result["candidate_id"] == candidate_id
        assert db.query(Candidate).count() == 0
        assert db.query(Application).count() == 0
        assert db.query(Resume).count() == 0
        assert db.query(ResumeVersion).count() == 0
        assert db.query(ActivityLog).count() == 0
    finally:
        db.close()
