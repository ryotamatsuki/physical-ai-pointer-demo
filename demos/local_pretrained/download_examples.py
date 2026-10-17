"""Optional: fetch the tiny, public COCO8 teaching subset. Never train."""
from pathlib import Path
import io
import urllib.request
import zipfile

URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco8.zip"


def main():
    destination = Path(__file__).resolve().parent / "examples"
    destination.mkdir(exist_ok=True)
    with urllib.request.urlopen(URL, timeout=60) as response:
        content = response.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise RuntimeError("Unexpectedly large archive")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise RuntimeError("Unsafe archive path")
            if member.file_size > 20 * 1024 * 1024:
                raise RuntimeError("Unexpectedly large file")
        archive.extractall(destination)
    (destination / "SOURCE.txt").write_text(
        "COCO8, downloaded from Ultralytics assets.\n" + URL + "\n"
        "Original images: COCO/Flickr. Refer to original image licenses for redistribution.\n"
        "This is an optional software teaching/test subset, not extra training for this demo.\n")
    print("Downloaded teaching/test examples to", destination)
    print("Training is NOT required. Use python demo.py --image PATH_TO_JPG")


if __name__ == "__main__":
    main()
