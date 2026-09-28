"""Modal backend for the Physical AI pointer demo.

Deploy flow:
    modal run modal_backend.py::download_model
    modal deploy modal_backend.py

The HTTP endpoint requires Modal proxy authentication.
"""

from __future__ import annotations

import base64
import io
import time

import modal
from fastapi import Request

APP_NAME = "physical-ai-pointer-vlm"
MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
MODEL_DIR = "/models/qwen3-vl-2b"
VOLUME_NAME = "physical-ai-pointer-model-cache"
SCHEMA_VERSION = "1"

app = modal.App(APP_NAME)

model_volume = modal.Volume.from_name(
    VOLUME_NAME,
    create_if_missing=True,
)

download_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub")
)

inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "git+https://github.com/huggingface/transformers.git",
        "accelerate",
        "pillow",
    )
)


@app.function(
    image=download_image,
    volumes={"/models": model_volume},
    timeout=1800,
)
def download_model():
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
    )
    model_volume.commit()
    print(f"Model cached: {MODEL_ID} -> {MODEL_DIR}")


def _normalize_target(text: str) -> str:
    upper = str(text).strip().upper()

    for token in ("RED", "BLUE", "GREEN", "NONE"):
        if upper == token:
            return token

    for token in ("RED", "BLUE", "GREEN", "NONE"):
        if token in upper:
            return token

    return "NONE"


@app.cls(
    image=inference_image,
    gpu="T4",
    volumes={"/models": model_volume},
    min_containers=0,
    max_containers=1,
    scaledown_window=900,
    timeout=600,
)
class PointerVLM:
    @modal.enter()
    def load_model(self):
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

        self.processor = AutoProcessor.from_pretrained(MODEL_DIR)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            MODEL_DIR,
            dtype="auto",
            device_map="auto",
        )
        self.model.eval()
        print(f"Loaded {MODEL_ID}")

    @modal.method()
    def classify(self, image_b64: str, instruction: str) -> dict:
        import torch
        from PIL import Image

        started = time.perf_counter()

        image_bytes = base64.b64decode(image_b64, validate=True)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        prompt = f"""
画像には赤・青・緑のカードがあります。
ユーザーの指示は「{instruction}」です。

画像と指示の両方を確認し、指すべきカードを1つ選んでください。
回答は RED / BLUE / GREEN / NONE のどれか1語だけにしてください。
対象が一意に決まらない場合は NONE としてください。
"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)

        with torch.inference_mode():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=12,
                do_sample=False,
            )

        trimmed = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(
                inputs.input_ids,
                generated_ids,
            )
        ]

        raw = self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

        return {
            "target": _normalize_target(raw),
            "model": MODEL_ID,
            "inference_ms": round((time.perf_counter() - started) * 1000, 1),
        }


@app.function(timeout=180)
@modal.fastapi_endpoint(
    method="POST",
    requires_proxy_auth=True,
)
async def classify_api(request: Request):
    payload = await request.json()

    if payload.get("schema_version") != SCHEMA_VERSION:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "unsupported_schema_version",
        }

    request_id = str(payload.get("request_id", "")).strip()
    instruction = str(payload.get("instruction", "")).strip()
    image_b64 = str(payload.get("image_b64", "")).strip()

    if not request_id:
        return {
            "schema_version": SCHEMA_VERSION,
            "error": "missing_request_id",
        }

    if not instruction or len(instruction) > 200:
        return {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "error": "invalid_instruction",
        }

    if not image_b64:
        return {
            "schema_version": SCHEMA_VERSION,
            "request_id": request_id,
            "error": "missing_image",
        }

    result = PointerVLM().classify.remote(
        image_b64,
        instruction,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        **result,
    }
