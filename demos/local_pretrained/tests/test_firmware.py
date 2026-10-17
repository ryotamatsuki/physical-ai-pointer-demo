"""Execute the real MicroPython main.py against simulated clock/GPIO/USB."""
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import contextlib
import io
import unittest
from unittest.mock import patch
from pico import protocol


class FirmwareTest(unittest.TestCase):
    def simulate(self, message, duration=2400):
        now = [0]
        chars = deque(message)
        events = []
        class Pin:
            OUT = 1
            def __init__(self, *args): pass
            def on(self): pass
            def off(self): pass
        class PWM:
            def __init__(self, pin): pass
            def freq(self, value): pass
            def duty_u16(self, value): events.append((now[0], value))
            def duty_ns(self, value): events.append((now[0], value))
        class Poll:
            def register(self, *args): pass
            def poll(self, timeout): return bool(chars)
        def tick():
            return now[0]
        def sleep(ms):
            now[0] += ms
            if now[0] >= duration:
                raise KeyboardInterrupt
        modules = {
            "machine": SimpleNamespace(Pin=Pin, PWM=PWM),
            "sys": SimpleNamespace(stdin=SimpleNamespace(read=lambda n: chars.popleft())),
            "select": SimpleNamespace(poll=Poll, POLLIN=1),
            "time": SimpleNamespace(ticks_ms=tick, ticks_diff=lambda a, b: a - b, sleep_ms=sleep),
            "protocol": protocol}
        code = (Path(__file__).resolve().parents[1] / "pico/main.py").read_text()
        with patch.dict("sys.modules", modules), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                exec(compile(code, "pico/main.py", "exec"), {})
        return events

    def test_no_motion_at_boot(self):
        self.assertTrue(all(pulse == 0 for _, pulse in self.simulate("")))

    def test_watchdog_removes_pwm_after_usb_stops(self):
        events = self.simulate("POINT 40\n")
        self.assertTrue(any(pulse > 0 for _, pulse in events))
        watchdog_off = [t for t, pulse in events if pulse == 0 and 1900 < t < 2300]
        self.assertTrue(watchdog_off)
        self.assertEqual(events[-1][1], 0)

    def test_invalid_command_stops_real_firmware(self):
        events = self.simulate("POINT 40\nPOINT 999\n", duration=500)
        self.assertFalse(any(t > 30 and pulse > 0 for t, pulse in events))


if __name__ == "__main__":
    unittest.main()
