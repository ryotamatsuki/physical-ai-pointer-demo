# 2-axis SmolVLA verification (2026-10-17; 5,000-step run)

## Result: real GPU fine-tuning completed; 80% synthetic pointing target not met

The saved Colab notebook ran the real `lerobot/smolvla_base` weights using LeRobot 0.6.1 with explicit 2D state and action features. The policy was fine-tuned for 5,000 optimizer steps on a Tesla T4, its final checkpoint was reloaded, and held-out evaluation completed on 60 independent episodes from 30 scene-disjoint synthetic test images.

At the provisional 6° final-angle-error threshold, unseen-scene success was **63.33%** (38/60), below the requested 80% target. Mean error was **6.04°**, median **5.21°**, and p95 **13.23°**. Performance improved from 31.67% at 3,000 steps. **Keep hardware purchase on hold.** This does not validate a camera, servos, calibration, or physical safety.

## Training and dataset

- GPU: Tesla T4; LeRobot 0.6.1; FP16 autocast with FP32 master weights; batch size 2.
- Full training: 5,000 steps in 1,576.87 seconds (26m 17s); peak allocated VRAM 4.945 GiB and peak reserved VRAM 5.160 GiB.
- Policy features were set before construction to `observation.state=(2,)`, RGB image `(3,96,96)`, and `action=(2,)`.
- `train_expert_only=True`; vision encoder frozen; 99,880,992 trainable of 450,046,176 total parameters.
- Train: 100 scenes / 200 episodes / 10,000 frames. Validation: 10 / 20 / 1,000. Test: 30 / 60 / 3,000. Each episode has 50 frames at 10 FPS.
- Scene hashes are disjoint across splits. Policy statistics use train data only. Each generated scene pairs the same image with both red-target and blue-target instructions and separate teacher trajectories. Geometry was used only to make teacher labels; inference has no color detector or geometry-to-angle rule.
- 6° is only a provisional synthetic-scene threshold, not a physical precision requirement.

| Cumulative steps | Added training time | Validation success | Mean error | Median error | p95 error |
|---:|---:|---:|---:|---:|---:|
| 300 | 121.6 s | 10% | 22.17° | 24.65° | 38.90° |
| 1,000 | 278.1 s | 5% | 18.83° | 17.73° | 30.27° |
| 3,000 | 565.6 s | 15% | 11.49° | 9.17° | 25.31° |
| 5,000 | 611.6 s | 50% | 6.88° | 5.75° | 12.63° |

## Held-out evaluation

Success means final angular error <= 6°.

| Evaluation | Episodes | Success | Mean error | Median error | p95 error |
|---|---:|---:|---:|---:|---:|
| Unseen scenes, overall | 60 | 63.33% | 6.04° | 5.21° | 13.23° |
| Red target | 30 | 70.00% | 5.89° | 5.01° | 12.83° |
| Blue target | 30 | 56.67% | 6.20° | 5.65° | 16.00° |
| Swapped color positions, same instruction | 60 | 65.00% | 5.68° | 4.57° | 15.26° |
| Changed start angles | 120 | 58.33% | 6.75° | 5.47° | 17.07° |
| Unseen Japanese paraphrases | 180 | 22.22% | 11.83° | 10.65° | 23.68° |

### Evidence that both image and language affect actions

- On the same 30 images and start states, changing only the instruction from red to blue produced a mean final-action separation of 27.79°. 96.67% of the pairs differed by more than 6°.
- The Japanese instruction `赤い丸を指して` was passed to the tokenizer as 12 tokens.
- Removing visual content reduced success from 63.33% to 6.67% and increased mean error by 15.10° (to 21.14°).
- Replacing the task with a generic instruction reduced success to 16.67% and increased mean error by 12.98° (to 19.02°).
- Swapping the colored targets' positions while keeping the same command achieved 65.00% on the paired-position test.

These counterfactuals show image and text sensitivity. They do not establish robust grounding: paraphrase success remains 22.22%, and overall success remains below target.

## Inference latency

After checkpoint load, 30 GPU calls were measured with 3 warmups excluded. One 50-step, 2-axis action chunk took median 0.360 s, p95 0.383 s, and mean 0.363 s. Model download and initial load are excluded.

## Failure analysis and remaining risk

A 100-step, 8-episode small-data overfit smoke test achieved 0/8 successes, so it did not establish that the model can memorize a tiny subset with this training configuration. Full evaluation improved from 31.67% at 3,000 steps to 63.33% at 5,000 steps, so optimization does affect the task; training loss alone is not evidence of the required pointing quality. The tokenizer accepts the Japanese instruction, while unseen paraphrases remain weak. `train_expert_only=True` and a frozen vision encoder may limit adaptation to simple synthetic shapes and language. The results do not isolate one root cause; next useful tests are longer small-set overfit with per-step checks, diverse scene data, and a controlled experiment that updates the visual/language path or uses LoRA.

## Artifacts

- Draft PR #5: https://github.com/ryotamatsuki/physical-ai-pointer-demo/pull/5
- Executed Colab notebook: https://colab.research.google.com/drive/1ZYLsrHC6C68GGEO04s5jACtMlggE7JOX
- Drive Stage 2 folder: https://drive.google.com/drive/folders/1KTkq524ep4BXJVZRLzJlp0jiDcsvUoxz
- Aggregate report: https://drive.google.com/file/d/1oX8d2zNAAgG-Y65A06PFXbPk-qlIvv68/view?usp=drivesdk
- Metrics JSON: https://drive.google.com/file/d/1OLcK7zEjyp0KIijWbCQn5FVogcP2BeWB/view?usp=drivesdk
- Evaluation summary CSV: https://drive.google.com/file/d/1gxQ_SQdmkOg_oAF4Xee0ZN649nA6PHFy/view?usp=drivesdk
- Training-stage CSV: https://drive.google.com/file/d/16BgXWqrhOAtvYcRuuqftOhsTZXY45Hkp/view?usp=drivesdk
- Evaluation success-rate graph: https://drive.google.com/file/d/1EhPdlOCt8B1D6OrZEjPlOOvXAFL5yCc0/view?usp=drivesdk

The executed notebook includes the final evaluation and embedded loss-curve, unseen-action-timeseries, and sample-scene plots. The aggregate report/JSON/CSVs and success-rate chart are in the Drive folder. The 5,000-step checkpoint is saved under `checkpoint_5000/` (7 files, 1,800,281,633 bytes); the 20 raw result files (1,186,665 bytes), including episode-level evaluation CSVs, manifests, training logs, loss curve, and action plots, are under `raw_results/`. Source and destination manifests matched by relative path and byte size after the 2026-10-17 transfer. No model weights were committed to GitHub.


## Stage 3: continued training, held-out generalization, and closed-loop simulation (2026-10-17)

Stage 3 ran on a Google Colab **NVIDIA A100-SXM4-40GB** with PyTorch 2.11.0+cu130 and LeRobot 0.6.1. Training used 20,000 frames / 400 episodes across 200 synthetic scenes; validation used 30 disjoint scenes / 60 episodes; the final set used another 60 disjoint scenes / 120 episodes. All three splits were hash-checked. Preprocessing used training statistics only. The original Stage 2 Drive checkpoint was copied for initialization and left unchanged.

### Training and validation model selection

Success means final Euclidean two-axis angle error <= 6 degrees. Model selection used the new validation split only.

| Model | Training from | Trainable parameters | Training time | Validation success | Mean error | Median / p95 error |
|---|---|---:|---:|---:|---:|---:|
| Stage 2 baseline | Stage 2 5,000-step weights | -- | -- | 31/60 (51.67%) | 7.329° | 5.767° / 16.178° |
| B: expert continuation | Stage 2 weights; fresh optimizer; expert-only; vision frozen; LR 1e-5; 2,000 steps | 99,880,992 | 387.03 s | 32/60 (53.33%) | 6.337° | 5.376° / 13.237° |
| C: VLM adaptation | Stage 2 weights; fresh optimizer; VLM text path + policy/expert; vision frozen; LR 5e-6; 2,000 steps | 306,471,072 (206,590,080 VLM) | 443.13 s | 37/60 (61.67%) | 6.436° | 5.032° / 14.836° |

The VLM parameter audit confirmed that language-path parameters were trainable and the vision encoder was frozen. Both B and C initialized from the same Stage 2 weights; optimizer state was reset in both experiments.

The small-set overfit check succeeded on 4 scenes / 8 episodes after 500 steps: 8/8 episodes were within 6 degrees, mean endpoint error 1.364 degrees. Mean error at action-chunk indices 0, 25, and 49 was 14.388°, 5.423°, and 1.364°, respectively. This establishes that the training pipeline can memorize the small demonstration set; it does not establish generalization.

### One-time final evaluation

C was selected using validation and reloaded from its Drive checkpoint before final inference. The previously untouched 60-scene / 120-episode final split was evaluated once. It achieved **71/120 (59.17%)**, below the 80% target. Mean / median / p95 endpoint error was **6.003° / 5.116° / 13.517°**. Scene-level bootstrap 95% interval: **49.17%–69.17%**. Red success was 60.00%; blue was 58.33%. After model load, GPU inference latency was median **0.296 s** and p95 **0.300 s** per 50x2 action chunk. The checkpoint reload succeeded.

### Input probes and closed-loop result

On validation, switching only red/blue language instructions separated paired endpoints by 32.88° on average; all 30 pairs differed by more than 6°. Blank-image ablation reduced success from 61.67% to 1.67%; a generic colorless instruction reduced it to 8.33%. These results show strong response to both input channels. Robust grounding remained weak: swapping red/blue positions yielded 12/30 successes (40%), and four held-out Japanese paraphrases yielded 42/120 (35%). Changing the start state from the observed value to [120, 120] reduced success from 56.67% to 40.00% on the 30-scene probe.

Ideal-actuator simulation on 10 validation scenes / 20 episodes per mode gave:
- Execute all 50 steps open loop: 12/20 (60%), mean final error 6.725°, 1 inference call.
- Replan after each 10 steps: 7/20 (35%), mean error 10.224°, 5 calls.
- Replan after each 5 steps: 2/20 (10%), mean error 12.894°, 10 calls.

No proposed command exceeded the simulated [30°, 150°] joint limits; the per-axis 6° velocity limiter clipped 0.1% of actions. More frequent replanning degraded performance, consistent with the policy restarting its action chunk. This simulation assumes ideal actuators and a fixed artificial image; it does not validate physical servo or camera behavior.

### Decision and artifacts

**Keep the 3,000–5,000 yen hardware purchase on hold.** The selected model is fast enough for a short demo and both input channels affect its output, but it missed the required final generalization rate (59.17% vs. 80%). Avoid extending synthetic-only training indefinitely; a small real-camera demonstration set with a new independent final test is the next useful software experiment.

- Executed Stage 3 Colab notebook: https://colab.research.google.com/drive/1s8RZAZ6JnSXk8noccYtSCVgc1pTbkPWg
- Stage 3 Drive folder (checkpoints, logs, datasets/manifests, CSVs, plots, and report): https://drive.google.com/drive/folders/1MNAuBtLtAqfq1Kow4ezWldFzRL5VCAXe
- Stage 3 report in Drive: `results/stage3_report.md`

Stage 2 artifacts remain intact. No model weights were committed to GitHub. This PR remains a draft; neither `main` nor the existing Pointer demo was modified.
