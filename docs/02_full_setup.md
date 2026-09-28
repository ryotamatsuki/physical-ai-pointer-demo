# 02. End-to-end setup

部品が手元にある状態から、実験開始直前までの手順。

---

## Phase A — Windows PC

### A1. Create working directory

```powershell
mkdir C:\physical_ai_demo
cd C:\physical_ai_demo
```

### A2. Install Python

Python 3.11 系を使用する。インストール時に **Add Python to PATH** を有効にする。

確認:

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
python -c "import cv2, serial, ollama, numpy; print('OK')"
```

### A4. Install Ollama

Windows版Ollamaをインストールし、PowerShellで確認する。

```powershell
ollama --version
ollama pull qwen3-vl:2b
ollama list
```

### A5. Install EOS Webcam Utility Pro

Canon EOS Webcam Utility Proをインストールする。インストール後、Windowsを再起動する。

EOS RP側:
- 動画モード
- Full HD
- 29.97p / 30p程度
- オートパワーオフを無効化推奨
- USB接続

カメラを使うZoom、Teams、OBS、ブラウザ等はテスト時に閉じる。

---

## Phase B — Pico H

### B1. Install Thonny

WindowsへThonnyをインストールする。

### B2. Install MicroPython

1. Pico HをPCから外す。
2. BOOTSELを押しながらUSB接続。
3. Windowsに `RPI-RP2` が現れることを確認。
4. ThonnyからMicroPython (Raspberry Pi Pico)をインストール。
5. ThonnyのShellで `>>>` が出ることを確認。

### B3. Basic REPL test

```python
print("Hello Pico")
```

期待値:

```text
Hello Pico
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

LEDが0.5秒間隔で点滅すればEXP-001 PASS。

---

## Phase C — Wiring

**電源OFFで配線する。**

### C1. Signal

- Pico GP15 (physical pin 20) → SG90 signal

### C2. Ground

- Pico GND → external 5V GND
- SG90 GND → external 5V GND

3者を共通GNDにする。

### C3. Servo power

- External 5V + → SG90 V+
- External 5V GND → SG90 GND

**SG90をPicoの3.3V端子から給電しない。**

概念図:

```text
Pico GP15  ---------------------- SG90 SIGNAL

Pico GND ----+
             +------------------- SG90 GND
5V GND ------+

5V + ---------------------------- SG90 V+
```

---

## Phase D — Servo standalone test

紙の指示針はまだ付けない。

Thonnyで60/90/120°を試す。

```python
from machine import Pin, PWM
import time

servo = PWM(Pin(15))
servo.freq(50)

def move(angle):
    min_us = 1000
    max_us = 2000
    pulse_us = min_us + (max_us - min_us) * angle / 180
    duty = int(pulse_us / 20000 * 65535)
    servo.duty_u16(duty)

for angle in (60, 90, 120, 90):
    move(angle)
    time.sleep(1)
```

異音、引っ掛かり、電源リセットがないことを確認する。

### D2. Attach pointer

1. `move(90)` を実行。
2. この状態を機械的な中央とする。
3. サーボホーンを正面向きに取り付ける。
4. 軽い紙の針を取り付ける。

---

## Phase E — Install Pico production program

`pico/main.py` をThonnyでPico本体へ **main.py** として保存する。

再起動後に `READY` が出ることを確認する。

---

## Phase F — PC to Pico serial

Windows Device ManagerでPicoのCOM番号を確認する。

例:

```text
USB Serial Device (COM5)
```

`pc/config.py` の `SERIAL_PORT` を変更する。

**PC側Pythonを実行するときはThonnyを閉じる。**

```powershell
python pc\pico_test.py
```

60 → 90 → 120 → 90°へ動けばEXP-003 PASS。

---

## Phase G — EOS RP + OpenCV

```powershell
python pc\camera_test.py
```

0〜数番のカメラインデックスを順に試し、EOS RPの映像が出る番号を `pc/config.py` の `CAMERA_INDEX` に記録する。

撮影構図:
- 赤・青・緑カードすべてが映る
- サーボ回転軸が映る
- できるだけ俯瞰
- 本番までカメラ位置を固定

---

## Phase H — Color detection

```powershell
python pc\vision_test.py
```

赤・青・緑のカード中心が安定して取れるまでHSV閾値を調整する。

変更した閾値はコードだけでなく、EXP-005のログにも残す。

---

## Phase I — Image coordinates to servo angle

画像上でサーボ回転軸中心を測定し、`pc/config.py` の

```python
PIVOT_X = ...
PIVOT_Y = ...
```

へ設定。

目標中心 `(x, y)` とpivotから角度を求める。

```python
dx = x - PIVOT_X
dy = PIVOT_Y - y
vision_angle = degrees(atan2(dx, dy))
servo_angle = SERVO_CENTER + vision_angle
```

実機で左右反転、倍率、オフセットを校正する。

---

## Phase J — VLM standalone test

```powershell
python pc\vlm_test.py
```

最低限確認:

1. 「赤を指して」→ RED
2. 「青を指して」→ BLUE
3. カードを並べ替える
4. 「一番左のカードを指して」→ 現在左にある色

1と2だけでは、画像を無視して言語だけで回答できるため、3と4まで必須。

---

## Phase K — Full integration

実行前確認:

- Thonnyを閉じる
- Ollamaが起動
- EOS RPが他アプリに占有されていない
- SG90外部5V ON
- 共通GND確認
- Pico COM番号確認
- カメラ位置固定
- 指示針が物理的に干渉しない

本番プログラム:

```powershell
python pc\main_demo.py
```

画面に指示入力待ちが出れば、実験開始直前の状態。

---

## Stop conditions

以下の場合は次工程へ進まない。

- PicoがUSBから頻繁に再起動する
- SG90が連続的に唸る/ストッパーへ当たる
- 3色検出が安定しない
- カメラ番号が実行ごとに変わる
- PC→PicoのSerial通信が不安定
- 「一番左」テストでVLMが画像配置を反映しない
