"""Reusable deterministic data, policy, training, and artifact helpers for Stage 3.

Synthetic geometry is used only to create teacher labels. Inference consumes only
the rendered image, Japanese task text, and the current two-joint state.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import shutil
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

ROOT = Path("/content/stage3")
DATA_ROOT = ROOT / "data"
ASSET_ROOT = ROOT / "assets"
EXPERIMENT_ROOT = ROOT / "experiments"
RESULT_ROOT = ROOT / "results"
FPS = 10
EPISODE_STEPS = 50
IMAGE_SIZE = 96
SUCCESS_THRESHOLD_DEG = 6.0
FEATURES = {
    "observation.state": {"dtype": "float32", "shape": (2,), "names": ["pan", "tilt"]},
    "action": {"dtype": "float32", "shape": (2,), "names": ["pan", "tilt"]},
    "observation.images.front": {
        "dtype": "video", "shape": (IMAGE_SIZE, IMAGE_SIZE, 3),
        "names": ["height", "width", "channels"],
    },
}

TRAIN_PHRASES = {
    "red": ("赤い丸を指して", "赤の目標に向けて", "赤い方を指し示して"),
    "blue": ("青い丸を指して", "青色の丸を狙って", "青い方を指し示して"),
}


def target_to_angles(x: float, y: float) -> np.ndarray:
    """Teacher-only pinhole mapping for the synthetic 96x96 scene."""
    return np.asarray([
        90.0 + (float(x) / 95.0 - 0.5) * 85.0,
        90.0 - (float(y) / 95.0 - 0.5) * 65.0,
    ], dtype=np.float32)


def create_scene(red, blue, *, rng=None, background=(235, 236, 230), radii=(7, 7)):
    """Render one paired red/blue scene; all randomness is explicit."""
    image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), tuple(int(x) for x in background))
    draw = ImageDraw.Draw(image)
    palette = ((235, 64, 64), (53, 96, 237))
    for (x, y), color, radius in zip((red, blue), palette, radii):
        draw.ellipse((int(x)-radius, int(y)-radius, int(x)+radius, int(y)+radius), fill=color)
    return image


def _random_scene(rng):
    while True:
        red = tuple(int(v) for v in rng.integers(14, 82, size=2))
        blue = tuple(int(v) for v in rng.integers(14, 82, size=2))
        if np.linalg.norm(np.asarray(red) - np.asarray(blue)) >= 25:
            return red, blue


def _manifest(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_manifest(path, payload):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _stage2_scene(red, blue):
    image = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (235, 236, 230))
    draw = ImageDraw.Draw(image)
    for (x, y), color in ((red, (235, 64, 64)), (blue, (53, 96, 237))):
        draw.ellipse((x-7, y-7, x+7, y+7), fill=color)
    return image


def build_stage2_compatible_dataset(split: str, scene_count: int, seed: int):
    """Re-create the exact Stage 2 scene/data protocol under the Stage 3 root."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    root = DATA_ROOT / "stage2_compat" / split
    assets = ASSET_ROOT / "stage2_compat" / split
    manifest_path = DATA_ROOT / "stage2_compat" / f"{split}_manifest.json"
    if root.exists() and manifest_path.exists() and (root / "meta" / "info.json").exists():
        m = _manifest(manifest_path)
        if len(m["scenes"]) == scene_count and m["seed"] == seed:
            return root, manifest_path, m
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True, exist_ok=True)
    ds = LeRobotDataset.create(
        repo_id=f"local/stage3_stage2_{split}", root=root, fps=FPS, features=FEATURES,
        robot_type="pico_pan_tilt", use_videos=True, image_writer_threads=2,
        batch_encoding_size=1,
    )
    rng = np.random.default_rng(seed)
    m = {"split": split, "seed": seed, "fps": FPS, "episode_steps": EPISODE_STEPS, "scenes": [], "episodes": []}
    for si in range(scene_count):
        while True:
            red = tuple(int(v) for v in rng.integers(15, 81, size=2))
            blue = tuple(int(v) for v in rng.integers(15, 81, size=2))
            if np.linalg.norm(np.asarray(red)-np.asarray(blue)) >= 24:
                break
        image = _stage2_scene(red, blue)
        scene_id = f"{split}_{si:04d}"
        image_path = assets / f"{scene_id}.png"
        image.save(image_path)
        image_hash = hashlib.sha256(np.asarray(image).tobytes()).hexdigest()
        start = rng.uniform([75.0, 75.0], [105.0, 105.0]).astype(np.float32)
        m["scenes"].append({"scene_id": scene_id, "image_path": str(image_path), "image_sha256": image_hash,
                            "red_xy": list(red), "blue_xy": list(blue), "shared_start_state": start.astype(float).tolist()})
        for color, phrase, target_xy in (("red", "赤い丸を指して", red), ("blue", "青い丸を指して", blue)):
            goal = target_to_angles(*target_xy)
            state = start.copy()
            episode_index = len(m["episodes"])
            for step in range(EPISODE_STEPS):
                u = (step+1)/EPISODE_STEPS
                smooth = u*u*(3-2*u)
                action = (start+(goal-start)*smooth).astype(np.float32)
                ds.add_frame({"observation.state": state.copy(), "action": action.copy(),
                              "observation.images.front": np.asarray(image, dtype=np.uint8).copy(), "task": phrase})
                state = action.copy()
            ds.save_episode()
            m["episodes"].append({"episode_index": episode_index, "scene_id": scene_id, "color": color,
                                  "instruction": phrase, "image_path": str(image_path), "image_sha256": image_hash,
                                  "target_xy": list(target_xy), "target_angles": goal.astype(float).tolist(),
                                  "start_state": start.astype(float).tolist()})
    ds.finalize()
    _write_manifest(manifest_path, m)
    inspect_dataset(f"local/stage3_stage2_{split}", root, scene_count, scene_count*2*EPISODE_STEPS, m)
    return root, manifest_path, m


def build_dataset(split: str, scene_count: int, seed: int, *, canonical: bool = False):
    """Build varied Stage 3 scenes; each frame stores an absolute angle target."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    root = DATA_ROOT / split
    assets = ASSET_ROOT / split
    manifest_path = DATA_ROOT / f"{split}_manifest.json"
    if root.exists() and manifest_path.exists() and (root / "meta" / "info.json").exists():
        m = _manifest(manifest_path)
        if len(m["scenes"]) == scene_count and m["seed"] == seed and m.get("generator") == "stage3_augmented_v1":
            return root, manifest_path, m
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(assets, ignore_errors=True)
    assets.mkdir(parents=True, exist_ok=True)
    ds = LeRobotDataset.create(
        repo_id=f"local/stage3_{split}", root=root, fps=FPS, features=FEATURES,
        robot_type="pico_pan_tilt", use_videos=True, image_writer_threads=2,
        batch_encoding_size=1,
    )
    rng = np.random.default_rng(seed)
    m = {"generator": "stage3_augmented_v1", "split": split, "seed": seed, "fps": FPS,
         "episode_steps": EPISODE_STEPS, "scenes": [], "episodes": []}
    for si in range(scene_count):
        red, blue = _random_scene(rng)
        brightness = int(rng.integers(-9, 10))
        tint = rng.integers(-3, 4, size=3)
        background = tuple(int(np.clip(v+brightness+int(t), 218, 247)) for v, t in zip((235, 236, 230), tint))
        radii = tuple(int(rng.integers(5, 10)) for _ in range(2))
        image = create_scene(red, blue, background=background, radii=radii)
        scene_id = f"stage3_{split}_{si:04d}"
        image_path = assets / f"{scene_id}.png"
        image.save(image_path)
        image_hash = hashlib.sha256(np.asarray(image).tobytes()).hexdigest()
        # Starts vary independently by command so the policy must use observed state.
        scene_entry = {"scene_id": scene_id, "image_path": str(image_path), "image_sha256": image_hash,
                       "red_xy": list(red), "blue_xy": list(blue), "background_rgb": list(background),
                       "radii": list(radii)}
        m["scenes"].append(scene_entry)
        for color, target_xy in (("red", red), ("blue", blue)):
            start = rng.uniform([68.0, 70.0], [112.0, 110.0]).astype(np.float32)
            phrases = TRAIN_PHRASES[color]
            phrase = f"{'赤' if color == 'red' else '青'}い丸を指して" if canonical else phrases[si % len(phrases)]
            goal = target_to_angles(*target_xy)
            state = start.copy()
            episode_index = len(m["episodes"])
            for step in range(EPISODE_STEPS):
                u = (step+1)/EPISODE_STEPS
                smooth = u*u*(3-2*u)
                action = (start+(goal-start)*smooth).astype(np.float32)
                ds.add_frame({"observation.state": state.copy(), "action": action.copy(),
                              "observation.images.front": np.asarray(image, dtype=np.uint8).copy(), "task": phrase})
                state = action.copy()
            ds.save_episode()
            m["episodes"].append({"episode_index": episode_index, "scene_id": scene_id, "color": color,
                                  "instruction": phrase, "image_path": str(image_path), "image_sha256": image_hash,
                                  "target_xy": list(target_xy), "target_angles": goal.astype(float).tolist(),
                                  "start_state": start.astype(float).tolist(), "background_rgb": list(background),
                                  "radii": list(radii)})
        if (si+1) % 25 == 0 or si+1 == scene_count:
            print(f"{split}: generated {si+1}/{scene_count} paired scenes")
    ds.finalize()
    _write_manifest(manifest_path, m)
    inspect_dataset(f"local/stage3_{split}", root, scene_count, scene_count*2*EPISODE_STEPS, m)
    return root, manifest_path, m


def inspect_dataset(repo_id, root, expected_scenes, expected_frames, manifest):
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    ds = LeRobotDataset(repo_id=repo_id, root=root)
    assert len(ds) == expected_frames, (len(ds), expected_frames)
    assert len(set(int(x) for x in ds.hf_dataset["episode_index"])) == expected_scenes*2
    assert tuple(ds.meta.features["observation.state"]["shape"]) == (2,)
    assert tuple(ds.meta.features["action"]["shape"]) == (2,)
    assert int(ds.meta.info["fps"]) == FPS
    assert set(("observation.state", "action")) <= set(ds.meta.stats)
    episodes = np.asarray(ds.hf_dataset["episode_index"], dtype=np.int64)
    states = np.asarray(ds.hf_dataset["observation.state"], dtype=np.float32)
    actions = np.asarray(ds.hf_dataset["action"], dtype=np.float32)
    for e in manifest["episodes"]:
        idx = np.flatnonzero(episodes == int(e["episode_index"]))
        assert len(idx) == EPISODE_STEPS
        assert np.allclose(states[idx[0]], e["start_state"], atol=1e-4)
        assert np.allclose(actions[idx[-1]], e["target_angles"], atol=1e-4)
        assert np.allclose(states[idx[1:]], actions[idx[:-1]], atol=1e-4)
    return ds


def episode_samples(dataset, manifest):
    episode_ids = np.asarray(dataset.hf_dataset["episode_index"], dtype=np.int64)
    out = []
    for entry in manifest["episodes"]:
        idx = np.flatnonzero(episode_ids == int(entry["episode_index"]))
        assert len(idx) == EPISODE_STEPS
        sample = dataset[int(idx[0])]
        assert np.allclose(sample["observation.state"].detach().cpu().numpy(), entry["start_state"], atol=1e-4)
        out.append((entry, sample, idx))
    return out


def sample_image_to_pil(value):
    arr = value.detach().cpu().numpy() if torch.is_tensor(value) else np.asarray(value)
    if arr.ndim == 3 and arr.shape[0] in (1, 3, 4): arr = arr.transpose(1, 2, 0)
    if np.issubdtype(arr.dtype, np.floating):
        if arr.size and np.nanmax(arr) <= 1.5: arr = arr * 255.0
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.shape[-1] == 1: arr = np.repeat(arr, 3, axis=-1)
    return Image.fromarray(arr[..., :3], mode="RGB")


def make_policy(checkpoint, *, train_expert_only=True, freeze_vision_encoder=True, learning_rate=1e-5):
    from lerobot.configs.types import FeatureType, PolicyFeature
    from lerobot.policies.smolvla.configuration_smolvla import SmolVLAConfig
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    cfg = SmolVLAConfig.from_pretrained(str(checkpoint))
    cfg.device = "cuda"
    cfg.use_amp = True
    cfg.train_expert_only = bool(train_expert_only)
    cfg.freeze_vision_encoder = bool(freeze_vision_encoder)
    cfg.optimizer_lr = float(learning_rate)
    cfg.input_features = {
        "observation.state": PolicyFeature(type=FeatureType.STATE, shape=(2,)),
        "observation.images.front": PolicyFeature(type=FeatureType.VISUAL, shape=(3, IMAGE_SIZE, IMAGE_SIZE)),
    }
    cfg.output_features = {"action": PolicyFeature(type=FeatureType.ACTION, shape=(2,))}
    cfg.chunk_size = EPISODE_STEPS
    cfg.n_action_steps = EPISODE_STEPS
    policy = SmolVLAPolicy.from_pretrained(str(checkpoint), config=cfg)
    assert tuple(policy.config.robot_state_feature.shape) == (2,)
    assert tuple(policy.config.action_feature.shape) == (2,)
    return policy.to(device="cuda", dtype=torch.float32)


def audit_trainable_parameters(model, *, require_vlm=False):
    total = trainable = 0
    names = []
    groups = {}
    for name, param in model.named_parameters():
        total += param.numel()
        if param.requires_grad:
            trainable += param.numel()
            names.append(name)
            group = "vlm" if ".vlm." in name or name.startswith("vlm.") else ("vision" if "vision_model" in name else "policy_or_expert")
            groups[group] = groups.get(group, 0) + param.numel()
    if require_vlm:
        vlm_trainable = [n for n, p in model.named_parameters() if p.requires_grad and ".vlm." in n]
        assert vlm_trainable, "VLM text side has no trainable parameters; this is not a language-path experiment"
        assert not any("vision_model" in n for n in names), "Vision encoder was meant to be frozen"
    return {"total_parameters": total, "trainable_parameters": trainable, "trainable_ratio": trainable/total,
            "trainable_groups": groups, "trainable_names": names}


class _Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, value):
        for s in self.streams: s.write(value); s.flush()
        return len(value)
    def flush(self):
        for s in self.streams: s.flush()


def train_variant(name, checkpoint_path, dataset_root, repo_id, steps, *, train_expert_only,
                  freeze_vision_encoder, learning_rate, output_root, batch_size=2, save_freq=None):
    """LeRobot official train pipeline. Weights initialize from checkpoint; optimizer is new."""
    from lerobot.configs.default import DatasetConfig
    from lerobot.configs.train import TrainPipelineConfig
    from lerobot.scripts import lerobot_train
    policy = make_policy(checkpoint_path, train_expert_only=train_expert_only,
                         freeze_vision_encoder=freeze_vision_encoder, learning_rate=learning_rate)
    audit = audit_trainable_parameters(policy, require_vlm=not train_expert_only)
    policy.train()
    output_root = Path(output_root)
    # LeRobot 0.6.1 refuses an existing output_dir when resume=False. Let the
    # official trainer create this leaf directory, while preserving any prior run.
    if output_root.exists():
        raise FileExistsError(f"Refusing to overwrite existing Stage3 output: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    cfg = TrainPipelineConfig(
        dataset=DatasetConfig(repo_id=repo_id, root=str(dataset_root), use_imagenet_stats=True),
        policy=policy.config, output_dir=output_root, job_name=f"stage3_{name}", seed=20261017,
        num_workers=0, persistent_workers=False, dataloader_multiprocessing_context=None,
        batch_size=batch_size, steps=steps, log_freq=10, save_freq=save_freq or steps,
        save_checkpoint=True, use_policy_training_preset=True,
    )
    cfg.wandb.enable = False
    cfg.policy.device = "cuda"
    cfg.policy.use_amp = True
    cfg.policy.train_expert_only = bool(train_expert_only)
    cfg.policy.freeze_vision_encoder = bool(freeze_vision_encoder)
    if hasattr(cfg.policy, "optimizer_lr"): cfg.policy.optimizer_lr = float(learning_rate)
    # 0.6.1's trainer may materialize the optimizer from the pipeline config.
    if hasattr(cfg, "optimizer") and hasattr(cfg.optimizer, "lr"): cfg.optimizer.lr = float(learning_rate)
    if hasattr(cfg, "scheduler"):
        if hasattr(cfg.scheduler, "num_warmup_steps"): cfg.scheduler.num_warmup_steps = min(100, steps//10)
        if hasattr(cfg.scheduler, "num_decay_steps"): cfg.scheduler.num_decay_steps = steps
    if hasattr(cfg.policy, "scheduler_warmup_steps"): cfg.policy.scheduler_warmup_steps = min(100, steps//10)
    if hasattr(cfg.policy, "scheduler_decay_steps"): cfg.policy.scheduler_decay_steps = steps
    if hasattr(cfg, "resume"): cfg.resume = False

    original_make_policy = lerobot_train.make_policy
    def reuse_policy(policy_cfg, ds_meta, **kwargs):
        assert tuple(policy_cfg.robot_state_feature.shape) == (2,)
        assert tuple(policy_cfg.action_feature.shape) == (2,)
        assert tuple(ds_meta.features["action"]["shape"]) == (2,)
        return policy
    lerobot_train.make_policy = reuse_policy
    log_path = ROOT / "results" / f"{name}_training.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    try:
        with log_path.open("w", encoding="utf-8") as log:
            tee = _Tee(sys.stdout, log)
            original_stderr = sys.stderr
            with redirect_stdout(tee), redirect_stderr(tee):
                print(f"STAGE3_TRAIN name={name} steps={steps} batch={batch_size} lr={learning_rate} "
                      f"expert_only={train_expert_only} vision_frozen={freeze_vision_encoder}")
                print("INITIALIZER_CHECKPOINT", str(checkpoint_path), "optimizer_state=RESET")
                print("AUDIT", json.dumps({k:v for k,v in audit.items() if k != "trainable_names"}))
                print("LR_AUDIT", "policy", getattr(cfg.policy, "optimizer_lr", None), "pipeline", getattr(getattr(cfg,"optimizer",None),"lr",None))
                lerobot_train.train(cfg)
                for h in logging.getLogger().handlers:
                    if getattr(h, "stream", None) is tee: h.setStream(original_stderr)
    finally:
        lerobot_train.make_policy = original_make_policy
    elapsed = time.perf_counter()-started
    candidates = [p for p in output_root.rglob("pretrained_model") if (p/"config.json").is_file()]
    assert candidates, f"No checkpoint saved under {output_root}"
    candidates.sort(key=lambda p: p.stat().st_mtime)
    result = {"name": name, "steps": steps, "seconds": elapsed, "gpu": torch.cuda.get_device_name(0),
              "peak_allocated_gib": torch.cuda.max_memory_allocated()/1024**3,
              "peak_reserved_gib": torch.cuda.max_memory_reserved()/1024**3,
              "trainable_parameters": audit["trainable_parameters"], "trainable_groups": audit["trainable_groups"],
              "trainable_names": audit["trainable_names"], "initializer_checkpoint": str(checkpoint_path),
              "optimizer_state": "reset (weights only loaded)", "learning_rate": learning_rate,
              "checkpoint": str(candidates[-1]), "log_path": str(log_path),
              "train_expert_only": train_expert_only, "freeze_vision_encoder": freeze_vision_encoder}
    return result


def load_processors(policy, checkpoint, train_stats):
    from lerobot.policies.factory import make_pre_post_processors
    return make_pre_post_processors(policy.config, pretrained_path=str(checkpoint), dataset_stats=train_stats)


def predict_chunk(policy, preprocess, postprocess, image, instruction, state, seed=123):
    image = image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE))
    pixels = torch.from_numpy(np.asarray(image, dtype=np.uint8).copy()).permute(2,0,1).float()/255.0
    obs = {"observation.images.front": pixels, "observation.state": torch.as_tensor(state,dtype=torch.float32), "task": instruction}
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    batch = preprocess(obs)
    with torch.inference_mode():
        pred = postprocess(policy.predict_action_chunk(batch))
    if isinstance(pred, dict): pred = pred.get("action", pred.get("actions"))
    if isinstance(pred, tuple): pred = pred[0]
    arr = torch.as_tensor(pred).detach().float().cpu().numpy()
    if arr.ndim == 3: arr = arr[0]
    assert arr.shape == (EPISODE_STEPS, 2), arr.shape
    assert np.isfinite(arr).all()
    return arr


def error_summary(rows, prediction_key="predicted_actions"):
    errors = np.asarray([r["error_deg"] for r in rows], dtype=np.float64)
    succ = errors <= SUCCESS_THRESHOLD_DEG
    return {"episodes": len(rows), "successes": int(succ.sum()), "success_rate": float(succ.mean()),
            "mean_error_deg": float(errors.mean()), "median_error_deg": float(np.median(errors)),
            "p95_error_deg": float(np.percentile(errors,95)), "threshold_deg": SUCCESS_THRESHOLD_DEG}


def scene_bootstrap_ci(rows, repeats=2000, seed=20261017):
    grouped = {}
    for row in rows: grouped.setdefault(row["scene_id"], []).append(bool(row["success"]))
    rates = np.asarray([np.mean(v) for v in grouped.values()], dtype=float)
    rng = np.random.default_rng(seed)
    samples = np.asarray([rng.choice(rates, size=len(rates), replace=True).mean() for _ in range(repeats)])
    return {"scene_count": len(rates), "success_rate": float(rates.mean()),
            "ci95_low": float(np.percentile(samples,2.5)), "ci95_high": float(np.percentile(samples,97.5))}


def write_csv(path, rows):
    if not rows: return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def parse_losses(log_paths):
    rows=[]
    for path in log_paths:
        for line in Path(path).read_text(encoding="utf-8",errors="replace").splitlines():
            lm=re.search(r"(?:loss|train_loss)\s*[:=]\s*(-?\d+(?:\.\d+)?(?:e[-+]?\d+)?)",line,re.I)
            sm=re.search(r"(?:step|steps)\s*[:=]\s*(\d+)",line,re.I)
            if lm: rows.append({"phase":Path(path).stem,"step":int(sm.group(1)) if sm else len(rows)+1,"loss":float(lm.group(1))})
    return rows
