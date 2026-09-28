"""Authenticated client for the Modal VLM endpoint."""

from __future__ import annotations

import base64
import os
import uuid

import cv2
import requests

import config

ALLOWED_TARGETS = {"RED", "BLUE", "GREEN", "NONE"}
SCHEMA_VERSION = "1"


class ModalVLMError(RuntimeError):
    pass


def _prepare_jpeg(frame) -> bytes:
    height, width = frame.shape[:2]

    if width > config.MAX_VLM_IMAGE_WIDTH:
        scale = config.MAX_VLM_IMAGE_WIDTH / width
        frame = cv2.resize(
            frame,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )

    ok, encoded = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY],
    )

    if not ok:
        raise ModalVLMError("JPEG encoding failed")

    return encoded.tobytes()


def classify_frame(frame, instruction: str) -> dict:
    url = config.MODAL_CLASSIFY_URL.strip()

    if not url or "REPLACE-WITH" in url:
        raise ModalVLMError(
            "pc/config.py の MODAL_CLASSIFY_URL を設定してください。"
        )

    proxy_key = os.getenv("MODAL_PROXY_KEY", "").strip()
    proxy_secret = os.getenv("MODAL_PROXY_SECRET", "").strip()

    if not proxy_key or not proxy_secret:
        raise ModalVLMError(
            "MODAL_PROXY_KEY / MODAL_PROXY_SECRET が未設定です。"
        )

    request_id = str(uuid.uuid4())
    image_b64 = base64.b64encode(_prepare_jpeg(frame)).decode("ascii")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "instruction": instruction,
        "image_b64": image_b64,
    }

    headers = {
        "Modal-Key": proxy_key,
        "Modal-Secret": proxy_secret,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=config.MODAL_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ModalVLMError(f"Modal request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise ModalVLMError("Modal returned non-JSON response") from exc

    if data.get("schema_version") != SCHEMA_VERSION:
        raise ModalVLMError("Schema version mismatch")

    if data.get("request_id") != request_id:
        raise ModalVLMError("Request ID mismatch")

    if "error" in data:
        raise ModalVLMError(f"Modal error: {data['error']}")

    target = str(data.get("target", "")).upper()

    if target not in ALLOWED_TARGETS:
        raise ModalVLMError(f"Invalid target: {target!r}")

    return data
