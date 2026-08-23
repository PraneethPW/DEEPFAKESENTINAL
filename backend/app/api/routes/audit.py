from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import AuditLog, User


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(AuditLog).where(AuditLog.user_id == user.id).order_by(desc(AuditLog.created_at)).limit(500)
    ).all()
    return [
        {
            "id": item.id,
            "analysis_id": item.analysis_id,
            "action": item.action,
            "previous_value": item.previous_value,
            "new_value": item.new_value,
            "note": item.note,
            "model_id": item.model_id,
            "created_at": item.created_at,
        }
        for item in items
    ]

