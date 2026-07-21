from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.chat import (
    ResumeChatRequest,
    ChatSessionResponse,
)
from app.services.chat_service import (
    get_or_create_chat_session,
    generate_chat_response_stream,
)
from app.models.ats import ChatMessage

router = APIRouter()


@router.get("/ai/chat/{candidate_id}", response_model=ChatSessionResponse)
def get_chat_history(
    candidate_id: str,
    job_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session = get_or_create_chat_session(db, candidate_id, job_id)
    return ChatSessionResponse.model_validate(chat_session)


@router.post("/ai/resume-chat")
async def resume_chat(
    request: ResumeChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session = get_or_create_chat_session(
        db, request.candidate_id, request.job_id
    )

    async def response_generator():
        async for chunk in generate_chat_response_stream(
            db,
            request.candidate_id,
            request.job_id,
            request.message,
            chat_session,
        ):
            yield chunk

    return StreamingResponse(
        response_generator(),
        media_type="text/plain",
    )
