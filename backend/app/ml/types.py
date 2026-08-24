from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class QualityResult:
    status: str
    width: int
    height: int
    blur_score: float
    brightness: float
    contrast: float
    face_detected: bool = False
    face_box: dict[str, int] | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class InferenceResult:
    fake_probability: float
    real_probability: float
    classification: str
    raw_scores: dict[str, float]
    attentions: tuple[Any, ...] | None = None
    calibrated: bool = False
    primary_fake_probability: float | None = None
    synthetic_fake_probability: float | None = None
    fusion_method: str = "primary_only"


@dataclass
class FrameSample:
    frame_index: int
    timestamp_ms: int
    image: np.ndarray
