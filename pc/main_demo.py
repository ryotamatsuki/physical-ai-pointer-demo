import math
import time

import cv2
import numpy as np
import serial

import config
from modal_client import ModalVLMError, classify_frame


def find_color(frame, color):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

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
        return None

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)

    if cv2.contourArea(contour) < config.MIN_CONTOUR_AREA:
        return None

    moments = cv2.moments(contour)

    if moments["m00"] == 0:
        return None

    return (
        int(moments["m10"] / moments["m00"]),
        int(moments["m01"] / moments["m00"]),
    )


def image_point_to_servo_angle(x, y):
    dx = x - config.PIVOT_X
    dy = config.PIVOT_Y - y

    vision_angle = math.degrees(math.atan2(dx, dy))

    angle = (
        config.SERVO_CENTER
        + config.ANGLE_SIGN * vision_angle * config.ANGLE_SCALE
        + config.ANGLE_OFFSET
    )

    return max(
        config.SERVO_MIN,
        min(config.SERVO_MAX, angle),
    )


def send_angle(ser, angle):
    command = f"ANGLE {angle:.2f}\n"
    ser.write(command.encode("utf-8"))
    return ser.readline().decode("utf-8", errors="ignore").strip()


def main():
    cap = cv2.VideoCapture(
        config.CAMERA_INDEX,
        cv2.CAP_DSHOW,
    )

    if not cap.isOpened():
        raise RuntimeError(
            f"Cannot open camera index {config.CAMERA_INDEX}"
        )

    try:
        with serial.Serial(
            config.SERIAL_PORT,
            config.SERIAL_BAUD,
            timeout=2,
        ) as ser:
            time.sleep(2)
            ser.reset_input_buffer()

            while True:
                instruction = input("\n指示（qで終了）: ").strip()

                if instruction.lower() == "q":
                    break

                ok, frame = cap.read()

                if not ok:
                    print("STOP: Camera capture failed")
                    continue

                # Fail closed:
                # no successful/valid Modal response => no servo command.
                try:
                    vlm_result = classify_frame(
                        frame,
                        instruction,
                    )
                except ModalVLMError as exc:
                    print("STOP: VLM unavailable:", exc)
                    continue

                target = vlm_result["target"]
                print("VLM target:", target)

                if target == "NONE":
                    print("STOP: VLM selected NONE")
                    continue

                point = find_color(frame, target)

                if point is None:
                    print(
                        f"STOP: OpenCV cannot find {target}"
                    )
                    continue

                angle = image_point_to_servo_angle(*point)

                print("Target center:", point)
                print("Servo angle:", round(angle, 2))
                print("Pico:", send_angle(ser, angle))

    finally:
        cap.release()


if __name__ == "__main__":
    main()
