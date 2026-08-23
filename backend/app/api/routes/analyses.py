import asyncio
import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_db
from app.dependencies import get_current_user, owned_analysis
from app.ml.video import VideoValidationError, inspect_video
from app.models import Analysis, AnalysisMedia, HumanReview, ReviewNote, User, VideoFrame
from app.schemas import AnalysisCreated, NoteRequest, ReviewRequest
from app.services.audit import add_audit, add_event
from app.services.processor import process_analysis
from app.services.storage import storage


router = APIRouter(prefix="/analyses", tags=["analyses"])
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi"}
VIDEO_MIMES = {"video/mp4", "video/quicktime", "video/webm", "video/x-msvideo", "application/octet-stream"}


def _base(analysis: Analysis) -> dict:
    latest_review = analysis.reviews[-1] if analysis.reviews else None
    return {
        "id": analysis.id,
        "media_type": analysis.media_type,
        "original_filename": analysis.original_filename,
        "mime_type": analysis.mime_type,
        "file_size": analysis.file_size,
        "sha256": analysis.sha256,
        "width": analysis.width,
        "height": analysis.height,
        "duration": analysis.duration,
        "fps": analysis.fps,
        "status": analysis.status,
        "mode": analysis.mode,
        "model_id": analysis.model_id,
        "model_version": analysis.model_version,
        "fake_probability": analysis.fake_probability,
        "real_probability": analysis.real_probability,
        "classification": analysis.classification,
        "quality_status": analysis.quality_status,
        "analysis_scope": analysis.analysis_scope,
        "analysed_frames": analysis.analysed_frames,
        "valid_frames": analysis.valid_frames,
        "aggregate": analysis.aggregate_metadata,
        "thresholds": analysis.thresholds,
        "failure_reason": analysis.failure_reason,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
        "review": ({"decision": latest_review.decision, "rationale": latest_review.rationale, "created_at": latest_review.created_at} if latest_review else None),
        "has_preview": bool(analysis.media and analysis.media.preview_path),
    }


def _detail(analysis: Analysis) -> dict:
    data = _base(analysis)
    data["quality"] = (
        {
            "status": analysis.quality.status,
            "blur_score": analysis.quality.blur_score,
            "brightness": analysis.quality.brightness,
            "contrast": analysis.quality.contrast,
            "face_detected": analysis.quality.face_detected,
            "face_box": analysis.quality.face_box,
            "warnings": analysis.quality.warnings or [],
            "details": analysis.quality.details,
        }
        if analysis.quality
        else None
    )
    main_evidence = next((item for item in analysis.evidence if item.frame_id is None), None)
    data["evidence"] = (
        {
            "available": main_evidence.available,
            "method": main_evidence.method,
            "has_attention": bool(main_evidence.grayscale_path),
            "has_heatmap": bool(main_evidence.heatmap_path),
            "has_overlay": bool(main_evidence.overlay_path),
            "has_crop": bool(main_evidence.crop_path),
            "metadata": main_evidence.metadata_json,
        }
        if main_evidence
        else None
    )
    data["events"] = [
        {"id": event.id, "stage": event.stage, "message": event.message, "metadata": event.metadata_json, "created_at": event.created_at}
        for event in analysis.events
    ]
    data["notes"] = [{"id": note.id, "note": note.note, "created_at": note.created_at} for note in analysis.notes]
    data["explanation"] = analysis.explanations[-1].content if analysis.explanations else None
    return data


async def _create_upload(
    media_type: str,
    file: UploadFile,
    mode: str,
    retain_original: bool,
    background_tasks: BackgroundTasks,
    user: User,
    db: Session,
) -> AnalysisCreated:
    filename = storage.safe_name(file.filename or "media")
    extension = Path(filename).suffix.lower()
    allowed_ext = IMAGE_EXTENSIONS if media_type == "IMAGE" else VIDEO_EXTENSIONS
    allowed_mimes = IMAGE_MIMES if media_type == "IMAGE" else VIDEO_MIMES
    max_bytes = (settings.max_image_mb if media_type == "IMAGE" else settings.max_video_mb) * 1024 * 1024
    if extension not in allowed_ext or (file.content_type or "") not in allowed_mimes:
        raise HTTPException(status_code=415, detail="Unsupported media type")
    content = await file.read(max_bytes + 1)
    if not content or len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="The selected file exceeds the configured size limit")

    analysis = Analysis(
        user_id=user.id,
        media_type=media_type,
        original_filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        mode=mode if mode in {"standard", "detailed"} else "standard",
        status="CREATED",
    )
    db.add(analysis)
    db.flush()
    source = storage.write(user.id, analysis.id, f"source{extension}", content)
    metadata = None
    try:
        if media_type == "IMAGE":
            with Image.open(source) as decoded:
                decoded.verify()
            with Image.open(source) as decoded:
                analysis.width, analysis.height = decoded.size
        else:
            metadata = inspect_video(source)
            if metadata["duration"] > settings.max_video_seconds:
                raise HTTPException(status_code=413, detail="The selected video exceeds the configured duration limit")
            analysis.width = metadata["width"]
            analysis.height = metadata["height"]
            analysis.duration = metadata["duration"]
            analysis.fps = metadata["fps"]
    except HTTPException:
        storage.delete_analysis(user.id, analysis.id)
        db.rollback()
        raise
    except (UnidentifiedImageError, OSError, VideoValidationError) as exc:
        storage.delete_analysis(user.id, analysis.id)
        db.rollback()
        raise HTTPException(status_code=422, detail="The selected media could not be decoded") from exc
    analysis.media = AnalysisMedia(
        source_path=str(source), retained=settings.store_original_media or retain_original, metadata_json=metadata
    )
    duplicate = db.scalar(
        select(Analysis.id)
        .where(Analysis.user_id == user.id, Analysis.sha256 == analysis.sha256, Analysis.id != analysis.id)
        .order_by(desc(Analysis.created_at))
    )
    db.commit()
    add_event(db, analysis.id, "CREATED", "Media accepted and queued")
    add_audit(db, user.id, "ANALYSIS_CREATED", analysis.id, new={"media_type": media_type, "sha256": analysis.sha256})
    background_tasks.add_task(process_analysis, analysis.id)
    return AnalysisCreated(id=analysis.id, status=analysis.status, duplicate_analysis_id=duplicate)


@router.post("/image", response_model=AnalysisCreated, status_code=202)
async def analyse_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = Form("standard"),
    retain_original: bool = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _create_upload("IMAGE", file, mode, retain_original, background_tasks, user, db)


@router.post("/video", response_model=AnalysisCreated, status_code=202)
async def analyse_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = Form("standard"),
    retain_original: bool = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _create_upload("VIDEO", file, mode, retain_original, background_tasks, user, db)


@router.get("")
def list_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Analysis).where(Analysis.user_id == user.id).order_by(desc(Analysis.created_at))).all()
    return [_base(item) for item in items]


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(owned_analysis(db, analysis_id, user.id))


@router.get("/{analysis_id}/status")
def get_status(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    return {"id": analysis.id, "status": analysis.status, "classification": analysis.classification, "failure_reason": analysis.failure_reason}


@router.get("/{analysis_id}/events")
def get_events(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    return _detail(analysis)["events"]


@router.get("/{analysis_id}/events/stream")
async def stream_events(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_analysis(db, analysis_id, user.id)

    async def generate():
        seen: set[str] = set()
        for _ in range(300):
            with SessionLocal() as stream_db:
                analysis = owned_analysis(stream_db, analysis_id, user.id)
                for event in analysis.events:
                    if event.id not in seen:
                        seen.add(event.id)
                        payload = {"id": event.id, "stage": event.stage, "message": event.message, "created_at": event.created_at.isoformat()}
                        yield f"data: {json.dumps(payload)}\n\n"
                if analysis.status in {"COMPLETED", "FAILED"}:
                    break
            await asyncio.sleep(1)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{analysis_id}/frames")
def get_frames(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    return [
        {
            "id": frame.id,
            "frame_index": frame.frame_index,
            "timestamp_ms": frame.timestamp_ms,
            "width": frame.width,
            "height": frame.height,
            "face_detected": frame.face_detected,
            "quality_status": frame.quality_status,
            "fake_probability": frame.fake_probability,
            "real_probability": frame.real_probability,
            "classification": frame.classification,
            "attention_available": frame.attention_available,
        }
        for frame in analysis.frames
    ]


@router.get("/{analysis_id}/evidence")
def get_evidence(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    return _detail(analysis)["evidence"]


@router.get("/{analysis_id}/summary")
def get_summary(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    return {key: _detail(analysis)[key] for key in ("classification", "fake_probability", "real_probability", "quality", "review", "explanation")}


def _asset_response(path: str | None) -> FileResponse:
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Asset not available")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=300"})


@router.get("/{analysis_id}/assets/{kind}")
def analysis_asset(kind: str, analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    evidence = next((item for item in analysis.evidence if item.frame_id is None), None)
    paths = {
        "preview": analysis.media.preview_path if analysis.media else None,
        "original": analysis.media.preview_path if analysis.media else None,
        "analysed": evidence.crop_path if evidence else None,
        "attention": evidence.grayscale_path if evidence else None,
        "heatmap": evidence.heatmap_path if evidence else None,
        "overlay": evidence.overlay_path if evidence else None,
    }
    if kind not in paths:
        raise HTTPException(status_code=404, detail="Unknown asset")
    return _asset_response(paths[kind])


@router.get("/{analysis_id}/frames/{frame_id}/assets/{kind}")
def frame_asset(kind: str, analysis_id: str, frame_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    frame = next((item for item in analysis.frames if item.id == frame_id), None)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")
    paths = {"preview": frame.preview_path, "original": frame.preview_path, "overlay": frame.overlay_path}
    if kind not in paths:
        raise HTTPException(status_code=404, detail="Unknown frame asset")
    return _asset_response(paths[kind])


@router.post("/{analysis_id}/review")
def review(payload: ReviewRequest, analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    previous = analysis.reviews[-1].decision if analysis.reviews else None
    item = HumanReview(analysis_id=analysis.id, user_id=user.id, decision=payload.decision, rationale=payload.rationale)
    db.add(item)
    db.commit()
    add_audit(db, user.id, "HUMAN_REVIEW_UPDATED", analysis.id, previous={"decision": previous}, new={"decision": payload.decision}, note=payload.rationale, model_id=analysis.model_id)
    return {"id": item.id, "decision": item.decision, "rationale": item.rationale, "created_at": item.created_at}


@router.post("/{analysis_id}/notes")
def add_note(payload: NoteRequest, analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    note = ReviewNote(analysis_id=analysis.id, user_id=user.id, note=payload.note)
    db.add(note)
    db.commit()
    add_audit(db, user.id, "NOTE_ADDED", analysis.id, new={"note_id": note.id})
    return {"id": note.id, "note": note.note, "created_at": note.created_at}


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = owned_analysis(db, analysis_id, user.id)
    add_audit(db, user.id, "ANALYSIS_DELETED", analysis.id, previous={"filename": analysis.original_filename})
    storage.delete_analysis(user.id, analysis.id)
    db.delete(analysis)
    db.commit()
