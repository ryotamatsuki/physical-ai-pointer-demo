"""Offline synthetic two-axis data preflight. This is NOT a SmolVLA inference test.

Usage: python demos/vla_pan_tilt/preflight.py --out /tmp/vla-preflight --scenes 20
Creates two different Japanese tasks per IDENTICAL scene image, plus held-out scenes.
Only standard-library dependencies. Images are PPM so Pillow/NumPy can read them in Colab.
"""
import argparse
import json
import math
import random
from pathlib import Path

SIZE = 96
STEPS = 12
TASKS = {"red": "赤い丸を指して", "blue": "青い丸を指して"}
ANGLE_MIN, ANGLE_MAX = 30.0, 150.0


def render_ppm(path, red, blue):
    """A static RGB camera surrogate with colored targets, not an actual camera."""
    background = (235, 236, 230)
    pixels = bytearray(bytes(background) * (SIZE * SIZE))
    for center, color in ((red, (232, 66, 60)), (blue, (46, 98, 218))):
        cx, cy = center
        for y in range(max(0, cy - 7), min(SIZE, cy + 8)):
            for x in range(max(0, cx - 7), min(SIZE, cx + 8)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= 49:
                    offset = (y * SIZE + x) * 3
                    pixels[offset : offset + 3] = bytes(color)
    path.write_bytes(f"P6\n{SIZE} {SIZE}\n255\n".encode() + pixels)


def teacher_angle(pixel_location):
    """Only for generating teacher demonstrations, NEVER for VLA inference."""
    x, y = pixel_location
    pan = 90 + (x / (SIZE - 1) - 0.5) * 85
    tilt = 90 - (y / (SIZE - 1) - 0.5) * 65
    return [round(pan, 3), round(tilt, 3)]


def interpolate(start, goal, steps=STEPS):
    trajectory = []
    for i in range(steps):
        fraction = (i + 1) / steps
        smooth = fraction * fraction * (3 - 2 * fraction)
        trajectory.append([round(a + (b - a) * smooth, 3) for a, b in zip(start, goal)])
    return trajectory


def generate(out, scenes=20, seed=20261017):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    frames = out / "images"
    frames.mkdir(exist_ok=True)
    rng = random.Random(seed)
    episodes = []
    for scene_id in range(scenes):
        # Keep the layout unseen across train/test. Both instructions use the SAME image.
        red = (rng.randint(13, 82), rng.randint(18, 74))
        blue = (rng.randint(13, 82), rng.randint(18, 74))
        while (red[0] - blue[0]) ** 2 + (red[1] - blue[1]) ** 2 < 625:
            blue = (rng.randint(13, 82), rng.randint(18, 74))
        image_file = frames / f"scene_{scene_id:04d}.ppm"
        render_ppm(image_file, red, blue)
        split = "test" if scene_id % 5 == 0 else "train"
        for target, center in (("red", red), ("blue", blue)):
            start = [90.0, 90.0]
            goal = teacher_angle(center)
            commanded = interpolate(start, goal)
            last = start
            rows = []
            for action in commanded:
                assert len(action) == 2 and all(ANGLE_MIN <= a <= ANGLE_MAX for a in action)
                rows.append({"state": last, "action": action})
                last = action
            episodes.append({
                "id": f"scene_{scene_id:04d}_{target}",
                "scene_id": scene_id,
                "split": split,
                "task": TASKS[target],
                "target": target,
                "image": str(image_file.relative_to(out)).replace("\\", "/"),
                "frames": rows,
                "teacher_goal": goal,
            })
    payload = {"metadata": {"kind": "synthetic_teacher_only", "fps": 10,
                            "camera_size": [SIZE, SIZE], "action_dim": 2,
                            "state_dim": 2, "scenes": scenes, "episodes": len(episodes)},
               "episodes": episodes}
    (out / "episodes.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    validate(payload)
    return payload


def validate(payload):
    episodes = payload["episodes"]
    assert episodes, "empty dataset"
    by_scene = {}
    for ep in episodes:
        by_scene.setdefault(ep["scene_id"], {})[ep["target"]] = ep
        assert len(ep["frames"]) == STEPS
        assert all(len(frame["state"]) == len(frame["action"]) == 2 for frame in ep["frames"])
        assert all(math.isfinite(v) and ANGLE_MIN <= v <= ANGLE_MAX
                   for frame in ep["frames"] for v in frame["action"])
        assert ep["frames"][-1]["action"] == ep["teacher_goal"]
    for pair in by_scene.values():
        assert set(pair) == {"red", "blue"}
        assert pair["red"]["image"] == pair["blue"]["image"], "language cannot be isolated"
        assert pair["red"]["teacher_goal"] != pair["blue"]["teacher_goal"], "language not causal"
    if len(by_scene) >= 5:
        train = {e["scene_id"] for e in episodes if e["split"] == "train"}
        test = {e["scene_id"] for e in episodes if e["split"] == "test"}
        assert train and test and not (train & test), "scene leakage"
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="vla_preflight_data")
    parser.add_argument("--scenes", type=int, default=20)
    args = parser.parse_args()
    if args.scenes < 5:
        parser.error("--scenes must be at least 5")
    result = generate(args.out, args.scenes)
    print("PASS: paired Japanese tasks, 2-axis trajectory, safety bounds, scene-level holdout")
    print("scenes:", result["metadata"]["scenes"], "episodes:", result["metadata"]["episodes"])
