import importlib.metadata
import json
import platform
import sys

PACKAGES = [
    "opencv-python",
    "numpy",
    "pyserial",
    "requests",
    "modal",
    "fastapi",
]

report = {
    "python": sys.version,
    "platform": platform.platform(),
    "packages": {},
}

for package in PACKAGES:
    try:
        report["packages"][package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        report["packages"][package] = None

print(json.dumps(report, ensure_ascii=False, indent=2))
