"""Ideal-actuator closed-loop simulation for SmolVLA action chunks."""
from __future__ import annotations

import numpy as np
import torch

from stage3_helpers import episode_samples, load_processors, predict_chunk, sample_image_to_pil


def simulate_closed_loop(predict, image, instruction, initial_state, *, horizon=50,
                         execute_per_chunk=5, max_step_deg=6.0, limits=(30.0,150.0)):
    """Replan from the updated two-axis state using a fixed synthetic camera image."""
    state=np.asarray(initial_state,dtype=np.float32).copy()
    trajectory=[state.copy()]
    calls=0; velocity_clips=0; range_clips=0; proposed_steps=0
    while len(trajectory)-1 < horizon:
        actions=np.asarray(predict(image,instruction,state.copy()),dtype=np.float32)
        assert actions.shape==(50,2),actions.shape
        assert np.isfinite(actions).all()
        calls+=1
        count=min(execute_per_chunk,horizon-(len(trajectory)-1),len(actions))
        for proposed in actions[:count]:
            proposed_steps+=1
            if np.any((proposed<limits[0]) | (proposed>limits[1])): range_clips+=1
            step_limited=np.clip(proposed,state-max_step_deg,state+max_step_deg)
            if not np.allclose(step_limited,proposed): velocity_clips+=1
            actual=np.clip(step_limited,limits[0],limits[1]).astype(np.float32)
            trajectory.append(actual.copy())
            state=actual
    path=np.asarray(trajectory,dtype=np.float32)
    delta=np.diff(path,axis=0)
    jerk=np.diff(path,n=2,axis=0)
    return {"final_state":state,"trajectory":path,"prediction_calls":calls,
            "velocity_clip_fraction":velocity_clips/max(1,proposed_steps),
            "range_violation_fraction":range_clips/max(1,proposed_steps),
            "max_step_norm_deg":float(np.linalg.norm(delta,axis=1).max()) if len(delta) else 0.0,
            "mean_step_norm_deg":float(np.linalg.norm(delta,axis=1).mean()) if len(delta) else 0.0,
            "max_jerk_norm_deg":float(np.linalg.norm(jerk,axis=1).max()) if len(jerk) else 0.0}


def evaluate_closed_loop(checkpoint, dataset, manifest, train_stats, *, label="model", scene_limit=10):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    policy=SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda",dtype=torch.float32).eval()
    pre,post=load_processors(policy,checkpoint,train_stats)
    def predict(image,task,state): return predict_chunk(policy,pre,post,image,task,state,seed=123)
    grouped={}
    for entry,sample,_ in episode_samples(dataset,manifest):
        grouped.setdefault(entry["scene_id"],[]).append((entry,sample))
    rows=[]; trajectories={}
    for scene_id,pairs in list(grouped.items())[:scene_limit]:
        for entry,sample in pairs:
            image=sample_image_to_pil(sample["observation.images.front"])
            state=sample["observation.state"].detach().cpu().numpy().astype(np.float32)
            target=np.asarray(entry["target_angles"],dtype=np.float32)
            for horizon in (50,10,5):
                result=simulate_closed_loop(predict,image,entry["instruction"],state,
                                            horizon=50,execute_per_chunk=horizon,max_step_deg=6.0)
                error=float(np.linalg.norm(result["final_state"]-target))
                row={"model":label,"scene_id":scene_id,"color":entry["color"],"instruction":entry["instruction"],
                     "execute_per_chunk":horizon,"prediction_calls":result["prediction_calls"],
                     "final_error_deg":error,"success":error<=6.0,
                     "velocity_clip_fraction":result["velocity_clip_fraction"],
                     "range_violation_fraction":result["range_violation_fraction"],
                     "max_step_norm_deg":result["max_step_norm_deg"],"mean_step_norm_deg":result["mean_step_norm_deg"],
                     "max_jerk_norm_deg":result["max_jerk_norm_deg"],
                     "final_pan_deg":float(result["final_state"][0]),"final_tilt_deg":float(result["final_state"][1])}
                rows.append(row)
                trajectories[(scene_id,entry["color"],horizon)]={"target":target.tolist(),"trajectory":result["trajectory"].tolist()}
    del policy,pre,post
    torch.cuda.empty_cache()
    return rows,trajectories


if __name__ == "__main__":
    raise SystemExit("Use evaluate_closed_loop() from the Stage 3 Colab notebook.")
