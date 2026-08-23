from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dependencies import get_current_user, owned_analysis
from app.models import AIExplanation, User
from app.schemas import AskRequest, ExplainRequest
from app.services.audit import add_audit
from app.services.explanations import explain


router = APIRouter(prefix="/ai", tags=["forensic intelligence"])


def _run(payload: ExplainRequest | AskRequest, user: User, db: Session, question: str | None = None):
    analysis = owned_analysis(db, payload.analysis_id, user.id)
    result, provider = explain(analysis, question)
    item = AIExplanation(
        analysis_id=analysis.id,
        provider=provider,
        model=settings.openrouter_model if provider == "openrouter" else "deterministic-fallback",
        kind="ANSWER" if question else "SUMMARY",
        content=result.model_dump(),
    )
    db.add(item)
    db.commit()
    add_audit(db, user.id, "AI_EXPLANATION_GENERATED", analysis.id, new={"provider": provider})
    return {**result.model_dump(), "provider": provider}


@router.post("/explain")
def explain_result(payload: ExplainRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(payload, user, db)


@router.post("/summarize")
def summarize(payload: ExplainRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(payload, user, db)


@router.post("/ask")
def ask(payload: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _run(payload, user, db, payload.question)

