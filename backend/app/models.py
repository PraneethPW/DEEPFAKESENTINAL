import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class MediaType(str, enum.Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class AnalysisStatus(str, enum.Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    DECODING = "DECODING"
    QUALITY_CHECK = "QUALITY_CHECK"
    EXTRACTING_FRAMES = "EXTRACTING_FRAMES"
    DETECTING_FACES = "DETECTING_FACES"
    PREPROCESSING = "PREPROCESSING"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    GENERATING_EVIDENCE = "GENERATING_EVIDENCE"
    AGGREGATING = "AGGREGATING"
    AI_EXPLANATION = "AI_EXPLANATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Classification(str, enum.Enum):
    LIKELY_AUTHENTIC = "LIKELY_AUTHENTIC"
    LIKELY_MANIPULATED = "LIKELY_MANIPULATED"
    INCONCLUSIVE = "INCONCLUSIVE"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    media_type: Mapped[str] = mapped_column(String(16))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float | None] = mapped_column(Float)
    fps: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default=AnalysisStatus.CREATED.value, index=True)
    mode: Mapped[str] = mapped_column(String(20), default="standard")
    model_id: Mapped[str | None] = mapped_column(String(255))
    model_version: Mapped[str | None] = mapped_column(String(100))
    fake_probability: Mapped[float | None] = mapped_column(Float)
    real_probability: Mapped[float | None] = mapped_column(Float)
    classification: Mapped[str | None] = mapped_column(String(40), index=True)
    quality_status: Mapped[str | None] = mapped_column(String(20), index=True)
    analysis_scope: Mapped[str | None] = mapped_column(String(40))
    analysed_frames: Mapped[int] = mapped_column(Integer, default=0)
    valid_frames: Mapped[int] = mapped_column(Integer, default=0)
    aggregate_metadata: Mapped[dict | None] = mapped_column(JSON)
    thresholds: Mapped[dict | None] = mapped_column(JSON)
    application_version: Mapped[str | None] = mapped_column(String(40))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="analyses")
    media: Mapped["AnalysisMedia | None"] = relationship(back_populates="analysis", cascade="all, delete-orphan", uselist=False)
    prediction: Mapped["Prediction | None"] = relationship(back_populates="analysis", cascade="all, delete-orphan", uselist=False)
    quality: Mapped["QualitySignal | None"] = relationship(back_populates="analysis", cascade="all, delete-orphan", uselist=False)
    evidence: Mapped[list["EvidenceMap"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    events: Mapped[list["AnalysisEvent"]] = relationship(back_populates="analysis", cascade="all, delete-orphan", order_by="AnalysisEvent.created_at")
    frames: Mapped[list["VideoFrame"]] = relationship(back_populates="analysis", cascade="all, delete-orphan", order_by="VideoFrame.timestamp_ms")
    reviews: Mapped[list["HumanReview"]] = relationship(back_populates="analysis", cascade="all, delete-orphan", order_by="HumanReview.created_at")
    notes: Mapped[list["ReviewNote"]] = relationship(back_populates="analysis", cascade="all, delete-orphan", order_by="ReviewNote.created_at")
    explanations: Mapped[list["AIExplanation"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class AnalysisMedia(Base):
    __tablename__ = "analysis_media"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    source_path: Mapped[str | None] = mapped_column(Text)
    preview_path: Mapped[str | None] = mapped_column(Text)
    retained: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    analysis: Mapped[Analysis] = relationship(back_populates="media")


class AnalysisEvent(Base):
    __tablename__ = "analysis_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analysis: Mapped[Analysis] = relationship(back_populates="events")


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    fake_probability: Mapped[float] = mapped_column(Float)
    real_probability: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(40))
    raw_label_scores: Mapped[dict | None] = mapped_column(JSON)
    calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analysis: Mapped[Analysis] = relationship(back_populates="prediction")


class QualitySignal(Base):
    __tablename__ = "quality_signals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    blur_score: Mapped[float | None] = mapped_column(Float)
    brightness: Mapped[float | None] = mapped_column(Float)
    contrast: Mapped[float | None] = mapped_column(Float)
    face_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    face_box: Mapped[dict | None] = mapped_column(JSON)
    warnings: Mapped[list | None] = mapped_column(JSON)
    details: Mapped[dict | None] = mapped_column(JSON)
    analysis: Mapped[Analysis] = relationship(back_populates="quality")


class EvidenceMap(Base):
    __tablename__ = "evidence_maps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    frame_id: Mapped[str | None] = mapped_column(ForeignKey("video_frames.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(40), default="ATTENTION_ROLLOUT")
    grayscale_path: Mapped[str | None] = mapped_column(Text)
    heatmap_path: Mapped[str | None] = mapped_column(Text)
    overlay_path: Mapped[str | None] = mapped_column(Text)
    crop_path: Mapped[str | None] = mapped_column(Text)
    available: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    analysis: Mapped[Analysis] = relationship(back_populates="evidence")


class VideoFrame(Base):
    __tablename__ = "video_frames"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    frame_index: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    face_detected: Mapped[bool] = mapped_column(Boolean)
    face_box: Mapped[dict | None] = mapped_column(JSON)
    quality_status: Mapped[str] = mapped_column(String(20))
    fake_probability: Mapped[float | None] = mapped_column(Float)
    real_probability: Mapped[float | None] = mapped_column(Float)
    classification: Mapped[str | None] = mapped_column(String(40))
    attention_available: Mapped[bool] = mapped_column(Boolean, default=False)
    preview_path: Mapped[str | None] = mapped_column(Text)
    overlay_path: Mapped[str | None] = mapped_column(Text)
    analysis: Mapped[Analysis] = relationship(back_populates="frames")


class HumanReview(Base):
    __tablename__ = "human_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    decision: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analysis: Mapped[Analysis] = relationship(back_populates="reviews")


class ReviewNote(Base):
    __tablename__ = "review_notes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analysis: Mapped[Analysis] = relationship(back_populates="notes")


class AIExplanation(Base):
    __tablename__ = "ai_explanations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="openrouter")
    model: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(40), default="SUMMARY")
    content: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analysis: Mapped[Analysis] = relationship(back_populates="explanations")


class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_id: Mapped[str] = mapped_column(String(255), index=True)
    revision: Mapped[str | None] = mapped_column(String(100))
    architecture: Mapped[str] = mapped_column(String(100))
    labels: Mapped[list | None] = mapped_column(JSON)
    evidence_method: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

