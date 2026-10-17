"""Run: python -m unittest discover -s demos/vla_pan_tilt -p "test_*.py"."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preflight import generate, validate


class PreflightTest(unittest.TestCase):
    def test_dataset_and_counterfactual(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = generate(folder, scenes=10)
            self.assertTrue(validate(payload))
            self.assertEqual(len(payload["episodes"]), 20)
            self.assertEqual(payload["metadata"]["action_dim"], 2)
            self.assertTrue((Path(folder) / "episodes.json").is_file())
            self.assertTrue((Path(folder) / "images" / "scene_0000.ppm").is_file())
            for scene_id in range(10):
                pair = [e for e in payload["episodes"] if e["scene_id"] == scene_id]
                self.assertEqual(pair[0]["image"], pair[1]["image"])
                self.assertNotEqual(pair[0]["teacher_goal"], pair[1]["teacher_goal"])

    def test_split_by_scene_no_leakage(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = generate(folder, scenes=10)
            train = {e["scene_id"] for e in payload["episodes"] if e["split"] == "train"}
            test = {e["scene_id"] for e in payload["episodes"] if e["split"] == "test"}
            self.assertEqual(len(train), 8)
            self.assertEqual(len(test), 2)
            self.assertFalse(train.intersection(test))

    def test_reproducible_and_safe(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            x = generate(a, scenes=5, seed=123)
            y = generate(b, scenes=5, seed=123)
            self.assertEqual(x, y)
            for ep in x["episodes"]:
                for frame in ep["frames"]:
                    self.assertTrue(all(30 <= v <= 150 for v in frame["action"]))


if __name__ == "__main__":
    unittest.main()
