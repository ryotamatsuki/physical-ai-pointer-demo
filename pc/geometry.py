from __future__ import annotations

import math

import config
from vision import roi_bounds


class GeometryError(RuntimeError):
    pass


def _require_calibration():
    required = {
        "CALIBRATION_FRAME_WIDTH": config.CALIBRATION_FRAME_WIDTH,
        "CALIBRATION_FRAME_HEIGHT": config.CALIBRATION_FRAME_HEIGHT,
        "PIVOT_X": config.PIVOT_X,
        "PIVOT_Y": config.PIVOT_Y,
    }

    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise GeometryError(
            "Calibration not configured: " + ", ".join(missing)
        )


def image_point_to_servo_angle(x, y, frame_shape):
    _require_calibration()

    height, width = frame_shape[:2]
    if (
        width != config.CALIBRATION_FRAME_WIDTH
        or height != config.CALIBRATION_FRAME_HEIGHT
    ):
        raise GeometryError(
            "Capture resolution differs from calibration: "
            f"got {width}x{height}, expected "
            f"{config.CALIBRATION_FRAME_WIDTH}x"
            f"{config.CALIBRATION_FRAME_HEIGHT}"
        )

    x0, y0, x1, y1 = roi_bounds_from_shape(frame_shape)
    if not (x0 <= x < x1 and y0 <= y < y1):
        raise GeometryError("Target center is outside calibrated ROI")

    dx = float(x) - float(config.PIVOT_X)
    dy = float(config.PIVOT_Y) - float(y)
    radius = math.hypot(dx, dy)

    if not math.isfinite(radius) or radius < config.MIN_TARGET_RADIUS_PX:
        raise GeometryError(
            f"Target too close to pivot or invalid: radius={radius}"
        )

    vision_angle = math.degrees(math.atan2(dx, dy))
    angle = (
        config.SERVO_CENTER
        + config.ANGLE_SIGN * vision_angle * config.ANGLE_SCALE
        + config.ANGLE_OFFSET
    )

    if not math.isfinite(angle):
        raise GeometryError("Calculated servo angle is not finite")

    if not (config.SERVO_MIN <= angle <= config.SERVO_MAX):
        raise GeometryError(
            f"Target requires unreachable angle {angle:.2f}°; "
            f"safe range is {config.SERVO_MIN:.2f}–"
            f"{config.SERVO_MAX:.2f}°"
        )

    return angle


def roi_bounds_from_shape(frame_shape):
    height, width = frame_shape[:2]
    return (
        int(round(width * config.ROI_LEFT)),
        int(round(height * config.ROI_TOP)),
        int(round(width * config.ROI_RIGHT)),
        int(round(height * config.ROI_BOTTOM)),
    )
