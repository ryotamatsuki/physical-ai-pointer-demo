import cv2
import numpy as np
import config

def find_color(frame, color):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    if color == "RED":
        mask1 = cv2.inRange(hsv, np.array(config.HSV_RED_1_LOW), np.array(config.HSV_RED_1_HIGH))
        mask2 = cv2.inRange(hsv, np.array(config.HSV_RED_2_LOW), np.array(config.HSV_RED_2_HIGH))
        mask = mask1 | mask2
    elif color == "BLUE":
        mask = cv2.inRange(hsv, np.array(config.HSV_BLUE_LOW), np.array(config.HSV_BLUE_HIGH))
    elif color == "GREEN":
        mask = cv2.inRange(hsv, np.array(config.HSV_GREEN_LOW), np.array(config.HSV_GREEN_HIGH))
    else:
        return None

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < config.MIN_CONTOUR_AREA:
        return None

    m = cv2.moments(contour)
    if m["m00"] == 0:
        return None
    return int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])

cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    raise RuntimeError(f"Cannot open camera index {config.CAMERA_INDEX}")

while True:
    ok, frame = cap.read()
    if not ok:
        continue

    for color in ("RED", "BLUE", "GREEN"):
        point = find_color(frame, color)
        if point:
            cv2.circle(frame, point, 10, (255, 255, 255), 2)
            cv2.putText(frame, color, point, cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow("Vision Test - q to quit", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
