import argparse

import cv2

import config
from modal_client import ModalVLMError, classify_frame


def load_frame(image_path: str | None):
    if image_path:
        frame = cv2.imread(image_path)
        if frame is None:
            raise RuntimeError(f"Cannot read image: {image_path}")
        return frame

    cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    ok, frame = cap.read()
    cap.release()

    if not ok:
        raise RuntimeError("Camera capture failed")

    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image",
        help="Static image path. Use this for PRE-001 before EOS RP setup.",
    )
    parser.add_argument(
        "--instruction",
        default=None,
        help="Natural-language instruction.",
    )
    args = parser.parse_args()

    frame = load_frame(args.image)
    instruction = args.instruction or input("指示を入力してください: ").strip()

    try:
        result = classify_frame(frame, instruction)
    except ModalVLMError as exc:
        print("FAIL:", exc)
        raise SystemExit(1)

    print("TARGET:", result["target"])
    print("MODEL:", result.get("model"))
    print("INFERENCE_MS:", result.get("inference_ms"))


if __name__ == "__main__":
    main()
