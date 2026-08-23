from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Analysis, AuditLog, HumanReview, User


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def distribution(values, labels: list[str]) -> list[dict]:
    counts = Counter(value for value in values if value)
    return [{"name": label, "value": counts.get(label, 0)} for label in labels]


@router.get("")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.scalars(
        select(Analysis).where(Analysis.user_id == user.id).order_by(desc(Analysis.created_at))
    ).all()
    reviews = db.scalars(select(HumanReview).where(HumanReview.user_id == user.id)).all()
    review_latest = {}
    for review in reviews:
        review_latest[review.analysis_id] = review.decision
    totals = {
        "total": len(analyses),
        "images": sum(item.media_type == "IMAGE" for item in analyses),
        "videos": sum(item.media_type == "VIDEO" for item in analyses),
        "likely_manipulated": sum(item.classification == "LIKELY_MANIPULATED" for item in analyses),
        "likely_authentic": sum(item.classification == "LIKELY_AUTHENTIC" for item in analyses),
        "inconclusive": sum(item.classification == "INCONCLUSIVE" for item in analyses),
        "human_reviewed": len(review_latest),
    }
    now = datetime.now(timezone.utc)
    activity = []
    for offset in range(13, -1, -1):
        day = (now - timedelta(days=offset)).date()
        activity.append({"date": day.isoformat(), "value": sum(item.created_at.date() == day for item in analyses)})
    recent_audit = db.scalars(
        select(AuditLog).where(AuditLog.user_id == user.id).order_by(desc(AuditLog.created_at)).limit(8)
    ).all()
    return {
        "totals": totals,
        "classification_distribution": distribution(
            [item.classification for item in analyses],
            ["LIKELY_AUTHENTIC", "INCONCLUSIVE", "LIKELY_MANIPULATED"],
        ),
        "media_distribution": distribution([item.media_type for item in analyses], ["IMAGE", "VIDEO"]),
        "quality_distribution": distribution([item.quality_status for item in analyses], ["GOOD", "LIMITED", "POOR"]),
        "review_distribution": distribution(review_latest.values(), ["CONFIRM_AUTHENTIC", "CONFIRM_MANIPULATED", "MARK_INCONCLUSIVE", "MARK_FOR_REVIEW"]),
        "activity": activity,
        "recent": [
            {"id": item.id, "filename": item.original_filename, "media_type": item.media_type, "status": item.status, "classification": item.classification, "fake_probability": item.fake_probability, "created_at": item.created_at}
            for item in analyses[:6]
        ],
        "audit": [
            {"id": item.id, "analysis_id": item.analysis_id, "action": item.action, "created_at": item.created_at}
            for item in recent_audit
        ],
    }

