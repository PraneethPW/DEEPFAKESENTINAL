from pathlib import Path

import cv2

from app.ml.types import FrameSample


class VideoValidationError(ValueError):
    pass


def inspect_video(path: Path) -> dict:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise VideoValidationError("The selected video could not be decoded")
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if frames <= 0 or fps <= 0 or width <= 0 or height <= 0:
            raise VideoValidationError("Video metadata is incomplete or invalid")
        duration = frames / fps
        return {"frames": frames, "fps": fps, "width": width, "height": height, "duration": duration}
    finally:
        capture.release()


def sample_video(path: Path, maximum: int, detailed: bool = False) -> list[FrameSample]:
    metadata = inspect_video(path)
    target = min(maximum, max(8, int(metadata["duration"] * (0.5 if detailed else 0.3))))
    target = min(target, metadata["frames"])
    if target <= 0:
        return []
    indices = sorted(set(int(round(i)) for i in __import__("numpy").linspace(0, metadata["frames"] - 1, target)))
    capture = cv2.VideoCapture(str(path))
    samples: list[FrameSample] = []
    try:
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, bgr = capture.read()
            if ok and bgr is not None:
                samples.append(FrameSample(index, int(index / metadata["fps"] * 1000), cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
    finally:
        capture.release()
    return samples

