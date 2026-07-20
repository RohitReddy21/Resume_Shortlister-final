from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ATSScoreResponse(BaseModel):
    job_id: str
    resume_id: str
    total_score: float = Field(..., ge=0.0, le=1.0)
    score_percentage: float = Field(..., ge=0.0, le=100.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    weights: Dict[str, float]
    component_scores: Dict[str, float]
    score_breakdown: Dict[str, str] = Field(default_factory=dict)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    explanation: str | None = None

    model_config = ConfigDict(from_attributes=True)
