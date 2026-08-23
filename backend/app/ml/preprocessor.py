from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class FaceCrop:
    image: Image.Image
    detected: bool
    box: dict[str, int] | None
    scope: str


class FaceExtractor:
    def __init__(self, padding: float = 0.2) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)
        self.padding = padding

    def extract(self, image: Image.Image) -> FaceCrop:
        rgb = np.asarray(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
        if len(faces) == 0:
            return FaceCrop(image.convert("RGB"), False, None, "full_frame")
        x, y, width, height = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        pad_x, pad_y = int(width * self.padding), int(height * self.padding)
        left, top = max(0, x - pad_x), max(0, y - pad_y)
        right, bottom = min(rgb.shape[1], x + width + pad_x), min(rgb.shape[0], y + height + pad_y)
        box = {"x": int(left), "y": int(top), "width": int(right - left), "height": int(bottom - top)}
        return FaceCrop(image.crop((left, top, right, bottom)).convert("RGB"), True, box, "face_crop")


face_extractor = FaceExtractor()

