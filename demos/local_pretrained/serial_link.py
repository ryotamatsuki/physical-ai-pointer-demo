"""Tiny USB protocol. No port means an explicit, motor-free dry run."""
import time
from pico.protocol import parse_command


class Link:
    def __init__(self, port=None):
        self.serial = None
        self.last_value = object()
        if port:
            import serial
            self.serial = serial.Serial(port, 115200, timeout=0.15, write_timeout=1)
            ready = False
            try:
                deadline = time.monotonic() + 4
                while time.monotonic() < deadline:
                    self.serial.write(b"HELLO\n")
                    if b"READY physical-ai-v1" in self.serial.readline():
                        ready = True
                        break
                if not ready:
                    raise RuntimeError("Pico did not answer. Check main.py, COM port, and close Thonny.")
                self.apply(None)
            except BaseException:
                self.serial.close()
                raise

    def apply(self, angle):
        command = "STOP" if angle is None else "POINT " + str(angle)
        parse_command(command)  # Use exactly the parser deployed on the Pico.
        if self.serial:
            self.serial.write((command + "\n").encode("ascii"))
            # Drain acknowledgements without waiting. Detect firmware errors.
            while self.serial.in_waiting:
                line = self.serial.readline().decode("ascii", errors="replace").strip()
                if line.startswith("ERR"):
                    raise RuntimeError("Pico rejected command: " + line)
        if angle != self.last_value:
            print(("USB: " if self.serial else "DRY RUN: ") + command, flush=True)
            self.last_value = angle

    def close(self):
        if self.serial:
            try:
                self.serial.write(b"STOP\n")
                self.serial.flush()
            finally:
                self.serial.close()
                self.serial = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
