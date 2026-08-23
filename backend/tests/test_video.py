import cv2
import numpy as np

from app.ml.video import inspect_video, sample_video


def make_video(path, frames: int = 12, fps: float = 6.0):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (64, 64))
    assert writer.isOpened()
    for index in range(frames):
        image = np.full((64, 64, 3), (index * 12) % 256, dtype=np.uint8)
        writer.write(image)
    writer.release()


def test_video_metadata_sampling_and_timestamp_order(tmp_path):
    path = tmp_path / "tiny.avi"
    make_video(path)
    metadata = inspect_video(path)
    samples = sample_video(path, maximum=8)
    assert metadata["duration"] == 2.0
    assert 1 <= len(samples) <= 8
    assert [item.timestamp_ms for item in samples] == sorted(item.timestamp_ms for item in samples)
    assert len({item.frame_index for item in samples}) == len(samples)


def test_detailed_mode_never_exceeds_frame_cap(tmp_path):
    path = tmp_path / "detailed.avi"
    make_video(path, frames=30, fps=5.0)
    samples = sample_video(path, maximum=10, detailed=True)
    assert len(samples) <= 10
