import json
from pathlib import Path
import unittest
from control import Detection, StableDecision, choose, validate_config
from pico.protocol import angle_to_pulse_us, parse_command

ROOT = Path(__file__).resolve().parents[1]


class DecisionsTest(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config.json").read_text())

    def test_meter_requires_one_confident_object(self):
        bottle = Detection("bottle", 0.9, .1, .1, .4, .8)
        cup = Detection("cup", 0.9, .5, .1, .8, .8)
        self.assertEqual(choose([bottle], self.config)[0], "left")
        self.assertIsNone(choose([bottle, cup], self.config)[0])
        self.assertIsNone(choose([Detection("bottle", .2, .1, .1, .4, .8)], self.config)[0])
        self.assertIsNone(choose([Detection("bottle", .99, .1, .1, .101, .11)], self.config)[0])
        self.assertIsNone(choose([Detection("person", .99, .1, .1, .9, .9)], self.config)[0])

    def test_locate_uses_target_position_and_rejects_boundary(self):
        for x, expected in [(0.2, "left"), (.5, "center"), (.8, "right"), (1 / 3, None)]:
            detection = Detection("bottle", .95, x - .1, .1, x + .1, .8)
            self.assertEqual(choose([detection], self.config, "locate", "bottle")[0], expected)

    def test_jitter_does_not_actuate(self):
        gate = StableDecision(self.config)
        for now, slot in [(0, "left"), (.4, "right"), (.8, "left"), (1.2, "right")]:
            self.assertIsNone(gate.update(slot, now))
        self.assertIsNone(gate.update("right", 1.6))
        self.assertEqual(gate.update("right", 2.1), "right")
        self.assertEqual(gate.update(None, 2.4), "right")
        self.assertIsNone(gate.update(None, 3.4))

    def test_large_observation_gap_restarts_stability(self):
        gate = StableDecision(self.config)
        gate.update("left", 0)
        gate.update("left", .5)
        self.assertIsNone(gate.update("left", 10))
        self.assertIsNone(gate.update("left", 10.4))
        self.assertEqual(gate.update("left", 10.9), "left")

    def test_calibration_values_are_bounded(self):
        self.config["angles"]["left"] = 180
        with self.assertRaises(ValueError):
            validate_config(self.config)

    def test_exact_firmware_protocol_rejects_bad_commands(self):
        self.assertEqual(parse_command("POINT 90"), ("POINT", 90))
        self.assertEqual(parse_command("STOP"), ("STOP", None))
        for value in ["POINT 0", "POINT 180", "POINT -1", "POINT nan", "POINT 40.0", "MOVE 90", "POINT 90 extra"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_command(value)
        self.assertEqual(angle_to_pulse_us(90), 1500)
        self.assertTrue(1000 < angle_to_pulse_us(30) < angle_to_pulse_us(150) < 2000)


if __name__ == "__main__":
    unittest.main()
