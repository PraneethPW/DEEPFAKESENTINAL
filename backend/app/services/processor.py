import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from app.config import settings
from app.db import SessionLocal
from app.ml.aggregation import aggregate_probabilities
from app.ml.attention import attention_rollout, render_evidence
from app.ml.inference import run_inference
from app.ml.model_loader import ModelUnavailable, model_manager
from app.ml.preprocessor import face_extractor
from app.ml.quality import analyse_quality
from app.ml.video import sample_video
from app.models import (
    Analysis,
    EvidenceMap,
    Prediction,
    QualitySignal,
    VideoFrame,
)
from app.services.audit import add_audit, add_event
from app.services.storage import storage


logger = logging.getLogger(__name__)
inference_slots = threading.BoundedSemaphore(settings.max_concurrent_inference)


def _save_image(image: Image.Image, path: Path, format_name: str = "WEBP") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    options = {"quality": 88} if format_name == "WEBP" else {}
    image.save(path, format=format_name, **options)
    return str(path)


def _record_quality(db, analysis: Analysis, quality) -> None:
    analysis.width = quality.width
    analysis.height = quality.height
    analysis.quality_status = quality.status
    db.add(
        QualitySignal(
            analysis_id=analysis.id,
            status=quality.status,
            blur_score=quality.blur_score,
            brightness=quality.brightness,
            contrast=quality.contrast,
            face_detected=quality.face_detected,
            face_box=quality.face_box,
            warnings=quality.warnings,
            details={"resolution": f"{quality.width}x{quality.height}"},
        )
    )


def _save_evidence(db, analysis: Analysis, image: Image.Image, result, frame_id: str | None = None, prefix: str = "image") -> EvidenceMap:
    base = storage.analysis_dir(analysis.user_id, analysis.id)
    evidence = EvidenceMap(
        analysis_id=analysis.id,
        frame_id=frame_id,
        method="ATTENTION_ROLLOUT",
        available=False,
        metadata_json={
            "language": "Regions indicate model influence, not pixel-level forgery.",
            "scope": "face-manipulation detector; the synthetic-image detector does not expose this map",
        },
    )
    if result.attentions:
        try:
            mask = attention_rollout(result.attentions, image.size)
            grayscale, heatmap, overlay = render_evidence(image, mask)
            evidence.grayscale_path = _save_image(grayscale, base / f"{prefix}_attention.png", "PNG")
            evidence.heatmap_path = _save_image(heatmap, base / f"{prefix}_heatmap.webp")
            evidence.overlay_path = _save_image(overlay, base / f"{prefix}_overlay.webp")
            evidence.available = True
            evidence.metadata_json = {
                **(evidence.metadata_json or {}),
                "minimum": float(mask.min()),
                "maximum": float(mask.max()),
            }
        except Exception:
            logger.exception("Attention evidence generation failed for analysis %s", analysis.id)
    db.add(evidence)
    return evidence


def _process_image(db, analysis: Analysis, source: Path) -> None:
    add_event(db, analysis.id, "DECODING", "Image decoded successfully")
    image = Image.open(source)
    image.verify()
    image = Image.open(source).convert("RGB")
    preview = image.copy()
    preview.thumbnail((1600, 1600))
    analysis.media.preview_path = _save_image(
        preview, storage.analysis_dir(analysis.user_id, analysis.id) / "preview.webp"
    )

    analysis.status = "DETECTING_FACES"
    db.commit()
    add_event(db, analysis.id, "DETECTING_FACES", "Searching for the strongest facial region")
    face = face_extractor.extract(image)
    quality = analyse_quality(image, face.detected, face.box)
    analysis.analysis_scope = face.scope
    analysis.status = "QUALITY_CHECK"
    _record_quality(db, analysis, quality)
    db.commit()
    add_event(db, analysis.id, "QUALITY_CHECK", f"Input quality rated {quality.status}", {"warnings": quality.warnings})

    base = storage.analysis_dir(analysis.user_id, analysis.id)
    crop_path = _save_image(face.image, base / "analysed_crop.webp")
    analysis.status = "MODEL_INFERENCE"
    db.commit()
    add_event(db, analysis.id, "MODEL_INFERENCE", "Vision Transformer inference started")
    with inference_slots:
        result = run_inference(face.image, synthetic_image=image)
    analysis.model_id = settings.detector_model_id
    analysis.model_version = getattr(model_manager.model.config, "_commit_hash", None) or "configured"
    analysis.fake_probability = result.fake_probability
    analysis.real_probability = result.real_probability
    analysis.classification = result.classification
    analysis.analysed_frames = 1
    analysis.valid_frames = 1
    db.add(
        Prediction(
            analysis_id=analysis.id,
            fake_probability=result.fake_probability,
            real_probability=result.real_probability,
            classification=result.classification,
            raw_label_scores=result.raw_scores,
            calibrated=result.calibrated,
        )
    )
    db.commit()
    add_event(
        db,
        analysis.id,
        "MODEL_INFERENCE",
        "Complementary detector signals combined"
        if result.synthetic_fake_probability is not None
        else "Primary detector signal produced",
        {
            "classification": result.classification,
            "primary_fake_probability": result.primary_fake_probability,
            "synthetic_fake_probability": result.synthetic_fake_probability,
            "fusion_method": result.fusion_method,
        },
    )

    analysis.status = "GENERATING_EVIDENCE"
    db.commit()
    add_event(db, analysis.id, "GENERATING_EVIDENCE", "Building attention-rollout evidence")
    evidence = _save_evidence(db, analysis, face.image, result)
    evidence.crop_path = crop_path
    db.commit()
    add_event(
        db,
        analysis.id,
        "GENERATING_EVIDENCE",
        "Evidence map generated" if evidence.available else "The model did not expose usable attention tensors",
        {"available": evidence.available},
    )


def _process_video(db, analysis: Analysis, source: Path) -> None:
    analysis.status = "EXTRACTING_FRAMES"
    db.commit()
    add_event(db, analysis.id, "EXTRACTING_FRAMES", "Sampling representative video frames")
    samples = sample_video(source, settings.max_video_frames, analysis.mode == "detailed")
    if not samples:
        raise ValueError("No usable frames could be decoded")
    values: list[float] = []
    primary_values: list[float] = []
    synthetic_values: list[float] = []
    qualities = []
    base = storage.analysis_dir(analysis.user_id, analysis.id)
    for position, sample in enumerate(samples):
        image = Image.fromarray(sample.image).convert("RGB")
        face = face_extractor.extract(image)
        quality = analyse_quality(image, face.detected, face.box)
        qualities.append(quality)
        add_event(
            db,
            analysis.id,
            "MODEL_INFERENCE",
            f"Analysing frame {position + 1} of {len(samples)}",
            {"frame_index": sample.frame_index, "timestamp_ms": sample.timestamp_ms},
        )
        with inference_slots:
            result = run_inference(face.image, synthetic_image=image)
        values.append(result.fake_probability)
        if result.primary_fake_probability is not None:
            primary_values.append(result.primary_fake_probability)
        if result.synthetic_fake_probability is not None:
            synthetic_values.append(result.synthetic_fake_probability)
        frame_preview = _save_image(image, base / f"frame_{position:03d}.webp")
        frame = VideoFrame(
            analysis_id=analysis.id,
            frame_index=sample.frame_index,
            timestamp_ms=sample.timestamp_ms,
            width=image.width,
            height=image.height,
            face_detected=face.detected,
            face_box=face.box,
            quality_status=quality.status,
            fake_probability=result.fake_probability,
            real_probability=result.real_probability,
            classification=result.classification,
            preview_path=frame_preview,
        )
        db.add(frame)
        db.flush()
        evidence = _save_evidence(db, analysis, face.image, result, frame.id, f"frame_{position:03d}")
        frame.overlay_path = evidence.overlay_path
        frame.attention_available = evidence.available
        db.commit()

    aggregate = aggregate_probabilities(values)
    aggregate["detectors"] = {
        "fusion_method": "maximum_risk",
        "primary_frame_scores": primary_values,
        "synthetic_frame_scores": synthetic_values,
    }
    representative = qualities[0]
    representative.face_detected = any(item.face_detected for item in qualities)
    representative.warnings = sorted({warning for item in qualities for warning in item.warnings})
    representative.status = "POOR" if any(item.status == "POOR" for item in qualities) else (
        "LIMITED" if any(item.status == "LIMITED" for item in qualities) else "GOOD"
    )
    analysis.status = "AGGREGATING"
    analysis.model_id = settings.detector_model_id
    analysis.model_version = getattr(model_manager.model.config, "_commit_hash", None) or "configured"
    analysis.fake_probability = aggregate["score"]
    analysis.real_probability = 1 - aggregate["score"] if aggregate["score"] is not None else None
    analysis.classification = aggregate["classification"]
    analysis.aggregate_metadata = aggregate
    analysis.analysed_frames = len(samples)
    analysis.valid_frames = len(values)
    analysis.width = samples[0].image.shape[1]
    analysis.height = samples[0].image.shape[0]
    analysis.quality_status = representative.status
    analysis.analysis_scope = "mixed_face_and_full_frame" if any(item.face_detected for item in qualities) else "full_frame"
    analysis.media.preview_path = str(base / "frame_000.webp")
    _record_quality(db, analysis, representative)
    db.add(
        Prediction(
            analysis_id=analysis.id,
            fake_probability=aggregate["score"] or 0.0,
            real_probability=1 - (aggregate["score"] or 0.0),
            classification=aggregate["classification"],
            raw_label_scores={"frame_scores": values},
            calibrated=False,
        )
    )
    db.commit()
    add_event(db, analysis.id, "AGGREGATING", "Frame signals combined with a deterministic trimmed mean", aggregate)


def process_analysis(analysis_id: str) -> None:
    db = SessionLocal()
    analysis = db.get(Analysis, analysis_id)
    if not analysis or not analysis.media or not analysis.media.source_path:
        db.close()
        return
    source = Path(analysis.media.source_path)
    try:
        analysis.started_at = datetime.now(timezone.utc)
        analysis.status = "VALIDATING"
        db.commit()
        add_event(db, analysis.id, "VALIDATING", "Validated media queued for analysis")
        if analysis.media_type == "IMAGE":
            _process_image(db, analysis, source)
        else:
            _process_video(db, analysis, source)
        analysis.status = "COMPLETED"
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.thresholds = {
            "authentic": settings.authentic_threshold,
            "manipulated": settings.manipulated_threshold,
            "calibrated": bool(settings.calibration_artifact),
        }
        analysis.application_version = settings.app_version
        db.commit()
        add_event(db, analysis.id, "COMPLETED", "Analysis is ready for human review")
        add_audit(db, analysis.user_id, "ANALYSIS_COMPLETED", analysis.id, new={"classification": analysis.classification}, model_id=analysis.model_id)
    except ModelUnavailable:
        logger.exception("Model unavailable for analysis %s", analysis_id)
        db.rollback()
        analysis = db.get(Analysis, analysis_id)
        analysis.status = "FAILED"
        analysis.failure_reason = "Detection model unavailable. No prediction was generated."
        analysis.completed_at = datetime.now(timezone.utc)
        db.commit()
        add_event(db, analysis.id, "FAILED", analysis.failure_reason)
    except Exception:
        logger.exception("Analysis %s failed", analysis_id)
        db.rollback()
        analysis = db.get(Analysis, analysis_id)
        analysis.status = "FAILED"
        analysis.failure_reason = "The media could not be analysed. No prediction was generated."
        analysis.completed_at = datetime.now(timezone.utc)
        db.commit()
        add_event(db, analysis.id, "FAILED", analysis.failure_reason)
    finally:
        if source.exists() and analysis and analysis.media and not analysis.media.retained:
            source.unlink(missing_ok=True)
            if analysis and analysis.media:
                analysis.media.source_path = None
                analysis.media.retained = False
                db.commit()
        db.close()
