import logging
import threading
from pathlib import Path

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app.config import settings


logger = logging.getLogger(__name__)


class ModelUnavailable(RuntimeError):
    pass


class ModelManager:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._load_lock = threading.Lock()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.model = None
        self.processor = None
        self.device = self._select_device()
        self.error: str | None = None
        self.labels: list[str] = []
        self.model_id = settings.deepfake_model_checkpoint or settings.deepfake_model_id

    @staticmethod
    def _select_device() -> str:
        requested = settings.model_device.lower()
        if requested != "auto":
            if requested == "cuda" and not torch.cuda.is_available():
                return "cpu"
            if requested == "mps" and not (
                hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
            ):
                return "cpu"
            return requested
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def load(self) -> None:
        if self.model is not None:
            return
        with self._load_lock:
            if self.model is not None:
                return
            try:
                source = settings.deepfake_model_checkpoint or settings.deepfake_model_id
                local_only = settings.model_local_only or bool(settings.deepfake_model_checkpoint)
                self.processor = AutoImageProcessor.from_pretrained(
                    source, local_files_only=local_only
                )
                kwargs = {
                    "local_files_only": local_only,
                    "output_attentions": True,
                }
                try:
                    self.model = AutoModelForImageClassification.from_pretrained(
                        source, attn_implementation="eager", **kwargs
                    )
                except TypeError:
                    self.model = AutoModelForImageClassification.from_pretrained(source, **kwargs)
                self.model.to(self.device)
                self.model.eval()
                labels = self.model.config.id2label or {}
                self.labels = [str(labels.get(i, i)) for i in range(self.model.config.num_labels)]
                normalized = " ".join(self.labels).lower()
                if not any(token in normalized for token in ("fake", "deepfake", "manipulated")):
                    raise ModelUnavailable(
                        "Configured classifier labels do not identify a manipulated/fake class"
                    )
                self.error = None
                logger.info("Loaded detector %s on %s", source, self.device)
            except Exception as exc:
                self.model = None
                self.processor = None
                self.error = str(exc)
                logger.exception("Deepfake model could not be loaded")
                raise ModelUnavailable("Detection model unavailable") from exc

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def public_status(self) -> dict:
        return {
            "model_id": Path(self.model_id).name if settings.deepfake_model_checkpoint else self.model_id,
            "architecture": "Vision Transformer",
            "device": self.device,
            "labels": self.labels,
            "loaded": self.loaded,
            "calibrated": bool(settings.calibration_artifact),
            "evidence_method": "ATTENTION_ROLLOUT",
            "error": "Detection model unavailable" if self.error else None,
        }


model_manager = ModelManager()

