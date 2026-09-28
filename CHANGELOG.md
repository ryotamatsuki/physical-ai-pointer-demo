# Changelog

## Unreleased

### Architecture
- Replaced Google Colab + Gradio VLM path with an authenticated Modal GPU backend.
- Added fixed API contract v1 between Windows PC and Modal.
- Added fail-closed behavior: no valid VLM result means no servo command.
- Added Modal Volume model cache and T4 scale-to-zero design.
- Proxy credentials are environment variables and are never stored in the repository.

### Added
- Researched end-to-end Modal demo machine build manual (`docs/04_modal_demo_machine_build_manual.md`).
- Dedicated 3.3V TTL USB-UART control path for production Pico communication.
- `modal_backend.py`
- `pc/modal_client.py`
- `docs/03_modal_architecture.md`
- `experiments/PRE-001_modal_vlm_smoke_test.md`

### Removed
- Colab notebook/server path from the current branch.

### Existing
- Pico H / SG90 control scaffold.
- EOS RP/OpenCV test scaffold.
- Experiment plan through EXP-010.

### Notes
実機依存の値（COMポート、カメラ番号、画像上のサーボ軸座標、HSV閾値、角度補正値）は、実験ログに根拠とともに記録する。
