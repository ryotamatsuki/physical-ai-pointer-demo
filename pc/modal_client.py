"""Authenticated client for the Modal VLM endpoint."""

from __future__ import annotations

import base64
import os
import time
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
    longest = max(width, height)

    if longest > config.MAX_VLM_IMAGE_SIDE:
        scale = config.MAX_VLM_IMAGE_SIDE / longest
        frame = cv2.resize(
            frame,
            (int(round(width * scale)), int(round(height * scale))),
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


def classify_frame(frame, instruction: str, timeout_seconds=None) -> dict:
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

    instruction = str(instruction).strip()
    if not instruction or len(instruction) > 200:
        raise ModalVLMError("Instruction must be 1–200 characters")

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

    if timeout_seconds is None:
        timeout_seconds = config.MODAL_REQUEST_TIMEOUT_SECONDS

    started = time.perf_counter()

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=(5, timeout_seconds),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ModalVLMError(f"Modal request failed: {exc}") from exc

    round_trip_ms = round(
        (time.perf_counter() - started) * 1000,
        1,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise ModalVLMError("Modal returned non-JSON response") from exc

    if not isinstance(data, dict):
        raise ModalVLMError(
            f"Modal JSON must be an object, got {type(data).__name__}"
        )

    if data.get("schema_version") != SCHEMA_VERSION:
        raise ModalVLMError("Schema version mismatch")

    if data.get("request_id") != request_id:
        raise ModalVLMError("Request ID mismatch")

    if "error" in data:
        detail = data.get("raw_output")
        suffix = f" raw={detail!r}" if detail else ""
        raise ModalVLMError(
            f"Modal error: {data['error']}{suffix}"
        )

    target = data.get("target")
    if not isinstance(target, str):
        raise ModalVLMError("Missing or non-string target")

    # Backend contract is exact-token output. Do not normalize prose here.
    if target not in ALLOWED_TARGETS:
        raise ModalVLMError(f"Invalid target: {target!r}")

    data["round_trip_ms"] = round_trip_ms
    return data
