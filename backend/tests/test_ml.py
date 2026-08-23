import numpy as np
import torch
from PIL import Image

from app.ml.aggregation import aggregate_probabilities
from app.ml.attention import attention_rollout
from app.ml.inference import classify
from app.ml.quality import analyse_quality


def test_threshold_classification():
    assert classify(0.2) == "LIKELY_AUTHENTIC"
    assert classify(0.5) == "INCONCLUSIVE"
    assert classify(0.8) == "LIKELY_MANIPULATED"


def test_quality_is_calculated_from_pixels():
    image = Image.fromarray(np.full((320, 480, 3), 128, dtype=np.uint8))
    result = analyse_quality(image)
    assert result.width == 480 and result.height == 320
    assert 127 <= result.brightness <= 129
    assert result.status in {"LIMITED", "POOR"}


def test_attention_rollout_uses_model_tensors():
    attention = torch.eye(197).repeat(1, 2, 1, 1)
    attention[:, :, 0, 1:] = torch.linspace(0, 1, 196)
    mask = attention_rollout((attention, attention), (224, 224))
    assert mask.shape == (224, 224)
    assert 0 <= mask.min() <= mask.max() <= 1


def test_video_aggregation_is_deterministic():
    result = aggregate_probabilities([0.1, 0.2, 0.3, 0.4])
    assert result["score"] == 0.25
    assert result["classification"] == "LIKELY_AUTHENTIC"
    assert aggregate_probabilities([0.9, 0.8])["classification"] == "INCONCLUSIVE"

