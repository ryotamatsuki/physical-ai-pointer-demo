"""Experiment orchestration for Stage 3; safe to import (no training on import)."""
from __future__ import annotations

import json
from pathlib import Path

from stage3_helpers import ROOT, build_dataset, build_stage2_compatible_dataset, train_variant


def run_small_overfit(stage2_checkpoint, *, steps=1000, learning_rate=1e-4, batch_size=2):
    """Train on four fixed scenes and save intermediate checkpoints for memorization checks."""
    root,manifest_path,manifest=build_dataset("overfit",4,20261071,canonical=True)
    result=train_variant("overfit_4scenes",stage2_checkpoint,root,"local/stage3_overfit",steps,
                         train_expert_only=True,freeze_vision_encoder=True,learning_rate=learning_rate,
                         output_root=ROOT/"experiments"/"overfit",batch_size=batch_size,save_freq=250)
    result.update({"dataset_root":str(root),"manifest_path":str(manifest_path),"episodes":len(manifest["episodes"])})
    return result


def run_expert_continue(stage2_checkpoint, train_root, *, steps=2000, learning_rate=1e-5, batch_size=1):
    return train_variant("expert_continue",stage2_checkpoint,train_root,"local/stage3_train",steps,
                         train_expert_only=True,freeze_vision_encoder=True,learning_rate=learning_rate,
                         output_root=ROOT/"experiments"/"expert",batch_size=batch_size,save_freq=steps)


def run_vlm_adaptation(stage2_checkpoint, train_root, *, steps=2000, learning_rate=5e-6, batch_size=1):
    return train_variant("vlm_adaptation",stage2_checkpoint,train_root,"local/stage3_train",steps,
                         train_expert_only=False,freeze_vision_encoder=True,learning_rate=learning_rate,
                         output_root=ROOT/"experiments"/"vlm",batch_size=batch_size,save_freq=steps)


def run_data_generation():
    """Generate augmented train/validation/final-test data with scene-disjoint seeds."""
    train=build_dataset("train",200,20261031,canonical=False)
    validation=build_dataset("validation",30,20261032,canonical=True)
    final_test=build_dataset("final_test",60,20261033,canonical=True)
    def hashes(item): return {s["image_sha256"] for s in item[2]["scenes"]}
    assert hashes(train).isdisjoint(hashes(validation))
    assert hashes(train).isdisjoint(hashes(final_test))
    assert hashes(validation).isdisjoint(hashes(final_test))
    return {"train":train,"validation":validation,"final_test":final_test,
            "scene_hashes_disjoint":True}


if __name__ == "__main__":
    raise SystemExit("Open the Stage 3 Colab notebook and run cells in order; import is side-effect free.")
