from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np

import config


class VisionError(RuntimeError):
    pass


@dataclass(frozen=True)
class CardDetection:
    color: str
    center: tuple[int, int]
    area: float
    bbox: tuple[int, int, int, int]
    extent: float
    aspect_ratio: float


def roi_bounds(frame):
    height, width = frame.shape[:2]
    x0 = int(round(width * config.ROI_LEFT))
    y0 = int(round(height * config.ROI_TOP))
    x1 = int(round(width * config.ROI_RIGHT))
    y1 = int(round(height * config.ROI_BOTTOM))

    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise VisionError("Invalid ROI configuration")

    return x0, y0, x1, y1


def _mask_for_color(hsv, color):
    if color == "RED":
        mask1 = cv2.inRange(
            hsv,
            np.array(config.HSV_RED_1_LOW),
            np.array(config.HSV_RED_1_HIGH),
        )
        mask2 = cv2.inRange(
            hsv,
            np.array(config.HSV_RED_2_LOW),
            np.array(config.HSV_RED_2_HIGH),
        )
        mask = mask1 | mask2
    elif color == "BLUE":
        mask = cv2.inRange(
            hsv,
            np.array(config.HSV_BLUE_LOW),
            np.array(config.HSV_BLUE_HIGH),
        )
    elif color == "GREEN":
        mask = cv2.inRange(
            hsv,
            np.array(config.HSV_GREEN_LOW),
            np.array(config.HSV_GREEN_HIGH),
        )
    else:
        raise VisionError(f"Unsupported color: {color}")

    k = max(1, int(config.MORPH_KERNEL_SIZE))
    kernel = np.ones((k, k), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def find_card_candidates(frame, color):
    x0, y0, x1, y1 = roi_bounds(frame)
    roi = frame[y0:y1, x0:x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = _mask_for_color(hsv, color)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    roi_area = float((x1 - x0) * (y1 - y0))
    candidates = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        area_fraction = area / roi_area if roi_area else 0.0

        if not (
            config.MIN_CARD_AREA_FRACTION
            <= area_fraction
            <= config.MAX_CARD_AREA_FRACTION
        ):
            continue

        bx, by, bw, bh = cv2.boundingRect(contour)
        if bw <= 0 or bh <= 0:
            continue

        aspect_ratio = bw / float(bh)
        extent = area / float(bw * bh)

        if not (
            config.MIN_CARD_ASPECT_RATIO
            <= aspect_ratio
            <= config.MAX_CARD_ASPECT_RATIO
        ):
            continue

        if extent < config.MIN_CARD_EXTENT:
            continue

        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue

        cx = int(moments["m10"] / moments["m00"]) + x0
        cy = int(moments["m01"] / moments["m00"]) + y0

        candidates.append(
            CardDetection(
                color=color,
                center=(cx, cy),
                area=area,
                bbox=(bx + x0, by + y0, bw, bh),
                extent=extent,
                aspect_ratio=aspect_ratio,
            )
        )

    candidates.sort(key=lambda item: item.area, reverse=True)
    return candidates


def detect_unique_card(frame, color):
    candidates = find_card_candidates(frame, color)

    if len(candidates) == 0:
        raise VisionError(f"No valid {color} card in ROI")

    if len(candidates) > 1:
        raise VisionError(
            f"Multiple valid {color} candidates in ROI: {len(candidates)}"
        )

    return candidates[0]


def detect_layout(frame):
    return {
        color: detect_unique_card(frame, color)
        for color in ("RED", "BLUE", "GREEN")
    }


def left_to_right_order(layout):
    return tuple(
        item.color
        for item in sorted(
            layout.values(),
            key=lambda item: item.center[0],
        )
    )


def layouts_consistent(before, after, frame_shape):
    if set(before) != set(after):
        return False, "card set changed"

    if left_to_right_order(before) != left_to_right_order(after):
        return False, "left-to-right order changed"

    height, width = frame_shape[:2]
    diagonal = math.hypot(width, height)
    max_shift = diagonal * config.MAX_LAYOUT_SHIFT_FRACTION

    for color in before:
        bx, by = before[color].center
        ax, ay = after[color].center
        displacement = math.hypot(ax - bx, ay - by)

        if displacement > max_shift:
            return False, (
                f"{color} moved {displacement:.1f}px "
                f"(limit {max_shift:.1f}px)"
            )

        old_area = before[color].area
        new_area = after[color].area
        if old_area <= 0:
            return False, f"{color} invalid previous area"

        area_change = abs(new_area - old_area) / old_area
        if area_change > config.MAX_CARD_AREA_CHANGE_FRACTION:
            return False, (
                f"{color} area changed {area_change:.1%} "
                f"(limit {config.MAX_CARD_AREA_CHANGE_FRACTION:.1%})"
            )

    return True, "ok"
