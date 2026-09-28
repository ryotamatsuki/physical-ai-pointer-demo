# Changelog

## Unreleased

### Astra review hardening
- Model output parser now accepts only exact `RED/BLUE/GREEN/NONE`.
- Continuous latest-frame camera capture added.
- Scene is re-observed before actuation; movement/order change aborts the action.
- Vision now uses ROI, area, aspect ratio, extent and unique-candidate validation.
- PC geometry rejects unreachable targets instead of clamping.
- Unconfigured calibration, changed resolution, pivot-near targets and non-finite values are rejected.
- Pico protocol now uses sequence-numbered PING/ANGLE/STOP acknowledgements.
- Pico rejects non-finite/out-of-range angles and overlong UART input.
- PWM STOP command added.
- Modal validates JSON type, JPEG/base64, bytes, dimensions and pixel count before GPU dispatch.
- Modal Web Function now awaits GPU work asynchronously.
- Model revision is captured when the model is cached.
- Client records total HTTP round-trip time.
- Public demo runbook uses temporary `min_containers=1` warm deployment.
- Camera 5-minute endurance and Pico five-cycle tests added.
- PRE-002 language evaluation, EXP-011 soak and EXP-012 cold restart added.
- Structured local JSONL runtime logging added.

### Architecture
- Replaced Google Colab + Gradio VLM path with authenticated Modal GPU backend.
- Fixed API contract v1 between Windows PC and Modal.
- Model cache uses Modal Volume.
- Proxy credentials stay outside GitHub.
- Dedicated 3.3V TTL USB-UART remains current production transport.

### Documentation
- Complete researched build manual.
- Public demo runbook.
- Astra review response matrix.
- Experiment dependency graph and reproducibility template.

### Notes
実機依存値は仮値を信用せず、実測して `pc/config.py` とexperiment logへ記録する。
