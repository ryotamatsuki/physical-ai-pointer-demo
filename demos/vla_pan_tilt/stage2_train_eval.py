"""Run real SmolVLA 2-axis imitation learning and held-out evaluation in Colab.

The target-angle geometry below is used only to create demonstration labels.
Inference functions accept pixels, a Japanese task string, and joint state only.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

MODEL_ID = "lerobot/smolvla_base"
ROOT = Path("/content/smolvla_stage2")
DATA_ROOT = ROOT / "data"
ASSET_ROOT = ROOT / "assets"
OUTPUT_ROOT = ROOT / "output"
RESULT_ROOT = ROOT / "results"
DRIVE_ROOT = Path("/content/drive/MyDrive/SmolVLA_2axis_Stage2_20261017")
FPS = 10
EPISODE_STEPS = 50
IMAGE_SIZE = 96
SUCCESS_THRESHOLD_DEG = 6.0
TRAIN_SCENES = 100
VAL_SCENES = 10
TEST_SCENES = 30
OVERFIT_SCENES = 4
OVERFIT_STEPS = 100
TRAIN_STEPS = 1000

FEATURES = {
    "observation.state": {
        "dtype": "float32",
        "shape": (2,),
        "names": ["pan", "tilt"],
    },
    "action": {
        "dtype": "float32",
        "shape": (2,),
        "names": ["pan", "tilt"],
    },
    "observation.images.front": {
        "dtype": "video",
        "shape": (IMAGE_SIZE, IMAGE_SIZE, 3),
        "names": ["height", "width", "channels"],
    },
}


def _ensure_dependencies():
    missing = []
    try:
        import av  # noqa: F401
    except ImportError:
        missing.append("av")
    try:
        import accelerate  # noqa: F401
    except ImportError:
        missing.append("accelerate")
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])
    try:
        import lerobot.utils.import_utils as import_utils

        import_utils._require_package_cache.clear()
    except Exception:
        pass


def _load_or_reuse_policy(ns):
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

    policy = ns.get("policy")
    if policy is None:
        cfg = SmolVLAConfig.from_pretrained(MODEL_ID)
        cfg.device = "cuda"
        cfg.input_features = {
            "observation.state": PolicyFeature(type=FeatureType.STATE, shape=(2,)),
            "observation.images.front": PolicyFeature(type=FeatureType.VISUAL, shape=(3, IMAGE_SIZE, IMAGE_SIZE)),
        }
        cfg.output_features = {
            "action": PolicyFeature(type=FeatureType.ACTION, shape=(2,)),
        }
        cfg.use_amp = True
        policy = SmolVLAPolicy.from_pretrained(MODEL_ID, config=cfg)
        print("Loaded base SmolVLA because this runtime did not already contain it.")
    else:
        print("Reusing the already-loaded lerobot/smolvla_base policy from this Colab runtime.")

    policy.config.device = "cuda"
    policy.config.use_amp = True
    policy.config.train_expert_only = True
    policy.config.freeze_vision_encoder = True
    policy.config.chunk_size = EPISODE_STEPS
    policy.config.n_action_steps = EPISODE_STEPS
    policy.config.input_features = {
        "observation.state": PolicyFeature(type=FeatureType.STATE, shape=(2,)),
        "observation.images.front": PolicyFeature(type=FeatureType.VISUAL, shape=(3, IMAGE_SIZE, IMAGE_SIZE)),
    }
    policy.config.output_features = {
        "action": PolicyFeature(type=FeatureType.ACTION, shape=(2,)),
    }
    assert tuple(policy.config.robot_state_feature.shape) == (2,)
    assert tuple(policy.config.action_feature.shape) == (2,)
    return policy.to("cuda").eval()


def target_to_angles(x: float, y: float) -> np.ndarray:
    """Synthetic teacher only. This geometry is never called by inference."""
    pan = 90.0 + (x / (IMAGE_SIZE - 1) - 0.5) * 85.0
    tilt = 90.0 - (y / (IMAGE_SIZE - 1) - 0.5) * 65.0
    return np.array([pan, tilt], dtype=np.float32)


def create_scene(red, blue):
    image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (235, 236, 230))
    draw = ImageDraw.Draw(image)
    for (x, y), color in [(red, (235, 64, 64)), (blue, (53, 96, 237))]:
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color)
    return image


def _random_scene(rng):
    while True:
        red = tuple(int(v) for v in rng.integers(15, 81, size=2))
        blue = tuple(int(v) for v in rng.integers(15, 81, size=2))
        if np.linalg.norm(np.asarray(red) - np.asarray(blue)) >= 24:
            return red, blue


def build_dataset(split, scene_count, seed):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    root = DATA_ROOT / split
    assets = ASSET_ROOT / split
    manifest_path = DATA_ROOT / f"{split}_manifest.json"
    if root.exists() and manifest_path.exists() and (root / "meta" / "info.json").exists():
        manifest = _read_manifest(manifest_path)
        assert len(manifest["scenes"]) == scene_count
        assert manifest["seed"] == seed
        print(f"Reusing finalized {split} dataset with {len(manifest['episodes'])} episodes.")
        return root, manifest_path, manifest
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True, exist_ok=True)

    ds = LeRobotDataset.create(
        repo_id=f"local/pointer_stage2_{split}",
        root=root,
        fps=FPS,
        features=FEATURES,
        robot_type="pico_pan_tilt",
        use_videos=True,
        image_writer_threads=2,
        batch_encoding_size=1,
    )
    rng = np.random.default_rng(seed)
    manifest = {
        "split": split,
        "seed": seed,
        "fps": FPS,
        "episode_steps": EPISODE_STEPS,
        "scenes": [],
        "episodes": [],
    }

    for scene_index in range(scene_count):
        red, blue = _random_scene(rng)
        image = create_scene(red, blue)
        scene_id = f"{split}_{scene_index:04d}"
        image_path = assets / f"{scene_id}.png"
        image.save(image_path)
        pixel_hash = hashlib.sha256(np.asarray(image).tobytes()).hexdigest()

        # Both language episodes for a scene start from the exact same joint state.
        start = rng.uniform([75.0, 75.0], [105.0, 105.0]).astype(np.float32)
        scene_entry = {
            "scene_id": scene_id,
            "image_path": str(image_path),
            "image_sha256": pixel_hash,
            "red_xy": list(red),
            "blue_xy": list(blue),
            "shared_start_state": start.astype(float).tolist(),
        }
        manifest["scenes"].append(scene_entry)

        for color_name, instruction, target_xy in (
            ("red", "赤い丸を指して", red),
            ("blue", "青い丸を指して", blue),
        ):
            goal = target_to_angles(*target_xy)
            state = start.copy()
            episode_index = len(manifest["episodes"])
            for step in range(EPISODE_STEPS):
                u = (step + 1) / EPISODE_STEPS
                smooth = u * u * (3.0 - 2.0 * u)
                action = (start + (goal - start) * smooth).astype(np.float32)
                ds.add_frame(
                    {
                        "observation.state": state.copy(),
                        "action": action.copy(),
                        "observation.images.front": np.asarray(image, dtype=np.uint8).copy(),
                        "task": instruction,
                    }
                )
                state = action.copy()
            ds.save_episode()
            manifest["episodes"].append(
                {
                    "episode_index": episode_index,
                    "scene_id": scene_id,
                    "color": color_name,
                    "instruction": instruction,
                    "image_path": str(image_path),
                    "image_sha256": pixel_hash,
                    "target_xy": list(target_xy),
                    "target_angles": goal.astype(float).tolist(),
                    "start_state": start.astype(float).tolist(),
                }
            )

        if (scene_index + 1) % 10 == 0 or scene_index + 1 == scene_count:
            print(f"{split}: created {scene_index + 1}/{scene_count} paired scenes")

    ds.finalize()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return root, manifest_path, manifest


def _episode_count(dataset):
    if hasattr(dataset, "hf_dataset") and "episode_index" in dataset.hf_dataset.column_names:
        return len(set(int(x) for x in dataset.hf_dataset["episode_index"]))
    for obj, name in ((dataset, "num_episodes"), (dataset.meta, "total_episodes")):
        value = getattr(obj, name, None)
        if value is not None:
            return int(value)
    episodes = getattr(dataset.meta, "episodes", None)
    if episodes is not None:
        return len(episodes)
    raise AssertionError("Could not determine saved episode count from LeRobot metadata")


def inspect_dataset(repo_id, root, expected_scenes, expected_frames, manifest):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    ds = LeRobotDataset(repo_id=repo_id, root=root)
    assert len(ds) == expected_frames, (len(ds), expected_frames)
    assert _episode_count(ds) == expected_scenes * 2, _episode_count(ds)
    assert set(ds.meta.stats.keys()) >= {"observation.state", "action"}, ds.meta.stats.keys()
    assert tuple(ds.meta.features["observation.state"]["shape"]) == (2,)
    assert tuple(ds.meta.features["action"]["shape"]) == (2,)
    sample = ds[0]
    assert tuple(sample["observation.state"].shape[-1:]) == (2,)
    assert tuple(sample["action"].shape[-1:]) == (2,)
    image = sample["observation.images.front"]
    image_shape = tuple(image.shape) if hasattr(image, "shape") else tuple(np.asarray(image).shape)
    assert (IMAGE_SIZE in image_shape and len(image_shape) == 3), image_shape
    fps = ds.meta.info.get("fps")
    assert int(fps) == FPS, f"expected fps={FPS}, metadata fps={fps}"
    episode_ids = np.asarray(ds.hf_dataset["episode_index"], dtype=np.int64)
    states = np.asarray(ds.hf_dataset["observation.state"], dtype=np.float32)
    actions = np.asarray(ds.hf_dataset["action"], dtype=np.float32)
    for entry in manifest["episodes"]:
        frame_ids = np.flatnonzero(episode_ids == int(entry["episode_index"]))
        assert len(frame_ids) == EPISODE_STEPS, (entry["episode_index"], len(frame_ids))
        assert np.allclose(states[frame_ids[0]], entry["start_state"], atol=1e-4)
        assert np.allclose(actions[frame_ids[-1]], entry["target_angles"], atol=1e-4)
        assert np.allclose(states[frame_ids[1:]], actions[frame_ids[:-1]], atol=1e-4)
    print(
        f"{repo_id}: frames={len(ds)}, episodes={_episode_count(ds)}, fps={fps}, "
        f"features={list(ds.meta.features)}, state/action=2, image={image_shape}, "
        f"stats={list(ds.meta.stats)}"
    )
    return ds


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def run_official_training(policy, repo_id, dataset_root, steps, output_dir, label):
    """Call LeRobot's official train() pipeline, reusing the loaded policy object."""
    from accelerate.utils import DistributedDataParallelKwargs
    from lerobot.configs.default import DatasetConfig
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.scripts import lerobot_train

    output_dir = Path(output_dir)
    shutil.rmtree(output_dir, ignore_errors=True)
    cfg = TrainPipelineConfig(
        dataset=DatasetConfig(
            repo_id=repo_id,
            root=str(dataset_root),
            use_imagenet_stats=True,
        ),
        policy=policy.config,
        output_dir=output_dir,
        job_name=f"smolvla_2axis_{label}",
        seed=20261017,
        num_workers=0,
        persistent_workers=False,
        dataloader_multiprocessing_context=None,
        batch_size=2,
        steps=steps,
        log_freq=10,
        save_freq=steps,
        save_checkpoint=True,
        use_policy_training_preset=True,
    )
    cfg.wandb.enable = False
    cfg.policy.device = "cuda"
    cfg.policy.use_amp = True
    cfg.policy.push_to_hub = False
    cfg.policy.train_expert_only = True
    cfg.policy.freeze_vision_encoder = True

    # T4 training uses FP16 autocast (PyTorch's CUDA default) with FP32 master
    # weights. LeRobot v0.6.1 hard-codes BF16 only for initial SmolVLM loading;
    # this wrapper reuses the already-loaded checkpoint and converts it before
    # optimizer construction, without changing the two-dimensional features.
    policy = policy.to(device="cuda", dtype=torch.float32)
    policy.train()
    original_make_policy = lerobot_train.make_policy

    def reuse_loaded_policy(cfg, ds_meta, **kwargs):
        assert tuple(cfg.robot_state_feature.shape) == (2,)
        assert tuple(cfg.action_feature.shape) == (2,)
        assert tuple(ds_meta.features["action"]["shape"]) == (2,)
        return policy

    lerobot_train.make_policy = reuse_loaded_policy
    log_path = RESULT_ROOT / f"{label}_training.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            tee = _Tee(sys.stdout, log_file)
            with redirect_stdout(tee), redirect_stderr(tee):
                print(f"Training phase={label}; steps={steps}; autocast=fp16; master_weights=float32")
                lerobot_train.train(cfg)
    finally:
        lerobot_train.make_policy = original_make_policy
    seconds = time.perf_counter() - started
    memory = {
        "peak_allocated_gib": torch.cuda.max_memory_allocated() / (1024**3),
        "peak_reserved_gib": torch.cuda.max_memory_reserved() / (1024**3),
    }
    print(f"TRAIN_DONE {label}: {seconds:.1f}s, {memory}")
    return {
        "label": label,
        "steps": steps,
        "seconds": seconds,
        "gpu_peak": memory,
        "log_path": str(log_path),
        "output_dir": str(output_dir),
        "checkpoint": _find_checkpoint(output_dir),
    }


def _find_checkpoint(output_dir):
    candidates = list(Path(output_dir).rglob("pretrained_model"))
    candidates = [p for p in candidates if (p / "config.json").exists()]
    if not candidates:
        raise FileNotFoundError(f"No pretrained_model checkpoint found under {output_dir}")
    candidates.sort(key=lambda p: p.stat().st_mtime)
    return candidates[-1]


def _read_manifest(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dataset_episode_samples(dataset, manifest):
    if not hasattr(dataset, "hf_dataset") or "episode_index" not in dataset.hf_dataset.column_names:
        raise AssertionError("LeRobot episode_index column is required for independent-episode evaluation")
    episode_ids = np.asarray(dataset.hf_dataset["episode_index"], dtype=np.int64)
    result = []
    for entry in manifest["episodes"]:
        matches = np.flatnonzero(episode_ids == int(entry["episode_index"]))
        assert len(matches) == EPISODE_STEPS, (entry["episode_index"], len(matches))
        sample = dataset[int(matches[0])]
        state = sample["observation.state"].detach().cpu().numpy().astype(np.float32)
        assert np.allclose(state, np.asarray(entry["start_state"], dtype=np.float32), atol=1e-4)
        if sample.get("task") is not None:
            assert str(sample["task"]) == entry["instruction"]
        result.append((entry, sample))
    return result


def _sample_image_to_pil(value):
    if torch.is_tensor(value):
        arr = value.detach().cpu().numpy()
    else:
        arr = np.asarray(value)
    if arr.ndim == 3 and arr.shape[0] in (1, 3, 4):
        arr = np.transpose(arr, (1, 2, 0))
    if np.issubdtype(arr.dtype, np.floating):
        if arr.size and float(np.nanmax(arr)) <= 1.5:
            arr = arr * 255.0
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    else:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    return Image.fromarray(arr[..., :3], mode="RGB")


def _predict_chunk(policy, preprocess, postprocess, image, instruction, state, seed=123):
    """Inference only: pixels, language, and observed 2-axis state enter the VLA."""
    import torch

    image = image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE))
    pixels = torch.from_numpy(np.asarray(image, dtype=np.uint8).copy()).permute(2, 0, 1).float() / 255.0
    observation = {
        "observation.images.front": pixels,
        "observation.state": torch.as_tensor(state, dtype=torch.float32),
        "task": instruction,
    }
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    batch = preprocess(observation)
    with torch.inference_mode():
        normalized_chunk = policy.predict_action_chunk(batch)
        action_chunk = postprocess(normalized_chunk)
    if isinstance(action_chunk, dict):
        action_chunk = action_chunk.get("action", action_chunk.get("actions"))
    if isinstance(action_chunk, tuple):
        action_chunk = action_chunk[0]
    actions = torch.as_tensor(action_chunk).detach().float().cpu().numpy()
    if actions.ndim == 3:
        actions = actions[0]
    assert actions.shape == (EPISODE_STEPS, 2), actions.shape
    assert np.isfinite(actions).all(), "NaN/Inf in de-normalized actions"
    return actions


def _error_deg(predicted, target):
    return float(np.linalg.norm(np.asarray(predicted, dtype=float) - np.asarray(target, dtype=float)))


def _metric_summary(rows):
    if not rows:
        return {"episodes": 0}
    errors = np.asarray([row["angular_error_deg"] for row in rows], dtype=np.float64)
    return {
        "episodes": int(len(rows)),
        "mean_error_deg": float(np.mean(errors)),
        "median_error_deg": float(np.median(errors)),
        "p95_error_deg": float(np.percentile(errors, 95)),
        "success_threshold_deg": SUCCESS_THRESHOLD_DEG,
        "success_rate": float(np.mean(errors <= SUCCESS_THRESHOLD_DEG)),
    }


def _eval_record(condition, entry, instruction, target, state, actions):
    error = _error_deg(actions[-1], target)
    return {
        "condition": condition,
        "scene_id": entry.get("scene_id", ""),
        "episode_index": entry.get("episode_index", -1),
        "color": entry.get("color", ""),
        "instruction": instruction,
        "start_pan_deg": float(state[0]),
        "start_tilt_deg": float(state[1]),
        "target_pan_deg": float(target[0]),
        "target_tilt_deg": float(target[1]),
        "predicted_final_pan_deg": float(actions[-1, 0]),
        "predicted_final_tilt_deg": float(actions[-1, 1]),
        "angular_error_deg": error,
        "success": bool(error <= SUCCESS_THRESHOLD_DEG),
    }


def _evaluate_manifest(policy, preprocess, postprocess, dataset, manifest, condition):
    rows = []
    samples = _dataset_episode_samples(dataset, manifest)
    by_scene = {}
    example = None
    for entry, sample in samples:
        image = _sample_image_to_pil(sample["observation.images.front"])
        state = np.asarray(sample["observation.state"].detach().cpu(), dtype=np.float32)
        actions = _predict_chunk(policy, preprocess, postprocess, image, entry["instruction"], state)
        row = _eval_record(condition, entry, entry["instruction"], entry["target_angles"], state, actions)
        rows.append(row)
        by_scene.setdefault(entry["scene_id"], {})[entry["color"]] = (image, state, actions, entry)
        if example is None:
            example = (image, actions, entry)
    return rows, by_scene, example


def _write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_losses(log_paths):
    records = []
    for path in log_paths:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "loss" not in line.lower():
                continue
            step_match = re.search(r"(?:step|steps)\s*[:=]\s*(\d+)", line, re.I)
            loss_match = re.search(r"(?:loss|train_loss)\s*[:=]\s*(-?\d+(?:\.\d+)?(?:e[-+]?\d+)?)", line, re.I)
            if loss_match:
                records.append(
                    {
                        "phase": Path(path).name.replace("_training.log", ""),
                        "step": int(step_match.group(1)) if step_match else len(records) + 1,
                        "loss": float(loss_match.group(1)),
                        "log_line": line[:500],
                    }
                )
    return records


def _save_plots(loss_rows, example):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    if loss_rows:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for phase in sorted(set(r["phase"] for r in loss_rows)):
            subset = [r for r in loss_rows if r["phase"] == phase]
            ax.plot([r["step"] for r in subset], [r["loss"] for r in subset], label=phase)
        ax.set(title="SmolVLA 2-axis training loss", xlabel="Logged step", ylabel="Training loss")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(RESULT_ROOT / "loss_curve.png", dpi=160)
        plt.close(fig)

    image, actions, entry = example
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].imshow(image)
    axes[0].set_title(f"Unseen scene: {entry['instruction']}")
    axes[0].axis("off")
    axes[1].plot(np.arange(len(actions)), actions[:, 0], label="predicted pan")
    axes[1].plot(np.arange(len(actions)), actions[:, 1], label="predicted tilt")
    axes[1].axhline(entry["target_angles"][0], linestyle="--", alpha=0.6, label="target pan")
    axes[1].axhline(entry["target_angles"][1], linestyle=":", alpha=0.75, label="target tilt")
    axes[1].set(xlabel="Action chunk step", ylabel="Angle (degrees)", title="Predicted 2-axis action")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULT_ROOT / "unseen_action_timeseries.png", dpi=160)
    plt.close(fig)
    image.save(RESULT_ROOT / "unseen_scene_example.png")


def _save_drive(checkpoint_dir):
    from google.colab import drive

    if not (Path("/content/drive") / "MyDrive").exists():
        print("Mounting the requested Google Drive destination.")
        drive.mount("/content/drive")
    DRIVE_ROOT.mkdir(parents=True, exist_ok=True)
    target_checkpoint = DRIVE_ROOT / "smolvla_two_axis_checkpoint"
    shutil.rmtree(target_checkpoint, ignore_errors=True)
    shutil.copytree(checkpoint_dir, target_checkpoint)
    for path in RESULT_ROOT.iterdir():
        if path.is_file():
            shutil.copy2(path, DRIVE_ROOT / path.name)
    for name in ("overfit_training.log", "full_training.log"):
        path = RESULT_ROOT / name
        if path.exists():
            shutil.copy2(path, DRIVE_ROOT / path.name)
    print(f"Drive artifacts saved to: {DRIVE_ROOT}")
    print(f"Checkpoint: {target_checkpoint}")


def run_stage2(ns):
    _ensure_dependencies()
    print("Python:", sys.version.split()[0])
    print("LeRobot:", importlib.metadata.version("lerobot"))
    assert torch.cuda.is_available(), "Attach a Colab GPU runtime first."
    gpu_name = torch.cuda.get_device_name(0)
    print("GPU:", gpu_name, "CUDA autocast dtype:", torch.get_autocast_dtype("cuda"))
    print("Native BF16 support reported by PyTorch:", torch.cuda.is_bf16_supported())
    print("Training precision policy: FP16 autocast with FP32 master weights.")
    ROOT.mkdir(parents=True, exist_ok=True)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    policy = _load_or_reuse_policy(ns)
    ns["policy"] = policy
    assert tuple(policy.config.robot_state_feature.shape) == (2,)
    assert tuple(policy.config.action_feature.shape) == (2,)
    base_path = ROOT / "base_2axis"
    if not (base_path / "config.json").exists() or not list(base_path.glob("*.safetensors")):
        shutil.rmtree(base_path, ignore_errors=True)
        policy.save_pretrained(base_path)
        print("Saved shape-aligned base checkpoint:", base_path)
    else:
        print("Reusing saved shape-aligned base checkpoint:", base_path)

    # Small-data overfit test first; this is a training-pipeline check, not the final score.
    overfit_root, overfit_manifest_path, overfit_manifest = build_dataset("overfit", OVERFIT_SCENES, 20261016)
    overfit_ds = inspect_dataset(
        "local/pointer_stage2_overfit", overfit_root, OVERFIT_SCENES,
        OVERFIT_SCENES * 2 * EPISODE_STEPS, overfit_manifest
    )
    overfit_run = run_official_training(
        policy, "local/pointer_stage2_overfit", overfit_root, OVERFIT_STEPS, OUTPUT_ROOT / "overfit", "overfit"
    )
    from lerobot.policies.factory import make_pre_post_processors

    overfit_pre, overfit_post = make_pre_post_processors(policy.config, dataset_stats=overfit_ds.meta.stats)
    overfit_rows, _, _ = _evaluate_manifest(
        policy, overfit_pre, overfit_post, overfit_ds, overfit_manifest, "overfit"
    )
    overfit_metrics = _metric_summary(overfit_rows)
    print("OVERFIT_EVAL:", json.dumps(overfit_metrics, ensure_ascii=False))
    _write_csv(RESULT_ROOT / "overfit_evaluation.csv", overfit_rows)

    # Reset to the untouched base weights before training on the independent train split.
    del policy
    ns["policy"] = None
    gc.collect()
    torch.cuda.empty_cache()
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

    policy = SmolVLAPolicy.from_pretrained(base_path).to("cuda").eval()
    ns["policy"] = policy
    assert tuple(policy.config.robot_state_feature.shape) == (2,)
    assert tuple(policy.config.action_feature.shape) == (2,)

    train_root, train_manifest_path, train_manifest = build_dataset("train", TRAIN_SCENES, 20261017)
    val_root, val_manifest_path, val_manifest = build_dataset("val", VAL_SCENES, 20261018)
    test_root, test_manifest_path, test_manifest = build_dataset("test", TEST_SCENES, 20261019)
    train_hashes = {x["image_sha256"] for x in train_manifest["scenes"]}
    val_hashes = {x["image_sha256"] for x in val_manifest["scenes"]}
    test_hashes = {x["image_sha256"] for x in test_manifest["scenes"]}
    assert not (train_hashes & val_hashes or train_hashes & test_hashes or val_hashes & test_hashes)
    assert len(train_manifest["episodes"]) == 200
    assert len(val_manifest["episodes"]) == 20
    assert len(test_manifest["episodes"]) == 60
    for scene in train_manifest["scenes"] + val_manifest["scenes"] + test_manifest["scenes"]:
        red = np.asarray(target_to_angles(*scene["red_xy"]))
        blue = np.asarray(target_to_angles(*scene["blue_xy"]))
        assert np.linalg.norm(red - blue) > 6.0
    for manifest in (train_manifest, val_manifest, test_manifest):
        pairs = {}
        for episode in manifest["episodes"]:
            pairs.setdefault(episode["scene_id"], []).append(episode)
        assert len(pairs) == len(manifest["scenes"])
        for pair in pairs.values():
            assert {episode["color"] for episode in pair} == {"red", "blue"}
            assert pair[0]["image_sha256"] == pair[1]["image_sha256"]
            assert np.allclose(pair[0]["start_state"], pair[1]["start_state"])
            assert np.linalg.norm(np.asarray(pair[0]["target_angles"]) - pair[1]["target_angles"]) > 6.0
    print("PASS: split hashes are disjoint; paired image episodes have distinct color targets.")

    train_ds = inspect_dataset(
        "local/pointer_stage2_train", train_root, TRAIN_SCENES,
        TRAIN_SCENES * 2 * EPISODE_STEPS, train_manifest
    )
    val_ds = inspect_dataset(
        "local/pointer_stage2_val", val_root, VAL_SCENES,
        VAL_SCENES * 2 * EPISODE_STEPS, val_manifest
    )
    test_ds = inspect_dataset(
        "local/pointer_stage2_test", test_root, TEST_SCENES,
        TEST_SCENES * 2 * EPISODE_STEPS, test_manifest
    )

    from lerobot.policies.factory import make_pre_post_processors

    training_runs = []
    checkpoint_path = None

    def load_checkpoint(checkpoint):
        nonlocal policy
        del policy
        ns["policy"] = None
        gc.collect()
        torch.cuda.empty_cache()
        policy = SmolVLAPolicy.from_pretrained(checkpoint).to(device="cuda", dtype=torch.float16).eval()
        assert next(policy.parameters()).dtype == torch.float16
        ns["policy"] = policy
        assert tuple(policy.config.robot_state_feature.shape) == (2,)
        assert tuple(policy.config.action_feature.shape) == (2,)
        preprocess_local, postprocess_local = make_pre_post_processors(
            policy.config, pretrained_path=checkpoint, dataset_stats=train_ds.meta.stats
        )
        return preprocess_local, postprocess_local

    def evaluate_validation(label):
        preprocess_local, postprocess_local = make_pre_post_processors(
            policy.config, pretrained_path=checkpoint_path, dataset_stats=train_ds.meta.stats
        )
        rows, _, _ = _evaluate_manifest(
            policy, preprocess_local, postprocess_local, val_ds, val_manifest, label
        )
        _write_csv(RESULT_ROOT / f"{label}_evaluation.csv", rows)
        return _metric_summary(rows)

    # Train and validate in stages. Each extension starts from the previous saved
    # weights with a fresh optimizer; the validation set never enters training.
    stage_plan = [(300, "full_300"), (700, "full_to_1000"), (2000, "full_to_3000")]
    val_metrics = None
    for stage_index, (steps, label) in enumerate(stage_plan):
        run = run_official_training(
            policy,
            "local/pointer_stage2_train",
            train_root,
            steps,
            OUTPUT_ROOT / label,
            label,
        )
        training_runs.append(run)
        checkpoint_path = run["checkpoint"]
        preprocess, postprocess = load_checkpoint(checkpoint_path)
        val_metrics = evaluate_validation(f"validation_{label}")
        total_steps = sum(item["steps"] for item in training_runs)
        print(f"VALIDATION after {label} ({total_steps} optimizer steps):", json.dumps(val_metrics, ensure_ascii=False))
        if val_metrics["success_rate"] >= 0.80:
            print(f"Validation reached the provisional 80% goal after {total_steps} steps; stopping the schedule.")
            break
        if stage_index == len(stage_plan) - 1:
            print("Validation remains below 80% at the 3,000-step ceiling.")

    assert checkpoint_path is not None
    preprocess, postprocess = load_checkpoint(checkpoint_path)
    assert policy.config.train_expert_only is True
    print("PASS: trained 2-axis checkpoint reloaded; dtype:", next(policy.parameters()).dtype)
    tokenizer = policy.vlm_with_expert.processor.tokenizer
    japanese_ids = tokenizer.encode("赤い丸を指して")
    assert len(japanese_ids) > 2, japanese_ids
    print("Japanese tokenizer check:", len(japanese_ids), "tokens", japanese_ids)

    # Final validation uses independent scenes and training-only normalization statistics.
    val_rows, _, _ = _evaluate_manifest(policy, preprocess, postprocess, val_ds, val_manifest, "validation")
    val_metrics = _metric_summary(val_rows)
    _write_csv(RESULT_ROOT / "validation_evaluation.csv", val_rows)
    print("FINAL_VALIDATION:", json.dumps(val_metrics, ensure_ascii=False))

    # Final unseen-placement benchmark: each of 60 independent test episodes is sampled by episode_index.
    test_rows, by_scene, example = _evaluate_manifest(
        policy, preprocess, postprocess, test_ds, test_manifest, "unseen_test"
    )
    print("UNSEEN_TEST:", json.dumps(_metric_summary(test_rows), ensure_ascii=False))
    by_color = {
        color: _metric_summary([row for row in test_rows if row["color"] == color])
        for color in ("red", "blue")
    }

    # A: same image and start state, switch only the Japanese instruction.
    paired_separations = []
    for color_pair in by_scene.values():
        if {"red", "blue"} <= set(color_pair):
            red_actions = color_pair["red"][2]
            blue_actions = color_pair["blue"][2]
            paired_separations.append(float(np.linalg.norm(red_actions[-1] - blue_actions[-1])))
    language_pair = {
        "paired_scenes": len(paired_separations),
        "mean_final_separation_deg": float(np.mean(paired_separations)),
        "pairs_separated_by_gt_6deg_rate": float(np.mean(np.asarray(paired_separations) > 6.0)),
    }

    # B: swap the two colored targets in each unseen image; the language stays fixed.
    swap_rows = []
    for scene in test_manifest["scenes"]:
        swapped_image = create_scene(scene["blue_xy"], scene["red_xy"])
        for color_name, instruction, target_xy in (
            ("red", "赤い丸を指して", scene["blue_xy"]),
            ("blue", "青い丸を指して", scene["red_xy"]),
        ):
            target = target_to_angles(*target_xy)
            state = np.asarray(scene["shared_start_state"], dtype=np.float32)
            actions = _predict_chunk(policy, preprocess, postprocess, swapped_image, instruction, state)
            entry = {"scene_id": scene["scene_id"], "color": color_name, "episode_index": -1}
            swap_rows.append(_eval_record("swapped_image", entry, instruction, target, state, actions))
    swap_metrics = _metric_summary(swap_rows)

    # C: move the initial joint state while holding pixels and instruction fixed.
    state_rows = []
    alternate_states = ([75.0, 105.0], [105.0, 75.0])
    for scene in test_manifest["scenes"]:
        for color_name, instruction, target_xy in (
            ("red", "赤い丸を指して", scene["red_xy"]),
            ("blue", "青い丸を指して", scene["blue_xy"]),
        ):
            target = target_to_angles(*target_xy)
            image = Image.open(scene["image_path"]).convert("RGB")
            for state_index, state in enumerate(alternate_states):
                state = np.asarray(state, dtype=np.float32)
                actions = _predict_chunk(policy, preprocess, postprocess, image, instruction, state)
                entry = {
                    "scene_id": scene["scene_id"],
                    "color": color_name,
                    "episode_index": -1,
                }
                state_rows.append(
                    _eval_record(f"changed_start_{state_index + 1}", entry, instruction, target, state, actions)
                )
    state_metrics = _metric_summary(state_rows)

    # D: unseen Japanese paraphrases; target labels come from the manifest, never the prediction.
    paraphrases = {
        "red": ["赤の目標に向けて", "赤い方を指し示して", "赤色の丸を狙って"],
        "blue": ["青の目標に向けて", "青い方を指し示して", "青色の丸を狙って"],
    }
    paraphrase_rows = []
    for scene in test_manifest["scenes"]:
        image = Image.open(scene["image_path"]).convert("RGB")
        state = np.asarray(scene["shared_start_state"], dtype=np.float32)
        for color_name, target_xy in (("red", scene["red_xy"]), ("blue", scene["blue_xy"])):
            target = target_to_angles(*target_xy)
            for phrase_index, instruction in enumerate(paraphrases[color_name]):
                actions = _predict_chunk(
                    policy, preprocess, postprocess, image, instruction, state, seed=123 + phrase_index
                )
                entry = {
                    "scene_id": scene["scene_id"],
                    "color": color_name,
                    "episode_index": -1,
                }
                paraphrase_rows.append(
                    _eval_record("unseen_japanese_paraphrase", entry, instruction, target, state, actions)
                )
    paraphrase_metrics = _metric_summary(paraphrase_rows)
    paraphrase_by_color = {
        color: _metric_summary([row for row in paraphrase_rows if row["color"] == color])
        for color in ("red", "blue")
    }

    # E: remove either visual evidence or the task distinction; inference remains SmolVLA-only.
    blank = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (235, 236, 230))
    image_ablation_rows = []
    language_ablation_rows = []
    for entry, sample in _dataset_episode_samples(test_ds, test_manifest):
        state = np.asarray(sample["observation.state"].detach().cpu(), dtype=np.float32)
        image = _sample_image_to_pil(sample["observation.images.front"])
        target = entry["target_angles"]
        no_image_actions = _predict_chunk(policy, preprocess, postprocess, blank, entry["instruction"], state)
        image_ablation_rows.append(
            _eval_record("blank_image", entry, entry["instruction"], target, state, no_image_actions)
        )
        no_task_actions = _predict_chunk(policy, preprocess, postprocess, image, "丸を指して", state)
        language_ablation_rows.append(
            _eval_record("generic_language", entry, "丸を指して", target, state, no_task_actions)
        )
    image_ablation_metrics = _metric_summary(image_ablation_rows)
    language_ablation_metrics = _metric_summary(language_ablation_rows)

    # Report warm model latency separately from loading and warm-up.
    latency_image = example[0]
    latency_instruction = example[2]["instruction"]
    latency_state = np.asarray(example[2]["start_state"], dtype=np.float32)
    for _ in range(3):
        _predict_chunk(policy, preprocess, postprocess, latency_image, latency_instruction, latency_state)
    timings = []
    for _ in range(30):
        torch.cuda.synchronize()
        started = time.perf_counter()
        _predict_chunk(policy, preprocess, postprocess, latency_image, latency_instruction, latency_state)
        torch.cuda.synchronize()
        timings.append(time.perf_counter() - started)
    latency = {
        "calls": len(timings),
        "warmup_calls_excluded": 3,
        "median_seconds_per_50x2_chunk": float(np.median(timings)),
        "p95_seconds_per_50x2_chunk": float(np.percentile(timings, 95)),
        "mean_seconds_per_50x2_chunk": float(np.mean(timings)),
    }

    all_rows = (
        test_rows
        + swap_rows
        + state_rows
        + paraphrase_rows
        + image_ablation_rows
        + language_ablation_rows
    )
    _write_csv(RESULT_ROOT / "evaluation_results.csv", all_rows)
    loss_rows = _parse_losses([overfit_run["log_path"]] + [run["log_path"] for run in training_runs])
    _write_csv(RESULT_ROOT / "training_loss.csv", loss_rows)
    _save_plots(loss_rows, example)

    report = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lerobot_version": importlib.metadata.version("lerobot"),
        "model": MODEL_ID,
        "gpu": gpu_name,
        "cuda_autocast_dtype": str(torch.get_autocast_dtype("cuda")),
        "native_bf16_supported_reported": bool(torch.cuda.is_bf16_supported()),
        "training_precision": "fp16 autocast, fp32 master weights",
        "features": {"observation.state": [2], "action": [2], "image": [3, IMAGE_SIZE, IMAGE_SIZE]},
        "training": {
            "small_overfit": {**overfit_run, "checkpoint": str(overfit_run["checkpoint"])},
            "full_stages": [
                {**run, "checkpoint": str(run["checkpoint"])} for run in training_runs
            ],
            "total_full_steps": sum(run["steps"] for run in training_runs),
            "train_expert_only": bool(policy.config.train_expert_only),
            "freeze_vision_encoder": bool(policy.config.freeze_vision_encoder),
            "trainable_parameters": int(sum(p.numel() for p in policy.parameters() if p.requires_grad)),
            "total_parameters": int(sum(p.numel() for p in policy.parameters())),
            "overfit_evaluation": overfit_metrics,
        },
        "data": {
            "train_scenes": TRAIN_SCENES,
            "train_episodes": len(train_manifest["episodes"]),
            "train_frames": len(train_ds),
            "validation_scenes": VAL_SCENES,
            "validation_episodes": len(val_manifest["episodes"]),
            "test_scenes": TEST_SCENES,
            "test_episodes": len(test_manifest["episodes"]),
            "test_frames": len(test_ds),
            "fps": FPS,
            "episode_steps": EPISODE_STEPS,
            "split_scene_hashes_disjoint": True,
            "stats_from_training_split_only_for_policy": True,
        },
        "validation": val_metrics,
        "unseen_test": _metric_summary(test_rows),
        "unseen_test_by_color": by_color,
        "same_image_instruction_switch": language_pair,
        "swapped_color_positions_same_instruction": swap_metrics,
        "changed_start_state": state_metrics,
        "unseen_japanese_paraphrases": paraphrase_metrics,
        "unseen_japanese_paraphrases_by_color": paraphrase_by_color,
        "input_ablation": {
            "blank_image": image_ablation_metrics,
            "generic_instruction": language_ablation_metrics,
            "blank_image_mean_error_delta_from_baseline_deg": (
                image_ablation_metrics["mean_error_deg"] - _metric_summary(test_rows)["mean_error_deg"]
            ),
            "generic_instruction_mean_error_delta_from_baseline_deg": (
                language_ablation_metrics["mean_error_deg"] - _metric_summary(test_rows)["mean_error_deg"]
            ),
        },
        "gpu_inference_latency_after_checkpoint_load": latency,
        "success_threshold_note": (
            "6 degrees is a provisional synthetic-scene threshold and does not represent physical robot accuracy."
        ),
        "inference_has_no_color_detector_or_geometry_controller": True,
        "teacher_geometry_used_only_for_labels": True,
        "japanese_tokenization": {
            "instruction": "赤い丸を指して",
            "token_count": len(japanese_ids),
            "token_ids": [int(x) for x in japanese_ids],
        },
        "checkpoint_path_colab": str(checkpoint_path),
    }
    (RESULT_ROOT / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    (RESULT_ROOT / "train_manifest.json").write_text(
        json.dumps(train_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULT_ROOT / "validation_manifest.json").write_text(
        json.dumps(val_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULT_ROOT / "test_manifest.json").write_text(
        json.dumps(test_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("STAGE2_REPORT:", json.dumps(report, ensure_ascii=False, indent=2, default=str))

    # The checkpoint and requested evaluation artifacts are copied to a new Drive folder.
    _save_drive(checkpoint_path)
    print("STAGE2_DONE: metrics, CSV, plots, logs, and trained checkpoint were saved.")


_ensure_dependencies()
run_stage2(globals())
