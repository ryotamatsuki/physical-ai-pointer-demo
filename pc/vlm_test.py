import os
import tempfile

import cv2
from gradio_client import Client, handle_file

import config


def parse_answer(text):
    upper = str(text).strip().upper()
    for token in ("RED", "BLUE", "GREEN", "NONE"):
        if upper == token:
            return token
    for token in ("RED", "BLUE", "GREEN", "NONE"):
        if token in upper:
            return token
    return "NONE"


if "REPLACE-ME" in config.COLAB_GRADIO_URL:
    raise RuntimeError(
        "pc/config.py の COLAB_GRADIO_URL を、Colabが表示した gradio.live URL に変更してください。"
    )

cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
ok, frame = cap.read()
cap.release()

if not ok:
    raise RuntimeError("Camera capture failed")

instruction = input("指示を入力してください: ").strip()

with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
    image_path = tmp.name

cv2.imwrite(image_path, frame)

try:
    client = Client(config.COLAB_GRADIO_URL)
    raw = client.predict(
        handle_file(image_path),
        instruction,
        api_name="/classify",
    )
    print("RAW:", raw)
    print("TARGET:", parse_answer(raw))
finally:
    try:
        os.remove(image_path)
    except OSError:
        pass
