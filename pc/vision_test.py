import cv2

import config
from vision import find_card_candidates, roi_bounds


cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    raise RuntimeError(
        f"Cannot open camera index {config.CAMERA_INDEX}"
    )

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        display = frame.copy()
        x0, y0, x1, y1 = roi_bounds(frame)
        cv2.rectangle(display, (x0, y0), (x1, y1), (255, 255, 255), 2)

        for color in ("RED", "BLUE", "GREEN"):
            candidates = find_card_candidates(frame, color)

            for index, item in enumerate(candidates, start=1):
                x, y, w, h = item.bbox
                cv2.rectangle(
                    display,
                    (x, y),
                    (x + w, y + h),
                    (255, 255, 255),
                    2,
                )
                cv2.circle(
                    display,
                    item.center,
                    8,
                    (255, 255, 255),
                    2,
                )
                cv2.putText(
                    display,
                    f"{color}#{index}",
                    (x, max(20, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                )

            if len(candidates) != 1:
                cv2.putText(
                    display,
                    f"{color}: {len(candidates)} valid candidates",
                    (20, 30 + 28 * ("RED", "BLUE", "GREEN").index(color)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                )

        cv2.imshow("Vision Test - q to quit", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
