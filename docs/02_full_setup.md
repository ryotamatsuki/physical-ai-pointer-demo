# 02. End-to-end setup

物品が手元にある状態から、実験開始直前までの標準手順。

原則: **前段階がPASSするまで次へ進まない。**

---

# Phase 0 — Modal VLMを実機より先に成立させる

## 0.1 Repository

Windows PowerShell:

```powershell
git clone https://github.com/ryotamatsuki/physical-ai-pointer-demo.git
cd physical-ai-pointer-demo
```

## 0.2 Python environment

Python 3.11系を使用。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

確認:

```powershell
python -c "import cv2, serial, requests, modal; print('OK')"
```

## 0.3 Modal authentication for deployment

Modalアカウントを準備し、ローカルCLIを認証する。

```powershell
modal token new
modal token info
```

これはModalへdeployするためのアカウント認証。

## 0.4 Cache Qwen3-VL in Modal Volume

```powershell
modal run modal_backend.py::download_model
```

成功条件:
- `physical-ai-pointer-model-cache` Volumeが作成される。
- Qwen/Qwen3-VL-2B-InstructがVolumeへ保存される。
- エラー終了しない。

## 0.5 Deploy

```powershell
modal deploy modal_backend.py
```

表示された `classify_api` のHTTPS URLを控える。

`pc/config.py`:

```python
MODAL_CLASSIFY_URL = "https://..."
```

## 0.6 Proxy authentication

Web endpointはproxy authを必須とする。

Modal workspaceでproxy tokenを発行し、Windowsへ次の2値を環境変数として設定する。

```text
MODAL_PROXY_KEY
MODAL_PROXY_SECRET
```

PowerShellの一時設定例:

```powershell
$env:MODAL_PROXY_KEY="wk-..."
$env:MODAL_PROXY_SECRET="ws-..."
```

**これらの値をGitHubへcommitしない。**

## 0.7 Static-image smoke test

赤・青・緑カードを横に並べた写真を1枚用意する。
スマホ写真でよく、EOS RPはまだ不要。

例:

```text
RED    BLUE    GREEN
```

実行:

```powershell
python pc\vlm_test.py --image C:\path\cards.jpg --instruction "一番左のカードを指して"
```

期待:

```text
TARGET: RED
```

カード順を変更した別画像:

```text
GREEN    RED    BLUE
```

同じ指示で:

```text
TARGET: GREEN
```

ここまで成功すれば **PRE-001 PASS**。

実機作業はこの後。

---

# Phase A — Pico H

## A1. Install Thonny

WindowsへThonnyをインストール。

## A2. Install MicroPython

1. Pico HをPCから外す。
2. BOOTSELを押しながらUSB接続。
3. Windowsに `RPI-RP2` が表示される。
4. ThonnyからMicroPython (Raspberry Pi Pico)を導入。
5. Shellの `>>>` を確認。

## A3. REPL test

```python
print("Hello Pico")
```

## A4. LED test

```python
from machine import Pin
import time

led = Pin("LED", Pin.OUT)

while True:
    led.value(1)
    time.sleep(0.5)
    led.value(0)
    time.sleep(0.5)
```

10周期以上安定 → **EXP-001 PASS**。

---

# Phase B — USB-UART + SG90 wiring

本番制御はPicoのUSB REPLではなく、3.3V TTL USB-UART adapterを専用通信路として使う。

電源OFFで配線。

## B1. PC → Pico UART0

```text
USB-UART TX → Pico GP1 / UART0 RX / physical pin 2
USB-UART RX ← Pico GP0 / UART0 TX / physical pin 1
USB-UART GND ↔ Pico GND / physical pin 3
```

- TX/RXは交差。
- USB-UARTのVCC/5Vは接続しない。
- PicoはMicro USBから給電する。

## B2. SG90

```text
Pico GP15 / physical pin 20 ------ SG90 SIGNAL

Pico GND / physical pin 18 ---+
                              +--- SG90 GND
External 5V GND --------------+

External 5V + --------------------- SG90 V+
```

原則:
- Pico: PCのMicro USB給電
- SG90: 外部5V給電
- USB-UART / Pico / SG90 / 外部電源はGND共通
- SG90をPico 3.3Vから給電しない

---

# Phase C — Servo standalone

紙の針はまだ付けない。

60° → 90° → 120° → 90°を繰り返す。

確認:
- 異音なし
- 引っ掛かりなし
- Pico再起動なし

成功後:
1. 90°へ移動
2. 90°を機械的中央とする
3. サーボホーンを正面へ
4. 軽い紙の指示針を装着

→ **EXP-002 PASS**

---

# Phase D — Pico production program

`pico/main.py` をThonnyでPico本体へ `main.py` として保存。

再起動後 `READY` を確認。

Windows Device ManagerでCOM番号を確認。

`pc/config.py`:

```python
SERIAL_PORT = "COM5"
```

実行時はThonnyを閉じる。

```powershell
python pc\pico_test.py
```

→ **EXP-003 PASS**

---

# Phase E — EOS RP

EOS Webcam Utility ProをWindowsへ導入。

EOS RP:
- 動画モード
- Full HD
- 30p前後
- オートパワーオフ無効推奨
- USB接続

他のカメラ利用アプリを閉じる。

```powershell
python pc\camera_test.py
```

EOS RPが映るindexを確認し:

```python
CAMERA_INDEX = 1
```

など実機値へ変更。

撮影構図:
- 3カード全部
- サーボ回転軸
- できるだけ俯瞰
- 本番までカメラ固定

→ **EXP-004 PASS**

---

# Phase F — OpenCV color detection

```powershell
python pc\vision_test.py
```

RED / BLUE / GREENの中心点が安定するまでHSV閾値を校正。

配置を変更した10試行で安定検出。

→ **EXP-005 PASS**

---

# Phase G — Geometry calibration

画像上のサーボ回転軸:

```python
PIVOT_X = ...
PIVOT_Y = ...
```

を測る。

計算:

```python
dx = x - PIVOT_X
dy = PIVOT_Y - y
vision_angle = degrees(atan2(dx, dy))
servo_angle = SERVO_CENTER + vision_angle
```

左右が逆なら `ANGLE_SIGN`。
ずれは `ANGLE_OFFSET`。
倍率ずれは `ANGLE_SCALE`。

複数配置でカード幅内を指せれば:

→ **EXP-006 PASS**

---

# Phase H — EOS RP → Modal

PRE-001では静止画ファイルを使用した。
ここではEOS RPから実際に取得したフレームをModalへ送る。

```powershell
python pc\vlm_test.py
```

確認:
1. 「赤を指して」→ RED
2. 「青を指して」→ BLUE
3. カードを並べ替える
4. 「一番左を指して」→ 現在左にある色
5. endpointを一時的に誤設定した場合、エラーで停止する

→ **EXP-007 PASS**

---

# Phase I — Full integration

実行前:
- Modal deployment active
- `MODAL_CLASSIFY_URL` 正しい
- proxy key/secret環境変数あり
- 展示直前にVLMテスト1回実行してwarm-up
- Thonnyを閉じる
- EOS RP接続
- SG90外部5V ON
- USB-UART adapterのCOM番号正しい
- カメラ固定
- 指示針干渉なし

実行:

```powershell
python pc\main_demo.py
```

画面:

```text
指示（qで終了）:
```

ここが実験開始直前。

---

# Fail-closed rule

次の場合は絶対にサーボ命令を送らない。

- Modal timeout
- proxy auth失敗
- HTTP error
- JSON parse失敗
- request_id mismatch
- invalid target
- target=NONE
- OpenCVが対象色を検出できない

AIモードの障害を、黙ってRULEモードへfallbackさせない。
