# Preflight verification (2026-10-17)

## Result: PARTIAL PASS — no hardware purchase decision yet

GitHub Actions:
- Standard project CI: https://github.com/ryotamatsuki/physical-ai-pointer-demo/actions/runs/39006997982 — PASS
- 2-axis preflight workflow: https://github.com/ryotamatsuki/physical-ai-pointer-demo/actions/runs/39006998056 — PASS

### Verified in an actual GitHub Actions runner
- Python standard-library synthetic image + Japanese-task dataset generator runs.
- 20 synthetic scenes -> 40 paired episodes; image is identical for red/blue task at a given scene.
- Each episode records 12 frames with a 2D state and a 2D next-angle action.
- Both red and blue labels yield distinct teacher actions on the same image.
- Angle and split invariants are tested; held-out scenes do not leak between splits.
- Colab notebook JSON and its Python cells parse, and contain explicit 2D policy features.

### Verified by inspecting upstream source, not executing weights
- SmolVLAConfig pads state/action lengths to configurable maximum 32 dimensions.
- SmolVLA includes an action-chunk predictor.
- Upstream pretrained-feature mismatch has been reported (see issue 2418).
- Full checkpoint compatibility with the new feature names and camera pipeline is still NOT confirmed.

### NOT yet verified
- Execution of Colab notebook with actual SmolVLA weights and GPU inference.
- LeRobotDataset video serialization on Colab.
- Correct Japanese language grounding / target localization, or successful fine-tuning.
- Real image capture, calibration, 2-axis Pico/SG90 control, latency, safety.

## How to continue

1. Open `01_smolvla_2axis_preflight.ipynb` in Google Colab via this branch.
2. Set runtime to GPU, execute cells in order, and retain outputs.
3. The acceptance criterion is the printed final line:
   `PASS: actual SmolVLA accepted image + Japanese task and generated 2-axis continuous action chunk`.
4. If it fails, capture error and GPU metadata, fix before purchasing hardware.
5. Passing this acceptance criterion is a SHAPE/INFERENCE smoke test, not proof of useful policy. Next step: train on held-out real camera-conditioned demonstrations, measure task success.

No secrets or private camera images are part of this preflight.
