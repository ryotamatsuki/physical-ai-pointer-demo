"""YOLOX-s wrapper. Preprocessing matches OpenCV Zoo's original demo."""
import json
from pathlib import Path
import cv2
import numpy as np
from control import Detection
from third_party.opencv_yolox_reference import YoloX

ROOT = Path(__file__).resolve().parent
CLASSES = tuple(json.loads((ROOT / "coco_classes.json").read_text(encoding="utf-8")))


class Detector:
    def __init__(self, model_path, confidence=0.60):
        self.model = YoloX(str(model_path), confThreshold=confidence,
                           nmsThreshold=0.45, backendId=cv2.dnn.DNN_BACKEND_OPENCV,
                           targetId=cv2.dnn.DNN_TARGET_CPU)

    def detect(self, frame):
        h, w = frame.shape[:2]
        ratio = min(640 / h, 640 / w)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
        blob = np.full((640, 640, 3), 114, dtype=np.float32)
        blob[:new_h, :new_w] = cv2.resize(rgb, (new_w, new_h)).astype(np.float32)
        predictions = self.model.infer(blob)
        detections = []
        for x, y, bw, bh, score, cls_id in np.asarray(predictions).reshape(-1, 6):
            # Coordinates must refer to the original, unmirrored/displayed frame.
            box = np.array([x, y, x + bw, y + bh]) / ratio
            box[[0, 2]] = np.clip(box[[0, 2]], 0, w) / w
            box[[1, 3]] = np.clip(box[[1, 3]], 0, h) / h
            detections.append(Detection(CLASSES[int(cls_id)], float(score), *map(float, box)))
        return detections
