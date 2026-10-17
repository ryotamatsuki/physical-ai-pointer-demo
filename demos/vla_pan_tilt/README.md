# VLA 2-axis preflight (NOT completed VLA training)

This isolated folder does not modify the existing local YOLOX pointer demo.

## Purpose

Before purchasing parts, verify that 2-DOF **camera + Japanese instruction + state → action**
data has correct shape and supports tests distinguishing image dependence from
language dependence. This synthetic generator is a **teacher** and is NOT SmolVLA.

Run with Python 3.12 or later, no packages required:

```bash
python demos/vla_pan_tilt/preflight.py --out vla_preflight_data --scenes 20
python -m unittest discover -s demos/vla_pan_tilt -p "test_*.py" -v
```

The data generator creates identical visual scenes twice, with distinct Japanese tasks
and different teacher trajectories. It partitions data by SCENE rather than by
individual frame, preventing the same scene from leaking into train and test.

## Important caveat

This tests only data generation and trajectory constraints. It **does not** mean
SmolVLA was downloaded, fine-tuned, or run on GPU; neither a genuine robot camera nor
Pico/SG90 is involved. The next step is to run the Colab notebook in this folder
and provide its output log. Colab training and hardware performance remain unverified.

## Existing upstream issue

When fine-tuning a pretrained SmolVLA on different robot dimensions, the
factory may retain pretrained \`input_features\` while refreshing output dimensions.
Always set/check explicitly:
- observation.state: shape [2]
- observation.images.front: shape [3, 96, 96] for this synthetic test
- action: shape [2]

Refs:
- https://github.com/huggingface/lerobot/issues/2418
- https://github.com/huggingface/lerobot/blob/main/src/lerobot/policies/factory.py
- https://github.com/huggingface/lerobot/blob/main/src/lerobot/policies/smolvla/configuration_smolvla.py

Production requires genuine camera image capture, synchronized commanded/observed
angles, calibration, independently evaluated target pointing accuracy, and safety.
