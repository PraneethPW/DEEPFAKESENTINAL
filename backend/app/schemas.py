from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReviewRequest(BaseModel):
    decision: Literal[
        "MARK_FOR_REVIEW", "CONFIRM_AUTHENTIC", "CONFIRM_MANIPULATED", "MARK_INCONCLUSIVE"
    ]
    rationale: str | None = Field(default=None, max_length=2000)


class NoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class ExplainRequest(BaseModel):
    analysis_id: str


class AskRequest(BaseModel):
    analysis_id: str
    question: str = Field(min_length=2, max_length=1000)
    selected_frame_id: str | None = None


class ExplanationOut(BaseModel):
    summary: str
    evidence_interpretation: str
    quality_context: str
    recommended_review: str
    limitations: str


class AnalysisCreated(BaseModel):
    id: str
    status: str
    duplicate_analysis_id: str | None = None


class ModelStatus(BaseModel):
    model_id: str
    architecture: str = "Vision Transformer"
    device: str
    labels: list[str]
    loaded: bool
    calibrated: bool = False
    evidence_method: str = "ATTENTION_ROLLOUT"
    error: str | None = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    stage: str
    message: str
    metadata_json: dict[str, Any] | None
    created_at: datetime


class DashboardOut(BaseModel):
    totals: dict[str, int]
    classification_distribution: list[dict[str, Any]]
    media_distribution: list[dict[str, Any]]
    quality_distribution: list[dict[str, Any]]
    review_distribution: list[dict[str, Any]]
    activity: list[dict[str, Any]]
    recent: list[dict[str, Any]]

