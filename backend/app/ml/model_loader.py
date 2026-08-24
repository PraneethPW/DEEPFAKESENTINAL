import logging
import threading
from pathlib import Path

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app.config import settings


logger = logging.getLogger(__name__)
FAKE_LABEL_TOKENS = (
    "fake",
    "deepfake",
    "manipulated",
    "synthetic",
    "generated",
    "artificial",
)


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
        self.synthetic_model = None
        self.synthetic_processor = None
        self.synthetic_labels: list[str] = []
        self.synthetic_model_id = settings.synthetic_model_id
        self.synthetic_error: str | None = None
        self._synthetic_load_attempted = False

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
        synthetic_ready = (
            not settings.synthetic_detector_enabled
            or self.synthetic_model is not None
            or self._synthetic_load_attempted
        )
        if self.model is not None and synthetic_ready:
            return
        with self._load_lock:
            if self.model is None:
                self._load_primary()
            if (
                settings.synthetic_detector_enabled
                and self.synthetic_model is None
                and not self._synthetic_load_attempted
            ):
                self._load_synthetic()

    @staticmethod
    def _labels(model) -> list[str]:
        labels = model.config.id2label or {}
        return [str(labels.get(i, labels.get(str(i), i))) for i in range(model.config.num_labels)]

    @staticmethod
    def _validate_labels(labels: list[str]) -> None:
        normalized = " ".join(labels).lower()
        if not any(token in normalized for token in FAKE_LABEL_TOKENS):
            raise ModelUnavailable(
                "Configured classifier labels do not identify a manipulated/generated class"
            )

    def _load_primary(self) -> None:
        try:
            source = settings.deepfake_model_checkpoint or settings.deepfake_model_id
            local_only = settings.model_local_only or bool(settings.deepfake_model_checkpoint)
            self.processor = AutoImageProcessor.from_pretrained(source, local_files_only=local_only)
            kwargs = {"local_files_only": local_only, "output_attentions": True}
            try:
                self.model = AutoModelForImageClassification.from_pretrained(
                    source, attn_implementation="eager", **kwargs
                )
            except TypeError:
                self.model = AutoModelForImageClassification.from_pretrained(source, **kwargs)
            self.model.to(self.device)
            self.model.eval()
            self.labels = self._labels(self.model)
            self._validate_labels(self.labels)
            self.error = None
            logger.info("Loaded face-manipulation detector %s on %s", source, self.device)
        except Exception as exc:
            self.model = None
            self.processor = None
            self.error = str(exc)
            logger.exception("Deepfake model could not be loaded")
            raise ModelUnavailable("Detection model unavailable") from exc

    def _load_synthetic(self) -> None:
        self._synthetic_load_attempted = True
        try:
            source = settings.synthetic_model_id
            self.synthetic_processor = AutoImageProcessor.from_pretrained(
                source, local_files_only=settings.model_local_only
            )
            self.synthetic_model = AutoModelForImageClassification.from_pretrained(
                source, local_files_only=settings.model_local_only
            )
            self.synthetic_model.to(self.device)
            self.synthetic_model.eval()
            self.synthetic_labels = self._labels(self.synthetic_model)
            self._validate_labels(self.synthetic_labels)
            self.synthetic_error = None
            logger.info("Loaded synthetic-image detector %s on %s", source, self.device)
        except Exception as exc:
            self.synthetic_model = None
            self.synthetic_processor = None
            self.synthetic_labels = []
            self.synthetic_error = str(exc)
            logger.warning(
                "Synthetic-image detector could not be loaded; primary detector remains available",
                exc_info=True,
            )

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def public_status(self) -> dict:
        ensemble_active = self.synthetic_model is not None
        return {
            "model_id": settings.detector_model_id,
            "architecture": "Vision Transformer ensemble",
            "device": self.device,
            "labels": sorted(set(self.labels + self.synthetic_labels)),
            "loaded": self.loaded,
            "calibrated": bool(settings.calibration_artifact)
            and not settings.synthetic_detector_enabled,
            "primary_calibrated": bool(settings.calibration_artifact),
            "evidence_method": "ATTENTION_ROLLOUT",
            "error": "Detection model unavailable" if self.error else None,
            "warning": (
                "Synthetic-image detector unavailable; results use only the face-manipulation detector."
                if settings.synthetic_detector_enabled and self.synthetic_error
                else None
            ),
            "ensemble_active": ensemble_active,
            "detectors": [
                {
                    "role": "face_manipulation",
                    "model_id": Path(self.model_id).name
                    if settings.deepfake_model_checkpoint
                    else self.model_id,
                    "loaded": self.loaded,
                    "labels": self.labels,
                },
                {
                    "role": "synthetic_image",
                    "model_id": self.synthetic_model_id,
                    "loaded": ensemble_active,
                    "labels": self.synthetic_labels,
                },
            ]
            if settings.synthetic_detector_enabled
            else [],
        }


model_manager = ModelManager()
