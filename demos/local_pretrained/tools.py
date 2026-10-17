"""Small setup helpers for the Windows launchers and command line."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def select_port(port=None, allow_dry_run=False):
    if port:
        return port
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    for item in ports:
        print(item.device, item.description)
    if allow_dry_run:
        print("Enter: camera/AI test only, without a motor")
    choice = input("Pico port (example COM5): ").strip()
    if not choice and allow_dry_run:
        return None
    if choice not in {p.device for p in ports}:
        raise ValueError("Select a port from the list above")
    return choice


def cameras():
    import cv2
    from demo import load_config, open_camera
    config = load_config()
    print("0..4: select camera; B: switch Windows backend; S: save; Q: cancel")
    current, backend = config["camera_index"], config["camera_backend"]
    cap = None
    try:
        while True:
            if cap is None:
                try:
                    cap = open_camera(current, backend)
                except RuntimeError as exc:
                    print(exc)
                    current = int(input("Camera number (0, 1, 2...): "))
                    backend = input("Backend (auto / msmf / any) [auto]: ").strip() or "auto"
                    continue
            ok, frame = cap.read()
            if not ok:
                cap.release()
                cap = None
                backend = input("No frame. Try backend (msmf / any) [any]: ").strip() or "any"
                continue
            cv2.putText(frame, f"Camera {current} / {backend} | 0..4 select | B backend | S save | Q quit",
                        (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)
            cv2.imshow("Camera setup", frame)
            key = cv2.waitKey(20) & 0xFF
            if key in (ord("q"), 27):
                return
            if key == ord("s"):
                config["camera_index"], config["camera_backend"] = current, backend
                (ROOT / "config.json").write_text(json.dumps(config, indent=2) + "\n")
                print("Saved camera selection.")
                return
            if ord("0") <= key <= ord("4"):
                current = key - ord("0")
                cap.release()
                cap = None
            if key == ord("b"):
                backend = "msmf" if backend != "msmf" else "dshow"
                cap.release()
                cap = None
    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["ports", "cameras", "flash", "calibrate", "run", "check"])
    parser.add_argument("--port")
    args = parser.parse_args()
    if args.action == "ports":
        from serial.tools import list_ports
        for p in list_ports.comports():
            print(p.device, p.description)
    elif args.action == "cameras":
        cameras()
    elif args.action == "check":
        for name in ("numpy", "opencv-python", "pyserial", "mpremote"):
            print(name, importlib.metadata.version(name))
        from setup_model import main as verify
        verify()
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"], check=True, cwd=ROOT)
    elif args.action == "flash":
        port = select_port(args.port)
        # mpremote interrupts a running main.py before copying these two files.
        for filename in ("protocol.py", "main.py"):
            subprocess.run([sys.executable, "-m", "mpremote", "connect", port,
                            "fs", "cp", str(ROOT / "pico" / filename), ":" + filename], check=True)
        subprocess.run([sys.executable, "-m", "mpremote", "connect", port, "reset"], check=True)
        print("Pico files copied. Disconnect/reconnect USB before calibration.")
    elif args.action == "calibrate":
        from demo import load_config
        from serial_link import Link
        config = load_config()
        print("Remove arrow first. C: center; L/R: ends; S: stop; Q: quit")
        print("PWM turns off automatically about 2 seconds after the last command.")
        with Link(select_port(args.port)) as link:
            while True:
                command = input("L / C / R / S / Q: ").strip().lower()
                if command == "q":
                    break
                slot = {"l": "left", "c": "center", "r": "right"}.get(command)
                if command == "s":
                    link.apply(None)
                elif slot:
                    print("Requested slot", slot, "control angle", config["angles"][slot])
                    link.apply(config["angles"][slot])
                    time.sleep(0.5)
    else:
        port = select_port(args.port, allow_dry_run=True)
        command = [sys.executable, str(ROOT / "demo.py")]
        if port:
            command += ["--port", port]
        raise SystemExit(subprocess.call(command, cwd=ROOT))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped.")
    except Exception as exc:
        print("ERROR:", exc)
        raise SystemExit(1)
