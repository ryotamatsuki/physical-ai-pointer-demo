from __future__ import annotations

from dataclasses import dataclass
import threading
import time

import cv2

import config


class CameraError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrameSnapshot:
    frame: object
    captured_monotonic: float
    captured_wall_time: float


class LatestFrameCamera:
    """Continuously drains the capture queue and retains only the newest frame."""

    def __init__(self, index=None):
        self.index = config.CAMERA_INDEX if index is None else index
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            raise CameraError(f"Cannot open camera index {self.index}")

        # Best-effort controls; some DirectShow drivers ignore them.
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if config.CAMERA_WIDTH:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        if config.CAMERA_HEIGHT:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        self._lock = threading.Lock()
        self._latest = None
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="latest-frame-camera",
            daemon=True,
        )
        self._thread.start()

    def _capture_loop(self):
        while self._running:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.02)
                continue

            snapshot = FrameSnapshot(
                frame=frame,
                captured_monotonic=time.monotonic(),
                captured_wall_time=time.time(),
            )
            with self._lock:
                self._latest = snapshot

    def wait_until_ready(self, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._latest is not None:
                    return
            time.sleep(0.02)
        raise CameraError("Camera did not produce a frame in time")

    def snapshot(self, max_age_seconds=None):
        if max_age_seconds is None:
            max_age_seconds = config.MAX_FRAME_AGE_SECONDS

        with self._lock:
            snapshot = self._latest

        if snapshot is None:
            raise CameraError("No camera frame available")

        age = time.monotonic() - snapshot.captured_monotonic
        if age > max_age_seconds:
            raise CameraError(
                f"Latest frame is stale: {age:.3f}s > {max_age_seconds:.3f}s"
            )

        return FrameSnapshot(
            frame=snapshot.frame.copy(),
            captured_monotonic=snapshot.captured_monotonic,
            captured_wall_time=snapshot.captured_wall_time,
        )

    def close(self):
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.cap.release()

    def __enter__(self):
        self.wait_until_ready()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
