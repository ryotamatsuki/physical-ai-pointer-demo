# 02. End-to-end setup

部品が手元にある状態から、実験開始直前までの手順。

## Phase 0 — Colab VLMを先に成立させる

実機を組む前にAI側だけを確認する。

1. `colab/qwen3_vl_server.ipynb` をGoogle Colabで開く。
2. **ランタイム → ランタイムのタイプを変更 → T4 GPU**。
3. セルを上から実行。
4. `CUDA available: True` とGPU名を確認。
5. Qwen3-VL-2B-Instructのロード完了を確認。
6. 赤・青・緑カードを並べた写真を1枚アップロード。
7. 「一番左のカードを指して」など画像を見ないと答えられない指示でテスト。
8. 正しい `RED / BLUE / GREEN` が返ればAI単体はPASS。

その後、最後のGradioセルを実行し、表示された `https://...gradio.live` URLを控える。

> Gradio共有URLはColabランタイム再起動等で変わる可能性がある。

---

## Phase A — Windows PC

### A1. Clone repository

```powershell
git clone https://github.com/ryotamatsuki/physical-ai-pointer-demo.git
cd physical-ai-pointer-demo
```

### A2. Install Python

Python 3.11系を使用する。インストール時に **Add Python to PATH** を有効にする。

```powershell
python --version
```

### A3. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

確認:

```powershell
python -c "import cv2, serial, numpy, gradio_client; print('OK')"
```

### A4. Register Colab URL

`pc/config.py`:

```python
COLAB_GRADIO_URL = "https://xxxxxxxx.gradio.live"
```

ここにはColabノートブックが表示した実際のURLを設定する。

### A5. Install EOS Webcam Utility Pro

EOS RPをWindowsへUSB接続し、PCから映像取得できる状態にする。

推奨:
- 動画モード
- Full HD
- 29.97p / 30p程度
- オートパワーオフ無効
- カメラ位置を固定

カメラを利用する他アプリはテスト時に閉じる。

---

## Phase B — Pico H

### B1. Install Thonny

WindowsへThonnyをインストール。

### B2. Install MicroPython

1. Pico HをPCから外す。
2. BOOTSELを押しながらUSB接続。
3. `RPI-RP2` が現れることを確認。
4. ThonnyからMicroPython (Raspberry Pi Pico)を導入。
5. Shellで `>>>` を確認。

### B3. Basic test

```python
print("Hello Pico")
```

### B4. LED test

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

10周期以上安定すればEXP-001 PASS。

---

## Phase C — Wiring

電源OFFで配線する。

```text
Pico GP15 ----------------------- SG90 SIGNAL

Pico GND ----+
             +------------------- SG90 GND
5V GND ------+

5V + ---------------------------- SG90 V+
```

- PicoはPCのUSBから給電。
- SG90は外部5V。
- Pico / SG90 / 外部電源はGND共通。
- SG90をPico 3.3Vから給電しない。

---

## Phase D — Servo standalone test

紙の指示針はまだ付けない。

60 → 90 → 120 → 90°を繰り返し、異音・引っ掛かり・Picoリセットがないことを確認する。

成功後:

1. 90°へ移動。
2. その位置を機械的中央とする。
3. サーボホーンを正面へ。
4. 軽い紙の指示針を装着。

---

## Phase E — Pico production program

`pico/main.py` をThonnyでPico本体へ `main.py` として保存する。

再起動後に `READY` を確認。

---

## Phase F — PC to Pico serial

Windows Device ManagerでCOM番号を確認し、`pc/config.py`:

```python
SERIAL_PORT = "COM5"
```

を実機値へ変更。

PC側Pythonを実行するときはThonnyを閉じる。

```powershell
python pc\pico_test.py
```

60 → 90 → 120 → 90°へ動けばEXP-003 PASS。

---

## Phase G — EOS RP + OpenCV

```powershell
python pc\camera_test.py
```

EOS RPが映るindexを探し、`CAMERA_INDEX`へ記録。

撮影構図:
- 赤・青・緑カードすべて
- サーボ回転軸
- できるだけ俯瞰
- 本番まで位置固定

---

## Phase H — Color detection

```powershell
python pc\vision_test.py
```

赤・青・緑中心が安定するまでHSVを調整。

設定変更はEXP-005にも記録する。

---

## Phase I — Image coordinates to servo angle

画像上のサーボ回転軸を測り、`PIVOT_X / PIVOT_Y`へ設定。

```python
dx = x - PIVOT_X
dy = PIVOT_Y - y
vision_angle = degrees(atan2(dx, dy))
servo_angle = SERVO_CENTER + vision_angle
```

左右反転、倍率、オフセットを実機校正する。

---

## Phase J — Windows → Colab VLM test

ColabのGradioサーバーセルを動かした状態で:

```powershell
python pc\vlm_test.py
```

確認:

1. 「赤を指して」→ RED
2. 「青を指して」→ BLUE
3. カードを並べ替える
4. 「一番左」→ 現在左のカード

3と4が重要。これで画像が実際に利用されていることを確認する。

---

## Phase K — Full integration

開始前:

- ColabランタイムがGPUで起動中
- Gradio共有URLが現在のもの
- `pc/config.py`へURL反映
- EOS RPが他アプリに占有されていない
- Thonnyを閉じる
- SG90外部5V ON
- Pico COM番号確認
- カメラ固定
- 指示針に干渉なし

実行:

```powershell
python pc\main_demo.py
```

`指示（qで終了）:` が表示されれば実験開始直前。

## Stop conditions

次の場合は次工程へ進まない。

- ColabでQwen3-VL単体テストが通らない
- Colab URLがWindowsから呼び出せない
- Picoが頻繁に再起動
- SG90がストッパーへ当たる
- 3色検出が不安定
- Serial通信が不安定
- 「一番左」でVLMが現在配置を反映しない
