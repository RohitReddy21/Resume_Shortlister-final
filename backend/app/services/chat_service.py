import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import get_settings
from app.models.ats import (
    Candidate,
    Job,
    Resume,
    ResumeVersion,
    ChatSession,
    ChatMessage,
)
from app.services.ai.providers import AIProvider, OllamaProvider, OpenAIProvider

logger = logging.getLogger(__name__)
settings = get_settings()


def get_ai_provider() -> AIProvider:
    """Get the configured AI provider instance."""
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is not configured")
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    elif settings.ai_provider == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
    else:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}")


async def get_or_create_chat_session(
    db: Session,
    candidate_id: str,
    job_id: Optional[str] = None,
) -> ChatSession:
    stmt = (
        select(ChatSession)
        .where(ChatSession.candidate_id == candidate_id)
        .where(ChatSession.job_id == job_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    session = result.scalar_one_or_none()
    if session:
        return session
    new_session = ChatSession(
        id=str(uuid4()),
        candidate_id=candidate_id,
        job_id=job_id,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def get_candidate_parsed_resume(db: Session, candidate_id: str) -> Optional[Dict[str, Any]]:
    stmt = (
        select(ResumeVersion)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(Resume.candidate_id == candidate_id)
        .where(ResumeVersion.parsed_json.isnot(None))
        .order_by(ResumeVersion.created_at.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    resume_version = result.scalar_one_or_none()
    if resume_version:
        try:
            return json.loads(resume_version.parsed_json)
        except Exception as e:
            logger.error(f"Failed to parse resume JSON: {e}")
    return None


def get_job_details(db: Session, job_id: Optional[str]) -> Optional[Job]:
    if not job_id:
        return None
    stmt = select(Job).where(Job.id == job_id)
    result = db.execute(stmt)
    return result.scalar_one_or_none()


def build_system_prompt(
    candidate: Candidate,
    parsed_resume: Optional[Dict[str, Any]],
    job: Optional[Job],
) -> str:
    parts = [
        "You are an AI assistant for recruiters, helping them analyze candidates based on their resume.",
        "Only use information from the candidate's resume and job description (if provided) to answer questions.",
        "If you don't have information to answer a question, say so clearly.",
    ]

    if parsed_resume:
        parts.append("\n--- Candidate Resume Data ---")
        parts.append(json.dumps(parsed_resume, indent=2))

    if candidate:
        parts.append("\n--- Candidate Basic Info ---")
        parts.append(f"Name: {candidate.first_name} {candidate.last_name}")
        if candidate.email:
            parts.append(f"Email: {candidate.email}")
        if candidate.phone:
            parts.append(f"Phone: {candidate.phone}")
        if candidate.headline:
            parts.append(f"Headline: {candidate.headline}")

    if job:
        parts.append("\n--- Job Description ---")
        parts.append(f"Title: {job.title}")
        if job.description:
            parts.append(f"Description: {job.description}")
        if job.skills:
            parts.append(f"Skills: {job.skills}")

    return "\n".join(parts)


async def generate_chat_response_stream(
    db: Session,
    candidate_id: str,
    job_id: Optional[str],
    user_message: str,
    chat_session: ChatSession,
) -> AsyncGenerator[str, None]:
    candidate_stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate = db.execute(candidate_stmt).scalar_one_or_none()
    if not candidate:
        yield json.dumps({"error": "Candidate not found"})
        return

    parsed_resume = get_candidate_parsed_resume(db, candidate_id)
    job = get_job_details(db, job_id)

    # Get existing messages
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    existing_messages = db.execute(stmt).scalars().all()
    conversation_history = []
    for msg in existing_messages:
        conversation_history.append({"role": msg.role, "content": msg.content})

    # Save user message
    user_msg = ChatMessage(
        id=str(uuid4()),
        session_id=chat_session.id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    db.commit()

    try:
        provider = get_ai_provider()
        system_prompt = build_system_prompt(candidate, parsed_resume, job)

        full_response = ""
        async for delta_content in provider.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            conversation_history=conversation_history,
        ):
            full_response += delta_content
            yield delta_content

        # Generate suggested questions
        suggested_questions = [
            "Summarize this candidate.",
            "Explain employment gaps.",
            "What are the candidate's strengths?",
            "What are the candidate's weaknesses?",
            "Should I shortlist this candidate?",
            "Generate interview questions.",
        ]

        # Save assistant message
        assistant_msg = ChatMessage(
            id=str(uuid4()),
            session_id=chat_session.id,
            role="assistant",
            content=full_response,
            suggested_questions=suggested_questions,
            confidence=0.8,
        )
        db.add(assistant_msg)
        db.commit()

    except Exception as e:
        logger.error(f"Error generating chat response: {e}")
        yield json.dumps({"error": str(e)})
