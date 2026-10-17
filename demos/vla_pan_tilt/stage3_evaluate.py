"""Episode-level Stage 3 SmolVLA evaluation and counterfactual probes."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch

from stage3_helpers import (
    EPISODE_STEPS, SUCCESS_THRESHOLD_DEG, create_scene, episode_samples,
    error_summary, predict_chunk, sample_image_to_pil, scene_bootstrap_ci, target_to_angles,
)


def evaluate_checkpoint(checkpoint, dataset, manifest, train_stats, *, label="model", limit=None):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from stage3_helpers import load_processors
    policy = SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda", dtype=torch.float32).eval()
    preprocess, postprocess = load_processors(policy, checkpoint, train_stats)
    rows=[]
    for entry, sample, indices in episode_samples(dataset, manifest):
        image=sample_image_to_pil(sample["observation.images.front"])
        state=sample["observation.state"].detach().cpu().numpy().astype(np.float32)
        started=time.perf_counter()
        actions=predict_chunk(policy,preprocess,postprocess,image,entry["instruction"],state,seed=123)
        latency=time.perf_counter()-started
        target=np.asarray(entry["target_angles"],dtype=np.float64)
        errors=np.linalg.norm(actions-target[None,:],axis=1)
        teacher=np.asarray(dataset.hf_dataset["action"][indices],dtype=np.float32)
        rows.append({"model":label,"scene_id":entry["scene_id"],"episode_index":entry["episode_index"],
                     "color":entry["color"],"instruction":entry["instruction"],
                     "start_pan_deg":float(state[0]),"start_tilt_deg":float(state[1]),
                     "target_pan_deg":float(target[0]),"target_tilt_deg":float(target[1]),
                     "predicted_final_pan_deg":float(actions[-1,0]),"predicted_final_tilt_deg":float(actions[-1,1]),
                     "error_deg":float(errors[-1]),"success":bool(errors[-1]<=SUCCESS_THRESHOLD_DEG),
                     "error_t0_deg":float(errors[0]),"error_t25_deg":float(errors[24]),
                     "error_t49_deg":float(errors[49]),"trajectory_rmse_deg":float(np.sqrt(np.mean((actions-teacher)**2))),
                     "latency_seconds":latency,"image_sha256":entry["image_sha256"]})
        if limit is not None and len(rows)>=limit: break
    summary=error_summary(rows)
    summary["scene_bootstrap_95ci"]=scene_bootstrap_ci(rows)
    summary["red_success_rate"]=float(np.mean([r["success"] for r in rows if r["color"]=="red"]))
    summary["blue_success_rate"]=float(np.mean([r["success"] for r in rows if r["color"]=="blue"]))
    summary["mean_trajectory_rmse_deg"]=float(np.mean([r["trajectory_rmse_deg"] for r in rows]))
    summary["latency_median_seconds"]=float(np.median([r["latency_seconds"] for r in rows]))
    summary["latency_p95_seconds"]=float(np.percentile([r["latency_seconds"] for r in rows],95))
    del policy,preprocess,postprocess
    torch.cuda.empty_cache()
    return rows,summary


def evaluate_paraphrases(checkpoint, dataset, manifest, train_stats, *, label="model"):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from stage3_helpers import load_processors, TRAIN_PHRASES
    policy=SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda",dtype=torch.float32).eval()
    pre,post=load_processors(policy,checkpoint,train_stats)
    rows=[]
    for entry,sample,_ in episode_samples(dataset,manifest):
        color=entry["color"]
        scene=entry["scene_id"]
        phrase_list=TRAIN_PHRASES[color]
        image=sample_image_to_pil(sample["observation.images.front"])
        state=sample["observation.state"].detach().cpu().numpy()
        target=np.asarray(entry["target_angles"],dtype=float)
        for phrase in phrase_list:
            actions=predict_chunk(policy,pre,post,image,phrase,state,seed=123)
            err=float(np.linalg.norm(actions[-1]-target))
            rows.append({"model":label,"scene_id":scene,"color":color,"instruction":phrase,
                         "error_deg":err,"success":err<=SUCCESS_THRESHOLD_DEG})
    del policy,pre,post; torch.cuda.empty_cache()
    return rows,error_summary(rows)


def evaluate_input_ablation(checkpoint, dataset, manifest, train_stats, *, label="model", scene_limit=30):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from stage3_helpers import load_processors
    policy=SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda",dtype=torch.float32).eval()
    pre,post=load_processors(policy,checkpoint,train_stats)
    rows=[]
    seen=set()
    for entry,sample,_ in episode_samples(dataset,manifest):
        if entry["scene_id"] not in seen:
            if len(seen)>=scene_limit: break
            seen.add(entry["scene_id"])
        image=sample_image_to_pil(sample["observation.images.front"])
        state=sample["observation.state"].detach().cpu().numpy()
        target=np.asarray(entry["target_angles"],dtype=float)
        for condition,img,task in (("baseline",image,entry["instruction"]),
                                   ("blank_image",Image.new("RGB",image.size,(235,236,230)),entry["instruction"]),
                                   ("generic_instruction",image,"丸を指して")):
            actions=predict_chunk(policy,pre,post,img,task,state,seed=123)
            err=float(np.linalg.norm(actions[-1]-target))
            rows.append({"model":label,"condition":condition,"scene_id":entry["scene_id"],"color":entry["color"],
                         "error_deg":err,"success":err<=SUCCESS_THRESHOLD_DEG})
    summaries={}
    for cond in ("baseline","blank_image","generic_instruction"):
        subset=[r for r in rows if r["condition"]==cond]
        summaries[cond]=error_summary(subset)
    del policy,pre,post; torch.cuda.empty_cache()
    return rows,summaries


def evaluate_instruction_switch(checkpoint, dataset, manifest, train_stats, *, label="model", scene_limit=30):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from stage3_helpers import load_processors
    policy=SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda",dtype=torch.float32).eval()
    pre,post=load_processors(policy,checkpoint,train_stats)
    grouped={}
    for entry,sample,_ in episode_samples(dataset,manifest):
        grouped.setdefault(entry["scene_id"],{})[entry["color"]]=(entry,sample)
    rows=[]
    for scene_id,pair in list(grouped.items())[:scene_limit]:
        e1,s1=pair["red"]; e2,s2=pair["blue"]
        image=sample_image_to_pil(s1["observation.images.front"])
        state=s1["observation.state"].detach().cpu().numpy()
        red=predict_chunk(policy,pre,post,image,e1["instruction"],state,seed=123)[-1]
        blue=predict_chunk(policy,pre,post,image,e2["instruction"],state,seed=123)[-1]
        sep=float(np.linalg.norm(red-blue))
        rows.append({"model":label,"scene_id":scene_id,"final_separation_deg":sep,"separated_gt_6deg":sep>6.0})
    result={"paired_scenes":len(rows),"mean_final_separation_deg":float(np.mean([r["final_separation_deg"] for r in rows])),
            "pairs_separated_gt_6deg_rate":float(np.mean([r["separated_gt_6deg"] for r in rows]))}
    del policy,pre,post; torch.cuda.empty_cache()
    return rows,result


def evaluate_swapped_positions(checkpoint,dataset,manifest,train_stats,*,label="model",scene_limit=30):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from stage3_helpers import load_processors
    policy=SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda",dtype=torch.float32).eval()
    pre,post=load_processors(policy,checkpoint,train_stats)
    scene_map={s["scene_id"]:s for s in manifest["scenes"]}
    rows=[]; seen=set()
    for entry,sample,_ in episode_samples(dataset,manifest):
        sid=entry["scene_id"]
        if sid in seen: continue
        seen.add(sid)
        if len(seen)>scene_limit: break
        scene=scene_map[sid]
        if "background_rgb" in scene:
            swapped=create_scene(scene["blue_xy"],scene["red_xy"],background=scene["background_rgb"],radii=scene.get("radii",(7,7)))
        else:
            swapped=create_scene(scene["blue_xy"],scene["red_xy"])
        state=np.asarray(entry["start_state"],dtype=np.float32)
        # Keep the same red instruction; after the image swap red is at former blue coordinates.
        target=np.asarray(target_to_angles(*scene["blue_xy"]),dtype=float)
        phrase="赤い丸を指して"
        actions=predict_chunk(policy,pre,post,swapped,phrase,state,seed=123)
        err=float(np.linalg.norm(actions[-1]-target))
        rows.append({"model":label,"scene_id":sid,"instruction":phrase,"error_deg":err,"success":err<=SUCCESS_THRESHOLD_DEG})
    summary=error_summary(rows)
    del policy,pre,post; torch.cuda.empty_cache()
    return rows,summary


def evaluate_state_effect(checkpoint,dataset,manifest,train_stats,*,label="model",scene_limit=30):
    from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
    from stage3_helpers import load_processors
    policy=SmolVLAPolicy.from_pretrained(str(checkpoint)).to(device="cuda",dtype=torch.float32).eval()
    pre,post=load_processors(policy,checkpoint,train_stats)
    rows=[]; seen=set()
    for entry,sample,_ in episode_samples(dataset,manifest):
        if entry["scene_id"] in seen: continue
        seen.add(entry["scene_id"])
        if len(seen)>scene_limit: break
        image=sample_image_to_pil(sample["observation.images.front"])
        target=np.asarray(entry["target_angles"],dtype=float)
        for k,state in enumerate((np.asarray(entry["start_state"],dtype=np.float32),np.asarray([120.,120.],dtype=np.float32))):
            actions=predict_chunk(policy,pre,post,image,entry["instruction"],state,seed=123)
            err=float(np.linalg.norm(actions[-1]-target))
            rows.append({"model":label,"scene_id":entry["scene_id"],"condition":"observed_start" if k==0 else "shifted_start",
                         "color":entry["color"],"error_deg":err,"success":err<=SUCCESS_THRESHOLD_DEG})
    del policy,pre,post; torch.cuda.empty_cache()
    return rows


if __name__ == "__main__":
    raise SystemExit("Use the documented functions from a Colab notebook after mounting Drive and loading the datasets.")
