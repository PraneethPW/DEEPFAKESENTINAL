from sqlalchemy.orm import Session

from app.models import AnalysisEvent, AuditLog


def add_event(
    db: Session,
    analysis_id: str,
    stage: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    db.add(AnalysisEvent(analysis_id=analysis_id, stage=stage, message=message, metadata_json=metadata))
    db.commit()


def add_audit(
    db: Session,
    user_id: str,
    action: str,
    analysis_id: str | None = None,
    previous: dict | None = None,
    new: dict | None = None,
    note: str | None = None,
    model_id: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            analysis_id=analysis_id,
            action=action,
            previous_value=previous,
            new_value=new,
            note=note,
            model_id=model_id,
        )
    )
    db.commit()

