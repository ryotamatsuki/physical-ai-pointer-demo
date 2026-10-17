"""Camera -> pretrained AI -> stable decision -> USB -> real pointer."""
import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
import cv2
from control import SLOTS, StableDecision, choose, validate_config
from detector import CLASSES, Detector
from serial_link import Link

ROOT = Path(__file__).resolve().parent


def load_config(path=None):
    config = json.loads(Path(path or ROOT / "config.json").read_text(encoding="utf-8"))
    validate_config(config)
    return config


def open_camera(index, backend="auto"):
    selected = backend
    if selected == "auto":
        selected = "dshow" if sys.platform == "win32" else "any"
    backend_id = {"dshow": cv2.CAP_DSHOW, "msmf": cv2.CAP_MSMF,
                  "any": cv2.CAP_ANY}.get(selected)
    if backend_id is None:
        raise ValueError("backend must be auto, dshow, msmf or any")
    cap = cv2.VideoCapture(index, backend_id)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Camera unavailable. Try --camera 1 or --backend msmf / any.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def draw_slots(frame):
    height, width = frame.shape[:2]
    for index, name in enumerate(SLOTS):
        x = int(width * index / 3)
        if index:
            cv2.line(frame, (x, 0), (x, height), (180, 180, 180), 1)
        cv2.putText(frame, name.upper(), (x + 12, height - 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return frame


def annotate(frame, detections, config):
    height, width = frame.shape[:2]
    for d in detections:
        if d.label not in config["classes"]:
            continue
        a, b = (int(d.x1 * width), int(d.y1 * height))
        c, e = (int(d.x2 * width), int(d.y2 * height))
        cv2.rectangle(frame, (a, b), (c, e), (30, 220, 130), 2)
        cv2.putText(frame, f"{d.label} {d.score:.2f}", (a, max(20, b - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 220, 130), 2)
    return frame


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--camera", type=int)
    parser.add_argument("--backend", choices=["auto", "dshow", "msmf", "any"])
    parser.add_argument("--port", help="COM5, /dev/ttyACM0, etc. Omit for dry run.")
    parser.add_argument("--mode", choices=["meter", "locate"], default="meter")
    parser.add_argument("--target", help="Defaults to the first class in config.json")
    parser.add_argument("--image", help="One image: inference only, never actuates hardware.")
    parser.add_argument("--output", help="Annotated image output; requires --image")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    args.target = args.target or config["classes"][0]
    if any(name not in CLASSES for name in config["classes"]):
        parser.error("config classes must be names from coco_classes.json")
    if args.target not in config["classes"]:
        parser.error("--target must be one of config classes")
    model = ROOT / config["model"]
    if not model.is_file():
        raise RuntimeError("Missing model. Run python setup_model.py")
    detector = Detector(model, confidence=config["confidence"])
    if args.image:
        if args.port:
            parser.error("--image never operates motors; remove --port")
        frame = cv2.imread(str(Path(args.image)))
        if frame is None:
            raise RuntimeError("Could not read image")
        detections = detector.detect(frame)
        slot, reason = choose(detections, config, args.mode, args.target)
        print(json.dumps({"detections": [asdict(d) for d in detections],
                          "proposed_slot": slot, "reason": reason,
                          "hardware": "not connected"}, ensure_ascii=False, indent=2))
        if args.output:
            cv2.imwrite(args.output, annotate(frame, detections, config))
        return 0
    cap = open_camera(args.camera if args.camera is not None else config["camera_index"],
                      args.backend or config["camera_backend"])
    gate = StableDecision(config)
    paused, mode, target = False, args.mode, args.target
    print("SPACE: pause/resume; M: meter/locate; 1/2/3: target; Q: quit")
    try:
        with Link(args.port) as link:
            while True:
                started = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    link.apply(None)
                    raise RuntimeError("No camera frame. Check EOS power and close EOS Utility/Zoom.")
                if config["mirror"]:
                    frame = cv2.flip(frame, 1)
                detections = [] if paused else detector.detect(frame)
                raw, reason = choose(detections, config, mode, target)
                stable = None if paused else gate.update(raw, time.monotonic())
                if paused:
                    gate.reset()
                angle = config["angles"].get(stable) if stable else None
                link.apply(angle)  # Repeat each frame to service the Pico's watchdog.
                display = annotate(frame.copy(), detections, config)
                if mode == "locate":
                    draw_slots(display)
                elapsed = time.monotonic() - started
                status = f"{mode.upper()} target={target} -> {stable or 'HOLD'}"
                if paused:
                    status = "PAUSED - MOTOR SIGNAL OFF"
                transport = "USB" if args.port else "DRY RUN - NO MOTOR"
                for i, line in enumerate((status, reason, f"{transport} | {elapsed:.2f}s/frame",
                                           "SPACE pause | M mode | 1/2/3 target | Q quit")):
                    y = 24 + i * 25
                    cv2.putText(display, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                                0.52, (0, 0, 0), 4)
                    cv2.putText(display, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX,
                                0.52, (255, 255, 255), 1)
                cv2.imshow("Physical AI - pretrained / no training", display)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord(" "):
                    paused = not paused
                    gate.reset()
                    link.apply(None)
                elif key == ord("m"):
                    mode = "locate" if mode == "meter" else "meter"
                    gate.reset()
                    link.apply(None)
                elif key in (ord("1"), ord("2"), ord("3")):
                    target = config["classes"][key - ord("1")]
                    gate.reset()
                    link.apply(None)
                if cv2.getWindowProperty("Physical AI - pretrained / no training", cv2.WND_PROP_VISIBLE) < 1:
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(1)
