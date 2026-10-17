"""Verify bundled weights, or restore them from the original public source."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT / "models/model_manifest.json").read_text())
    destination = ROOT / "models" / manifest["filename"]
    expected = manifest["sha256"]
    def valid(path):
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected
    if valid(destination):
        print("Model OK. Already trained; no training/data collection required.")
        return
    sources = [manifest["source_url"],
        "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/object_detection_yolox/" + manifest["filename"]]
    temporary = destination.with_suffix(".download")
    for source in sources:
        try:
            print("Downloading pretrained YOLOX-s...")
            with urllib.request.urlopen(source, timeout=90) as response, temporary.open("wb") as output:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
            if not valid(temporary):
                raise RuntimeError("Model checksum mismatch")
            os.replace(temporary, destination)
            print("Model downloaded and SHA256 verified.")
            return
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            print("Download attempt failed:", type(exc).__name__)
    raise RuntimeError("Could not download model. Check network/proxy, then retry.")


if __name__ == "__main__":
    main()
