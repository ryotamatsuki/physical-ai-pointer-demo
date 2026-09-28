# 02. End-to-end setup

詳細版は [04_modal_demo_machine_build_manual.md](04_modal_demo_machine_build_manual.md) を参照。

## 0. Risk tracks

独立して進められる。

```text
VLM:     PRE-001 → PRE-002
Camera:  EXP-004 → EXP-005
Control: EXP-001 → EXP-002 → EXP-003
```

これらが揃ってからgeometry/integrationへ進む。

## 1. Windows

```powershell
git clone https://github.com/ryotamatsuki/physical-ai-pointer-demo.git
cd physical-ai-pointer-demo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
python pc\environment_report.py
```

## 2. Modal

```powershell
modal token new
modal token info
modal run modal_backend.py::download_model
modal deploy modal_backend.py
modal workspace proxy-tokens create
```

`pc/config.py`へendpoint URLを設定。

PowerShell:

```powershell
$env:MODAL_PROXY_KEY="wk-..."
$env:MODAL_PROXY_SECRET="ws-..."
```

### PRE-001

```powershell
python pc\vlm_test.py --image C:\path\cards.jpg --instruction "一番左のカードを指して" --cold-start
pytest -q tests\test_model_output_contract.py
```

合格:
- 正しい対象
- model revision記録
- NOT RED / CREDIT / RED. 等を色へ変換しない

### PRE-002

静止画30ケース以上。
左/右/中央、欠落、曖昧、意味図柄を先に評価。

## 3. EOS RPを早期確認

Pico完成を待たない。

```powershell
python pc\camera_test.py
python pc\camera_test.py --index <EOS_INDEX> --duration 300
```

5分連続取得、実解像度、WB/露出/focus、電源を確認。

## 4. Pico

BOOTSEL → MicroPython → LED test。

本番:
- Micro USB: power / Thonny
- 3.3V TTL USB-UART: production command
- GP0 TX / GP1 RX
- GP15 servo PWM

SG90:
- external 5V
- common GND
- physical power cutoff
- 470–1000 µF capacitor推奨

## 5. Servo calibration

指示針なしで60/90/120°。

nominal command angleを実角度とみなさない。
紙分度器等で実方向を記録し、安全範囲を決定。

## 6. Pico protocol

```text
PING <seq>           → PONG <seq>
ANGLE <seq> <angle>  → OK <seq> <angle>
STOP <seq>           → STOPPED <seq>
```

```powershell
python pc\pico_test.py
```

5セット全ACK一致、抜線timeout、STOPを確認。

## 7. Vision

```powershell
python pc\vision_test.py
```

本番条件:
- board ROI
- each color exactly one candidate
- area/aspect/extent validation
- duplicate/missing → STOP

## 8. Geometry

`pc/config.py` に実測で設定:

```text
CALIBRATION_FRAME_WIDTH
CALIBRATION_FRAME_HEIGHT
PIVOT_X / PIVOT_Y
SERVO_MIN / SERVO_MAX
ANGLE_SIGN / SCALE / OFFSET
```

可動域外、pivot近傍、NaN/Inf、解像度違いはreject。clampしない。

## 9. Live VLM

```powershell
python pc\vlm_test.py
```

入力中もbackground capture。
指示確定後のfresh frameを使う。

## 10. Integration

```powershell
python pc\main_demo.py
```

main flow:
1. latest frame freeze
2. unique layout precheck
3. Modal VLM
4. current scene re-observe
5. layout/order/movement check
6. safe geometry
7. sequence command
8. matching ACK

System fault → STOP PWMを試行。
Semantic NONE → no new ANGLE、no auto recenter。

## 11. Public demo

[05_public_demo_runbook.md](05_public_demo_runbook.md) を使用。

本番時間帯だけ:

```powershell
$env:MODAL_MIN_CONTAINERS="1"
modal deploy modal_backend.py
```

終了後:

```powershell
$env:MODAL_MIN_CONTAINERS="0"
modal deploy modal_backend.py
```

公開前にEXP-011 100回耐久、EXP-012 cold restartをPASSする。
