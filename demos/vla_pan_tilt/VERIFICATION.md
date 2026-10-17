# 2-axis SmolVLA verification (2026-10-17)

## Result: real GPU fine-tuning completed; synthetic pointing target NOT met

The saved Colab notebook ran the real `lerobot/smolvla_base` weights through a 2-axis LeRobot 0.6.1 setup, fine-tuned for 3,000 optimizer steps on a Tesla T4, reloaded the resulting checkpoint, and evaluated it on 60 independent episodes from 30 held-out synthetic scenes.

The final unseen-scene success rate was **31.67%** at the provisional 6° angular-error threshold. The requested 80% target was not met. **Keep hardware purchase on hold.** This remains a synthetic task; no real camera, servo, calibration, or physical-safety validation was performed.

## CI and branch

- Draft PR #5: https://github.com/ryotamatsuki/physical-ai-pointer-demo/pull/5
- Work branch: `test/vla-two-axis-preflight`; main and the existing Pointer demo were not changed.
- CI before this result-record update:
  - Standard CI: https://github.com/ryotamatsuki/physical-ai-pointer-demo/actions/runs/39013917580 — PASS
  - VLA preflight: https://github.com/ryotamatsuki/physical-ai-pointer-demo/actions/runs/39013917579 — PASS

## Training and dataset

- GPU: Tesla T4; LeRobot 0.6.1; FP16 autocast with FP32 master weights; batch size 2.
- Total full training: 3,000 steps in 965.25 seconds (16m 05s); peak allocated VRAM 4.94 GiB, peak reserved 5.15 GiB.
- Policy features were set to `observation.state=(2,)`, RGB image `(3,96,96)`, and `action=(2,)` before policy construction.
- `train_expert_only=True`; vision encoder frozen; 99,880,992 trainable of 450,046,176 total parameters.
- Train: 100 scenes / 200 episodes / 10,000 frames. Validation: 10 / 20 / 1,000. Test: 30 / 60 / 3,000. Each episode has 50 frames at 10 FPS.
- Scene hashes are disjoint across splits. Policy normalization statistics use train data only. Each scene pairs the same image with red and blue target instructions and distinct teacher trajectories. Geometric control was used only to generate synthetic labels; inference uses no color detector or geometry-based motor rule.
- Validation at 3,000 steps: 15.00% success; mean 11.49°, median 9.17°, p95 25.31°.

## Held-out evaluation

Success means final angular error <= 6°. This is only a provisional synthetic-scene threshold.

| Evaluation | Episodes | Success | Mean error | Median error | p95 error |
|---|---:|---:|---:|---:|---:|
| Unseen scenes, overall | 60 | 31.67% | 10.23° | 8.38° | 24.69° |
| Red target | 30 | 36.67% | 9.52° | 7.41° | 23.39° |
| Blue target | 30 | 26.67% | 10.95° | 9.53° | 23.77° |
| Changed start angles | 120 | 30.83% | 11.04° | 9.71° | 24.11° |
| Unseen Japanese paraphrases | 180 | 21.11% | 14.84° | 13.26° | 32.71° |
| Swapped color positions, same instruction | 60 | 31.67% | 10.01° | 8.70° | 20.43° |

### Evidence that both inputs affect actions

- On the same 30 images and start states, changing only the Japanese task from red to blue produced mean final-action separation of 19.54°. 93.33% of pairs differed by more than 6°.
- The Japanese instruction `赤い丸を指して` tokenized to 12 tokens.
- Removing visual content reduced success from 31.67% to 6.67% and increased mean error by 10.54° (to 20.77°).
- Replacing the task with a generic instruction reduced success to 13.33% and increased mean error by 9.29° (to 19.53°).

These counterfactuals show that vision and task text influence the model output, but they do not establish reliable semantic grounding: overall and paraphrase success remain low.

## Inference latency

After checkpoint load, 30 GPU calls were measured with 3 warmups excluded. For each 50-step, 2-axis action chunk: median 0.364 s, p95 0.380 s, mean 0.365 s. Model download and initial load time are excluded.

## Implementation correction and remaining risks

The first post-training evaluation stopped at a tokenizer-path error (`SmolVLAPolicy.vlm_with_expert` does not exist in this version). The path was corrected to `policy.model.vlm_with_expert.processor.tokenizer`, and evaluation resumed from the saved 3,000-step checkpoint without retraining. The final evaluation completed.

The synthetic 80% target was missed. Data covers only 100 training scenes and two primary Japanese templates; the vision encoder was frozen and only the expert-side policy parameters were trained. The model may need more diverse demonstrations plus a controlled experiment that updates the language/vision path or uses LoRA. A small exploratory overfit probe reported 0/8 successes at 6° and is not evidence of task readiness.

## Artifacts

- Executed Colab notebook (saved in Drive): https://colab.research.google.com/drive/1ZYLsrHC6C68GGEO04s5jACtMlggE7JOX
- Drive Stage 2 folder: https://drive.google.com/drive/folders/1KTkq524ep4BXJVZRLzJlp0jiDcsvUoxz
- Aggregate report: https://drive.google.com/file/d/1oX8d2zNAAgG-Y65A06PFXbPk-qlIvv68/view?usp=drivesdk
- Metrics JSON: https://drive.google.com/file/d/1OLcK7zEjyp0KIijWbCQn5FVogcP2BeWB/view?usp=drivesdk
- Evaluation summary CSV: https://drive.google.com/file/d/1gxQ_SQdmkOg_oAF4Xee0ZN649nA6PHFy/view?usp=drivesdk
- Training-stage CSV: https://drive.google.com/file/d/16BgXWqrhOAtvYcRuuqftOhsTZXY45Hkp/view?usp=drivesdk
- Evaluation success-rate graph: https://drive.google.com/file/d/1EhPdlOCt8B1D6OrZEjPlOOvXAFL5yCc0/view?usp=drivesdk

The notebook itself is saved in Drive with its executed cells. A summary JSON/CSV/report and an evaluation graph were uploaded and verified in the folder. The original episode-level evaluation CSV, training loss curve, logs, action-timeseries plot, and 1,800,281,633-byte checkpoint remain in the active Colab runtime and were **not** transferred to Drive: the browser security policy blocked file delivery from Colab's localhost file server. No model weights were committed to GitHub. Do not treat the aggregate summary CSV or success-rate chart as substitutes for those original files.
