import os

import pytest
from PIL import Image

from app.ml.inference import run_inference


@pytest.mark.skipif(os.getenv("RUN_MODEL_INTEGRATION") != "1", reason="set RUN_MODEL_INTEGRATION=1 to download and run the configured detector")
def test_real_configured_model_inference():
    result = run_inference(Image.new("RGB", (224, 224), "gray"))
    assert 0 <= result.fake_probability <= 1
    assert result.classification in {"LIKELY_AUTHENTIC", "INCONCLUSIVE", "LIKELY_MANIPULATED"}

