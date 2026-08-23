import cv2
import numpy as np
from PIL import Image

from app.ml.types import QualityResult


def analyse_quality(image: Image.Image, face_detected: bool = False, face_box: dict | None = None) -> QualityResult:
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    warnings: list[str] = []
    if min(width, height) < 224:
        warnings.append("Resolution is below the model's nominal input size.")
    if blur < 45:
        warnings.append("The media appears blurred; fine visual evidence may be limited.")
    if brightness < 35 or brightness > 225:
        warnings.append("Extreme brightness may reduce detector reliability.")
    if contrast < 20:
        warnings.append("Low contrast may reduce visible evidence.")
    if not face_detected:
        warnings.append("No face was detected; inference uses the full frame.")
    status = "GOOD" if not warnings else "LIMITED"
    if min(width, height) < 96 or blur < 12:
        status = "POOR"
    return QualityResult(status, width, height, blur, brightness, contrast, face_detected, face_box, warnings)

