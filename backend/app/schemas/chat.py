from typing import List, Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatMessageBase(BaseModel):
    role: str
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageResponse(ChatMessageBase):
    id: str
    session_id: str
    citations: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    suggested_questions: Optional[List[str]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionBase(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ResumeChatRequest(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    message: str


class ResumeChatResponse(BaseModel):
    answer: str
    citations: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    suggested_questions: Optional[List[str]] = None
