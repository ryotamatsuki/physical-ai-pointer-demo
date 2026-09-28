from __future__ import annotations

import math
import time

import serial

import config


class PicoLinkError(RuntimeError):
    pass


class PicoLink:
    def __init__(self):
        self.ser = serial.Serial(
            config.SERIAL_PORT,
            config.SERIAL_BAUD,
            timeout=0.1,
            write_timeout=1.0,
        )
        self._seq = 0
        time.sleep(0.5)
        self.ser.reset_input_buffer()
        self.ping()

    def _next_seq(self):
        self._seq += 1
        return str(self._seq)

    def _send_and_wait(self, command, expected_prefix):
        if len(command.encode("ascii")) > 96:
            raise PicoLinkError("Command too long")

        self.ser.write((command + "\n").encode("ascii"))
        deadline = time.monotonic() + config.SERIAL_ACK_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            raw = self.ser.readline()
            if not raw:
                continue

            line = raw.decode("ascii", errors="replace").strip()
            if line.startswith(expected_prefix):
                return line

            if line.startswith("ERROR "):
                raise PicoLinkError(line)

            # Ignore unrelated startup/stale lines and keep waiting for
            # the current sequence-specific ACK.

        raise PicoLinkError(
            f"Timeout waiting for Pico ACK: {expected_prefix}"
        )

    def ping(self):
        seq = self._next_seq()
        line = self._send_and_wait(
            f"PING {seq}",
            f"PONG {seq}",
        )
        if line != f"PONG {seq}":
            raise PicoLinkError(f"Unexpected PING response: {line}")
        return line

    def send_angle(self, angle):
        if not math.isfinite(angle):
            raise PicoLinkError("Angle is not finite")

        if not (config.SERVO_MIN <= angle <= config.SERVO_MAX):
            raise PicoLinkError(
                f"Angle outside PC safety range: {angle}"
            )

        seq = self._next_seq()
        line = self._send_and_wait(
            f"ANGLE {seq} {angle:.2f}",
            f"OK {seq} ",
        )

        parts = line.split()
        if len(parts) != 3:
            raise PicoLinkError(f"Malformed ANGLE ACK: {line}")

        try:
            ack_angle = float(parts[2])
        except ValueError as exc:
            raise PicoLinkError(f"Invalid ACK angle: {line}") from exc

        if abs(ack_angle - angle) > 0.11:
            raise PicoLinkError(
                f"ACK angle mismatch: sent={angle:.2f}, ack={ack_angle:.2f}"
            )

        return line

    def stop_pwm(self):
        seq = self._next_seq()
        line = self._send_and_wait(
            f"STOP {seq}",
            f"STOPPED {seq}",
        )
        if line != f"STOPPED {seq}":
            raise PicoLinkError(f"Unexpected STOP response: {line}")
        return line

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.stop_pwm()
        except Exception:
            pass
        self.close()
