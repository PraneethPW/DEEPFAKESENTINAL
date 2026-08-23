import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from app.config import settings
from app.ml.model_loader import ModelManager, model_manager
from app.ml.types import InferenceResult


def classify(fake_probability: float) -> str:
    if fake_probability <= settings.authentic_threshold:
        return "LIKELY_AUTHENTIC"
    if fake_probability >= settings.manipulated_threshold:
        return "LIKELY_MANIPULATED"
    return "INCONCLUSIVE"


def _fake_index(labels: list[str]) -> int:
    candidates = ("fake", "deepfake", "manipulated", "synthetic")
    for index, label in enumerate(labels):
        if any(token in label.lower() for token in candidates):
            return index
    raise ValueError("configured labels do not contain a fake/manipulated class")


def _apply_calibration(value: float) -> tuple[float, bool]:
    if not settings.calibration_artifact:
        return value, False
    path = Path(settings.calibration_artifact)
    if not path.exists():
        return value, False
    artifact = json.loads(path.read_text(encoding="utf-8"))
    temperature = float(artifact.get("temperature", 1.0))
    if temperature <= 0:
        return value, False
    epsilon = 1e-7
    logit = np.log(np.clip(value, epsilon, 1 - epsilon) / np.clip(1 - value, epsilon, 1 - epsilon))
    calibrated = float(1 / (1 + np.exp(-(logit / temperature))))
    return calibrated, True


def run_inference(image: Image.Image, manager: ModelManager = model_manager) -> InferenceResult:
    manager.load()
    inputs = manager.processor(images=image.convert("RGB"), return_tensors="pt")
    inputs = {key: value.to(manager.device) for key, value in inputs.items()}
    with torch.inference_mode():
        output = manager.model(**inputs, output_attentions=True, return_dict=True)
    probabilities = torch.softmax(output.logits.float(), dim=-1)[0].cpu().numpy()
    labels = manager.labels
    fake_idx = _fake_index(labels)
    fake, calibrated = _apply_calibration(float(probabilities[fake_idx]))
    if len(probabilities) == 2:
        real = 1.0 - fake
    else:
        real_indices = [i for i, label in enumerate(labels) if "real" in label.lower() or "authentic" in label.lower()]
        if not real_indices:
            raise ValueError("multi-class model does not identify a real/authentic class")
        real = float(sum(probabilities[i] for i in real_indices))
        total = fake + real
        fake, real = fake / total, real / total
    return InferenceResult(
        fake_probability=fake,
        real_probability=real,
        classification=classify(fake),
        raw_scores={labels[i]: float(value) for i, value in enumerate(probabilities)},
        attentions=output.attentions,
        calibrated=calibrated,
    )

