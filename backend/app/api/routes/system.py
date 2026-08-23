from fastapi import APIRouter

from app.config import settings
from app.ml.model_loader import model_manager


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/model")
def model_status(load: bool = False):
    if load and not model_manager.loaded:
        try:
            model_manager.load()
        except Exception:
            pass
    status = model_manager.public_status()
    return {
        **status,
        "thresholds": {
            "authentic": settings.authentic_threshold,
            "manipulated": settings.manipulated_threshold,
        },
    }

