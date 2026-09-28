import argparse
import time

import cv2


def scan():
    for index in range(10):
        print(f"Testing camera index {index}...")
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

        if not cap.isOpened():
            print("  cannot open")
            cap.release()
            continue

        ok, frame = cap.read()
        if ok:
            h, w = frame.shape[:2]
            print(f"  SUCCESS {w}x{h}")
        else:
            print("  opened but frame read failed")

        cap.release()


def endurance(index, duration):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {index}")

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    started = time.monotonic()
    frames = 0
    failures = 0
    first_shape = None

    try:
        while time.monotonic() - started < duration:
            ok, frame = cap.read()

            if not ok:
                failures += 1
                continue

            frames += 1
            if first_shape is None:
                first_shape = frame.shape

            cv2.imshow(
                f"Camera endurance index={index} - q to stop",
                frame,
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        elapsed = time.monotonic() - started
        cap.release()
        cv2.destroyAllWindows()

    fps = frames / elapsed if elapsed > 0 else 0.0
    resolution = (
        f"{first_shape[1]}x{first_shape[0]}"
        if first_shape is not None
        else "unknown"
    )

    print(f"elapsed_s={elapsed:.1f}")
    print(f"frames={frames}")
    print(f"read_failures={failures}")
    print(f"average_fps={fps:.2f}")
    print(f"resolution={resolution}")

    if frames > 0 and failures == 0:
        print("PASS: continuous capture completed with zero read failures")
    else:
        print("CHECK: capture had failures or no frames")


parser = argparse.ArgumentParser()
parser.add_argument("--index", type=int)
parser.add_argument("--duration", type=float, default=300.0)
args = parser.parse_args()

if args.index is None:
    scan()
else:
    endurance(args.index, args.duration)
