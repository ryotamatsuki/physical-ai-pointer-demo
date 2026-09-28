import os
import tempfile
import cv2
import ollama
import config

def parse_answer(text):
    upper = text.strip().upper()
    for token in ("RED", "BLUE", "GREEN", "NONE"):
        if upper == token:
            return token
    for token in ("RED", "BLUE", "GREEN", "NONE"):
        if token in upper:
            return token
    return "NONE"

cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
ok, frame = cap.read()
cap.release()
if not ok:
    raise RuntimeError("Camera capture failed")

instruction = input("指示を入力してください: ").strip()

with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
    image_path = tmp.name
cv2.imwrite(image_path, frame)

prompt = f"""
画像には赤・青・緑のカードがあります。
ユーザーの指示は「{instruction}」です。
画像と指示の両方を確認し、指すべきカードを選んでください。
回答は RED / BLUE / GREEN / NONE のどれか1語だけにしてください。
"""

try:
    response = ollama.chat(
        model=config.VLM_MODEL,
        messages=[{"role":"user","content":prompt,"images":[image_path]}],
    )
    raw = response.message.content
    print("RAW:", raw)
    print("TARGET:", parse_answer(raw))
finally:
    try:
        os.remove(image_path)
    except OSError:
        pass
