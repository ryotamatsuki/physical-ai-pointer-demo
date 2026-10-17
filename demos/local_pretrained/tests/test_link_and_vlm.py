from types import SimpleNamespace
from unittest.mock import patch
import unittest
from serial_link import Link
from vlm_demo import parse_answer


class FakePort:
    def __init__(self, *args, **kwargs):
        self.writes = []
        self.responses = []
        self.closed = False
    def write(self, data):
        self.writes.append(data)
        self.responses.append(b"READY physical-ai-v1\n" if data == b"HELLO\n" else b"OK\n")
    @property
    def in_waiting(self):
        return len(self.responses)
    def readline(self):
        return self.responses.pop(0) if self.responses else b""
    def flush(self): pass
    def close(self): self.closed = True


class IntegrationBoundaryTest(unittest.TestCase):
    def test_usb_handshake_stop_and_range_guard(self):
        port = FakePort()
        with patch.dict("sys.modules", {"serial": SimpleNamespace(Serial=lambda *a, **k: port)}):
            with Link("FAKE") as link:
                link.apply(90)
                with self.assertRaises(ValueError):
                    link.apply(999)
        self.assertIn(b"POINT 90\n", port.writes)
        self.assertNotIn(b"POINT 999\n", port.writes)
        self.assertEqual(port.writes[-1], b"STOP\n")
        self.assertTrue(port.closed)

    def test_vlm_can_only_select_a_named_slot(self):
        self.assertEqual(parse_answer({"slot": "left", "object": "pen"})[0], "left")
        self.assertEqual(parse_answer({"slot": "none"})[0], "none")
        for value in [{"angle": 999}, {"slot": "POINT 999"}, None]:
            with self.assertRaises(ValueError):
                parse_answer(value)


if __name__ == "__main__":
    unittest.main()
