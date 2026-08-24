import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from app.config import settings
from app.ml.model_loader import FAKE_LABEL_TOKENS, ModelManager, model_manager
from app.ml.types import InferenceResult


def classify(fake_probability: float) -> str:
    if fake_probability <= settings.authentic_threshold:
        return "LIKELY_AUTHENTIC"
    if fake_probability >= settings.manipulated_threshold:
        return "LIKELY_MANIPULATED"
    return "INCONCLUSIVE"


def _fake_index(labels: list[str]) -> int:
    for index, label in enumerate(labels):
        if any(token in label.lower() for token in FAKE_LABEL_TOKENS):
            return index
    raise ValueError("configured labels do not contain a fake/manipulated/generated class")


def fuse_detector_scores(primary: float, synthetic: float | None) -> float:
    """Preserve a strong warning from either complementary detector.

    The scores are not assumed to be statistically independent or calibrated, so
    they are not averaged or combined with a probabilistic noisy-OR formula.
    """
    values = [float(np.clip(primary, 0, 1))]
    if synthetic is not None:
        values.append(float(np.clip(synthetic, 0, 1)))
    return max(values)


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


def _run_detector(image: Image.Image, processor, model, device: str, attentions: bool = False):
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        output = model(
            **inputs,
            output_attentions=attentions,
            return_dict=True,
        )
    probabilities = torch.softmax(output.logits.float(), dim=-1)[0].cpu().numpy()
    return output, probabilities


def _binary_score(probabilities: np.ndarray, labels: list[str]) -> tuple[float, float]:
    fake_idx = _fake_index(labels)
    fake = float(probabilities[fake_idx])
    if len(probabilities) == 2:
        return fake, 1.0 - fake
    real_indices = [
        i
        for i, label in enumerate(labels)
        if "real" in label.lower() or "authentic" in label.lower() or "human" in label.lower()
    ]
    if not real_indices:
        raise ValueError("multi-class model does not identify a real/authentic class")
    real = float(sum(probabilities[i] for i in real_indices))
    total = fake + real
    return fake / total, real / total


def run_inference(
    image: Image.Image,
    manager: ModelManager = model_manager,
    synthetic_image: Image.Image | None = None,
) -> InferenceResult:
    manager.load()
    output, probabilities = _run_detector(
        image, manager.processor, manager.model, manager.device, attentions=True
    )
    labels = manager.labels
    primary_fake, _ = _binary_score(probabilities, labels)
    primary_fake, primary_calibrated = _apply_calibration(primary_fake)

    synthetic_probabilities = None
    synthetic_fake = None
    if manager.synthetic_model is not None and manager.synthetic_processor is not None:
        _, synthetic_probabilities = _run_detector(
            synthetic_image if synthetic_image is not None else image,
            manager.synthetic_processor,
            manager.synthetic_model,
            manager.device,
        )
        synthetic_fake, _ = _binary_score(synthetic_probabilities, manager.synthetic_labels)

    fake = fuse_detector_scores(primary_fake, synthetic_fake)
    real = 1.0 - fake
    raw_scores = {f"primary:{labels[i]}": float(value) for i, value in enumerate(probabilities)}
    raw_scores["detector:primary_fake"] = primary_fake
    if synthetic_probabilities is not None:
        raw_scores.update(
            {
                f"synthetic:{manager.synthetic_labels[i]}": float(value)
                for i, value in enumerate(synthetic_probabilities)
            }
        )
        raw_scores["detector:synthetic_fake"] = synthetic_fake
    raw_scores["ensemble:fake"] = fake
    return InferenceResult(
        fake_probability=fake,
        real_probability=real,
        classification=classify(fake),
        raw_scores=raw_scores,
        attentions=output.attentions,
        calibrated=primary_calibrated and synthetic_fake is None,
        primary_fake_probability=primary_fake,
        synthetic_fake_probability=synthetic_fake,
        fusion_method="maximum_risk" if synthetic_fake is not None else "primary_only",
    )
