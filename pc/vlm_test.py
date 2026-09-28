import argparse

import cv2

import config
from camera_stream import CameraError, LatestFrameCamera
from modal_client import ModalVLMError, classify_frame


def load_static_image(image_path):
    frame = cv2.imread(image_path)
    if frame is None:
        raise RuntimeError(f"Cannot read image: {image_path}")
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image",
        help="Static image path. Use this for PRE-001/PRE-002.",
    )
    parser.add_argument(
        "--instruction",
        default=None,
        help="Natural-language instruction.",
    )
    parser.add_argument(
        "--cold-start",
        action="store_true",
        help="Use the longer cold-start timeout.",
    )
    args = parser.parse_args()

    instruction = args.instruction or input(
        "指示を入力してください: "
    ).strip()

    if args.image:
        frame = load_static_image(args.image)
    else:
        # Capture continuously while the user is typing. Freeze only after the
        # instruction has been finalized, so the frame is current.
        try:
            with LatestFrameCamera() as camera:
                snapshot = camera.snapshot()
                frame = snapshot.frame
                print(
                    "CAPTURED_UNIX:",
                    f"{snapshot.captured_wall_time:.3f}",
                )
        except CameraError as exc:
            print("FAIL:", exc)
            raise SystemExit(1)

    timeout = (
        config.MODAL_COLD_START_TIMEOUT_SECONDS
        if args.cold_start
        else config.MODAL_REQUEST_TIMEOUT_SECONDS
    )

    try:
        result = classify_frame(
            frame,
            instruction,
            timeout_seconds=timeout,
        )
    except ModalVLMError as exc:
        print("FAIL:", exc)
        raise SystemExit(1)

    print("TARGET:", result["target"])
    print("RAW_OUTPUT:", result.get("raw_output"))
    print("MODEL:", result.get("model"))
    print("MODEL_REVISION:", result.get("model_revision"))
    print("INFERENCE_MS:", result.get("inference_ms"))
    print("ROUND_TRIP_MS:", result.get("round_trip_ms"))


if __name__ == "__main__":
    main()
