# Modal方式 Physical AI Pointer Demo — 実機構築・セットアップ完全手順書

最終更新: 2026-09-28

この文書は、**WindowsノートPC + Canon EOS RP + Modal GPU + Qwen3-VL-2B-Instruct + Raspberry Pi Pico H + SG90** で、自然言語に従って色カードを物理的な指示針で指すデモ機を、購入・配線・クラウド設定・PC設定・校正・統合・本番直前確認まで一貫して構築するための手順書です。

---

## 0. 完成形

### 0.1 目的

観客が例えば、

- 「青いカードを指して」
- 「一番左のカードを指して」
- 「一番右のカードを指して」

と入力すると、EOS RPが現在のカード配置を撮影し、Modal上のVLMが対象色を選び、Windows PCがOpenCVで対象カードの正確な画像座標を測定し、Pico H経由でSG90を回して紙の指示針を対象へ向けます。

### 0.2 最終アーキテクチャ

```text
観客の自然言語指示
        +
Canon EOS RPの現在画像
        ↓
Windows PC
  ├─ カメラ取得
  ├─ JPEG縮小・圧縮
  └─ HTTPS request
        ↓ Internet
Modal authenticated Web Function
        ↓
Qwen3-VL-2B-Instruct / T4 GPU
        ↓
RED / BLUE / GREEN / NONE
        ↓ Internet
Windows PC
  ├─ OpenCVで対象色カード中心(x,y)を検出
  ├─ サーボ軸中心から目標角を計算
  └─ USB-UARTへ ANGLE xx.x
        ↓
USB-UART adapter
        ↓ UART0
Raspberry Pi Pico H
        ↓ GP15 / 50 Hz PWM
SG90
        ↓
軽量な紙の指示針
```

### 0.3 このデモの位置付け

これは **VLAそのものではなく、VLM + classical controlによるPhysical AIデモ** です。

- VLM: 「何を指すか」
- OpenCV: 「それは画像上のどこか」
- 幾何計算: 「何度回すか」
- Pico H: 「PWMを出す」
- SG90: 「物理的に動く」

という責務分離を行います。

---

# 1. 仕様確認と設計上の判断

## 1.1 Raspberry Pi Pico H

Raspberry Pi公式資料では、Pico HはRP2040搭載・ヘッダピン実装済みのPicoです。Pico/Pico Hは同一ピン配置で、40ピン中26 GPIOを利用できます。

今回使用するピン:

| Pico H | 物理ピン | 用途 |
|---|---:|---|
| GP0 | 1 | UART0 TX |
| GP1 | 2 | UART0 RX |
| GND | 3 | USB-UART共通GND |
| GND | 18 | SG90電源との共通GND |
| GP15 | 20 | SG90 PWM signal |

公式pinoutではGP15は物理ピン20、GP0/GP1はUART0 TX/RXとして使用できます。

Pico HのUSBは **Micro USB** で、電源・MicroPython書込み・REPLに使用します。

## 1.2 PC↔Pico通信は専用UARTを使う

試作だけならPicoのUSB REPL経由でも通信できますが、本番デモでは以下を分離します。

```text
Pico Micro USB
  → 電源 + Thonny/MicroPython書込み

USB-UART adapter
  → 本番制御コマンド専用
```

理由:
- ThonnyとPC制御プログラムのCOMポート競合を避ける
- REPL文字列と制御プロトコルを分離する
- 通信トラブルの切り分けが容易になる

USB-UART adapterは **3.3V TTL logic対応** を使います。RS-232レベルのアダプタは使用しません。

## 1.3 SG90

TowerPro公式のSG90は9 g、4.8 V駆動、1.8 kg·cm（4.8 V）のstall torque、約0.1～0.12 s/60°クラスの小型サーボです。メーカーは外部アダプタ給電を指定しています。

重要:
- 「SG90」という名称で多数の互換品・クローンが流通している
- 正常な角度範囲、pulse width、消費電流は製品ごとの差がある
- TowerPro公式でも通常サーボは150°程度としている記述がある
- 360°連続回転版も存在するため、購入時に**位置制御型**を確認する

したがって本デモでは最初から0°/180°を使いません。

初期安全設定:

```text
PWM frequency: 50 Hz
初期pulse range: 1000–2000 µs
最初のテスト角: 60° / 90° / 120°
運用safe range初期値: 30°–150°
```

実機で異音やストッパー接触があればさらに狭めます。

## 1.4 Canon EOS RP

Canon公式仕様:
- USB端子: USB Type-C
- Windows PCとのUSB通信に対応
- EOS Webcam Utility Pro対応機種
- 日本ではEOS Webcam Utility Proの基本機能に1台接続が含まれる

本デモでは1台しか使わないため基本機能で足ります。

長時間展示ではバッテリー切れを避けるため、必要ならEOS RP対応のACアダプター/DR-E18系ダミーバッテリー構成を使用します。

## 1.5 Qwen3-VL-2B-Instruct

Hugging Face公式モデル:
- model: `Qwen/Qwen3-VL-2B-Instruct`
- task: image-text-to-text
- Apache-2.0
- weight repository 約4.27 GB
- Transformersで画像＋テキストのmultimodal入力に対応

本デモでは出力を自由文にせず、必ず:

```text
RED
BLUE
GREEN
NONE
```

の4値へ正規化します。

## 1.6 Modal

2026-09-28時点のModal公式仕様を前提にします。

採用機能:
- `@modal.fastapi_endpoint(..., requires_proxy_auth=True)`
- T4 GPU
- `min_containers=0`
- `max_containers=1`
- `scaledown_window=900`
- `modal.Volume` にモデルを永続キャッシュ
- Proxy Token認証

Proxy Token:
- key: `wk-...`
- secret: `ws-...`
- HTTP header:
  - `Modal-Key`
  - `Modal-Secret`

Modal API token (`ak-/as-`) とproxy token (`wk-/ws-`) は別物です。

---

# 2. 購入・準備する機材

## 2.1 必須

| 品目 | 数量 | 条件 |
|---|---:|---|
| WindowsノートPC | 1 | Python/OpenCVが動けば可 |
| Canon EOS RP | 1 | 手持ちを使用 |
| EOS RP用USBデータケーブル | 1 | カメラ側USB Type-C |
| Raspberry Pi Pico H | 1 | RP2040、ヘッダ実装済み |
| Micro USBデータケーブル | 1 | Pico用。充電専用不可 |
| SG90位置制御型サーボ | 1 | 360°continuous版不可 |
| 3.3V TTL USB-UART adapter | 1 | CP2102/CH340等。3.3V logic対応 |
| ジャンパーワイヤ | 1式 | メス-メス中心 |
| ブレッドボード | 1 | 小型で可 |
| 5V電源 | 1 | 5V 2A程度を推奨 |
| 5V/GND取り出し部品 | 1 | USB breakout等 |
| 赤・青・緑カード | 各1 | つや消し推奨 |
| 軽量指示針 | 1 | 厚紙等 |
| 台座 | 1 | A3程度のスチレンボード等 |

5V 2Aは「SG90が常時2A消費する」という意味ではありません。起動・急加速・拘束時の電流変動や個体差へ余裕を持たせるためです。

## 2.2 強く推奨

| 品目 | 理由 |
|---|---|
| EOS RPを俯瞰固定できる三脚/カメラアーム | 幾何校正を維持するため |
| デジタルテスター | 5V極性と共通GND確認 |
| SG90予備1個 | 安価な互換サーボの個体差対策 |
| 470–1000 µF程度の電解コンデンサ | サーボ電源変動対策。必要時のみ |
| EOS RP AC電源 | 長時間展示時の電池切れ防止 |

---

# 3. 最初に作る物理レイアウト

## 3.1 台座

初期推奨:

```text
A3程度
背景: 白または無彩色
カード: 70×100 mm程度以上
サーボ軸からカード中心まで: 約200–250 mm
カードは円弧上へ配置
```

初期配置例:

```text
              RED     BLUE     GREEN

                   約20–25 cm
                      ↑
                      │
                 [ pointer ]
                    [SG90]
```

最初はカードを±45～50°程度の範囲へ収めます。
サーボ端点近くを使わないことが重要です。

## 3.2 指示針

- 長さ: 約120–150 mmから開始
- 材質: 厚紙、薄いプラ板など
- できるだけ軽くする
- 先端を尖らせすぎない
- サーボホーンへの固定は両面テープ等で試作

---

# 4. Windows PCの初期設定

## 4.1 Repository clone

PowerShell:

```powershell
git clone https://github.com/ryotamatsuki/physical-ai-pointer-demo.git
cd physical-ai-pointer-demo
```

## 4.2 Python

Python 3.11系を推奨。

確認:

```powershell
python --version
```

仮想環境:

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

---

# 5. Modalバックエンドを構築する

この工程は**実機を組む前に行う**。

## 5.1 Modal CLI認証

```powershell
modal token new
modal token info
```

`modal token new` はdeploy用のAPI tokenをローカルプロファイルへ設定します。

## 5.2 モデルをVolumeへ保存

```powershell
modal run modal_backend.py::download_model
```

期待:
- `physical-ai-pointer-model-cache` Volume作成
- Qwen3-VL-2B-Instruct取得
- 正常終了

## 5.3 deploy

```powershell
modal deploy modal_backend.py
```

出力に表示される `classify_api` のHTTPS URLを控えます。

`pc/config.py`:

```python
MODAL_CLASSIFY_URL = "https://....modal.run"
```

## 5.4 Proxy Token作成

CLI:

```powershell
modal workspace proxy-tokens create
```

表示されたkey/secretを安全に保存します。

PowerShellの現在セッションだけに設定:

```powershell
$env:MODAL_PROXY_KEY="wk-..."
$env:MODAL_PROXY_SECRET="ws-..."
```

永続化する場合はWindowsのユーザー環境変数へ設定してください。

**禁止:**
- GitHubへcommit
- READMEへ貼る
- Issueへ貼る
- スクリーンショットへ残す

## 5.5 PRE-001 静止画テスト

スマホで赤青緑カードを撮影。

画像1:

```text
RED   BLUE   GREEN
```

実行:

```powershell
python pc\vlm_test.py --image C:\path\cards1.jpg --instruction "一番左のカードを指して"
```

期待:

```text
TARGET: RED
```

画像2:

```text
GREEN   RED   BLUE
```

同じ指示:

```text
TARGET: GREEN
```

この2試行が通ればModal側の基本経路は成立。

## 5.6 Cold start

`min_containers=0` のため、しばらく使わないとGPUコンテナは0台へ縮退します。
`scaledown_window=900` はアイドル後最大15分程度保持する設定です。

本番前には必ず1回テスト推論を行ってwarm-upします。

---

# 6. Pico HへMicroPythonを導入

## 6.1 BOOTSEL

1. Pico HのUSBを抜く
2. BOOTSELを押したままMicro USB接続
3. `RPI-RP2` ドライブが表示されたらBOOTSELを離す
4. 最新stableのPico用MicroPython UF2を書き込む

Raspberry Pi公式手順ではUF2書込み後に自動再起動し、USB Serial経由でREPLへアクセスできます。

## 6.2 Thonny

Thonnyでinterpreterを:

```text
MicroPython (Raspberry Pi Pico)
```

に設定。

Shell:

```python
print("Hello Pico")
```

## 6.3 LEDテスト

Pico H（RP2040）のオンボードLEDはGP25。

```python
from machine import Pin
import time

led = Pin(25, Pin.OUT)

for _ in range(20):
    led.toggle()
    time.sleep(0.5)
```

10周期以上安定すればEXP-001 PASS。

---

# 7. 本番用PC↔Pico UART配線

## 7.1 なぜUSB-UARTか

PicoのMicro USB REPLと本番制御通信を分離します。

本番配線:

```text
Windows PC
   │
   ├── USB ───────── Pico Micro USB
   │                   └ 電源 / Thonny
   │
   └── USB ─── USB-UART adapter
                  │ TX
                  │ RX
                  │ GND
                  ↓
               Pico H
```

## 7.2 UART信号

```text
USB-UART TX  → Pico GP1 / UART0 RX / physical pin 2
USB-UART RX  ← Pico GP0 / UART0 TX / physical pin 1
USB-UART GND ↔ Pico GND / physical pin 3
```

注意:
- TXとRXは交差
- USB-UARTの5V/VCC線は接続しない
- PicoはMicro USBから給電
- 3.3V TTL logicを使用
- RS-232アダプタは不可

Windows Device ManagerでUSB-UART adapterのCOM番号を確認。

例:

```text
Silicon Labs CP210x USB to UART Bridge (COM6)
```

`pc/config.py`:

```python
SERIAL_PORT = "COM6"
SERIAL_BAUD = 115200
```

---

# 8. SG90電源・信号配線

## 8.1 一般的な線色

TowerPro系:

```text
Brown/Black  = GND
Red          = V+
Orange/Yellow= PWM signal
```

互換品は必ず販売元仕様も確認してください。

## 8.2 配線

```text
Pico H physical pin 20 / GP15
        │
        └──────────────── SG90 signal

External 5V +
        └──────────────── SG90 V+ (red)

External 5V GND ───────── SG90 GND
        │
        └──────────────── Pico GND (physical pin 18)

USB-UART GND ───────────── Pico GND (physical pin 3)
```

結果として:
- Pico GND
- USB-UART GND
- SG90 GND
- 外部5V GND

は共通になります。

## 8.3 やってはいけない配線

- SG90をPicoの3V3(OUT)から給電
- USB-UARTの5VをPico GPIOへ接続
- サーボGNDとPico GNDを分離したまま信号だけ接続
- 電源ONのまま配線変更

---

# 9. SG90単体試験

まず**指示針を外した状態**で実施。

Thonnyから一時的に次を試します。

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

for a in (60, 90, 120, 90):
    move(a)
    time.sleep(1)
```

確認:
- 大きく震えない
- ストッパーへ押し付ける音がしない
- Picoが再起動しない
- 外部5Vが著しく低下しない

異常があれば電源OFF。

---

# 10. Pico本番プログラム

Repositoryの `pico/main.py` は本番ではUART0を使用します。

Picoへ:

```text
main.py
```

として保存。

制御プロトコル:

```text
PING
CENTER
ANGLE 90
ANGLE 123.4
```

応答:

```text
PONG
OK 90.0
ERROR ...
```

## 10.1 PC→Pico試験

Thonnyは閉じなくてもUART adapterは別COMですが、実験時は混乱防止のため閉じることを推奨。

```powershell
python pc\pico_test.py
```

60 → 90 → 120 → 90°の順で動けばEXP-003 PASS。

---

# 11. 指示針を取り付ける

1. `CENTER` または90°へ移動
2. 電源OFF
3. サーボホーンを物理的に正面へ付け直す
4. 軽量指示針を固定
5. 電源ON
6. 60/90/120°を再試験

90°を「真正面」とする基準を作ります。

---

# 12. EOS RPセットアップ

## 12.1 EOS Webcam Utility Pro

日本CanonのEOS Webcam Utility Proをインストール。

EOS RPは対応機種です。
基本機能でカメラ1台接続が可能。

インストール後Windowsを再起動。

## 12.2 接続

EOS RP側はUSB Type-C。

```text
EOS RP USB-C
   ↓ data cable
Windows PC
```

## 12.3 カメラ設定の初期推奨

- 動画モード
- Full HD系
- 30p前後
- 固定ホワイトバランス推奨
- 露出をできるだけ固定
- カードとサーボ軸へ合焦後、可能ならAF挙動を安定化
- オートパワーオフ無効
- カメラ固定後は触らない

HSV色検出を使うため、**ホワイトバランスと露出が勝手に変化し続ける状態は避ける**のが重要です。

## 12.4 camera index確認

Zoom、Teams、OBS等カメラを使うアプリを閉じる。

```powershell
python pc\camera_test.py
```

EOS RPが表示されたindexを記録。

例:

```python
CAMERA_INDEX = 1
```

---

# 13. カメラの物理配置

## 13.1 俯瞰配置

理想:

```text
             EOS RP
                │
                ▼
   ┌─────────────────────┐
   │ RED   BLUE   GREEN  │
   │                     │
   │          ↑          │
   │       pointer       │
   │        [SG90]       │
   └─────────────────────┘
```

カメラ光軸をできるだけ台座へ垂直に近づけます。

## 13.2 レンズ

可能なら極端な広角は避けます。

目安:
- フルサイズ換算35–50 mm前後が扱いやすい
- 台座全体が入ればよい
- 画面端の大きな歪みを避ける

手持ちレンズで構いません。

---

# 14. OpenCV色検出

```powershell
python pc\vision_test.py
```

画面上で:
- RED
- BLUE
- GREEN

の中心点がカードへ重なることを確認。

## 14.1 HSV初期値

Repositoryの `pc/config.py` の値は**開始点であり実測値ではない**。

照明・印刷色・EOS RP設定で変わるためEXP-005で校正します。

## 14.2 合格基準

カード配置を変えた10試行で:
- 3色とも検出
- 別の物体を誤検出しない
- 中心座標がカード内部

を目標にする。

---

# 15. 画像座標→サーボ角度の校正

## 15.1 Pivot

OpenCV画面上でサーボの回転軸中心を測定。

`pc/config.py`:

```python
PIVOT_X = ...
PIVOT_Y = ...
```

## 15.2 幾何

```python
dx = target_x - PIVOT_X
dy = PIVOT_Y - target_y

vision_angle = degrees(atan2(dx, dy))
servo_angle = SERVO_CENTER + vision_angle
```

実機補正:

```python
ANGLE_SIGN
ANGLE_SCALE
ANGLE_OFFSET
```

を使う。

## 15.3 校正順

1. 正面カード → 90°付近
2. 左カード
3. 右カード
4. 中間位置
5. カード位置変更

左右が逆:
```python
ANGLE_SIGN = -1.0
```

全体に一定量ずれる:
```python
ANGLE_OFFSET = ...
```

端へ行くほど誤差が増える:
- `ANGLE_SCALE`
- カメラの俯瞰角
- レンズ歪み
- カード円弧配置

を見直す。

---

# 16. EOS RP→Modal実画像試験

Modalがwarmな状態で:

```powershell
python pc\vlm_test.py
```

試験順:

1. 「赤を指して」→ RED
2. 「青を指して」→ BLUE
3. 「一番左のカードを指して」
4. カードを並べ替える
5. 再度「一番左のカードを指して」

3～5が重要。
色名指定だけでは画像を見なくても回答できるためです。

---

# 17. 統合試験

```powershell
python pc\main_demo.py
```

処理:

```text
1. instruction入力
2. EOS RP frame取得
3. JPEG化
4. Modalへ送信
5. target受信
6. OpenCVでtarget色中心
7. servo angle計算
8. UARTへ ANGLE
9. Pico PWM
10. SG90移動
```

## 17.1 Fail-closed

以下では**絶対にサーボを動かさない**。

- Modal timeout
- 401/403
- 5xx
- responseがJSONでない
- schema version違い
- request_id不一致
- targetが4値以外
- target=NONE
- OpenCVが該当色を検出できない
- カメラ取得失敗

AI障害時に黙って固定角度やrule-based modeへfallbackしません。

---

# 18. 推奨デモシナリオ

## Demo 1 — 単純意味理解

```text
「青いカードを指して」
```

## Demo 2 — 視覚依存

カードを並べ替えて:

```text
「一番左のカードを指して」
```

## Demo 3 — 再配置適応

同じ「青を指して」で青カード位置を移動。

固定された `BLUE=90°` ではなく、現在画像から物理位置を再計算していることを示す。

---

# 19. 本番15分前チェック

## Modal

```text
□ modal deploymentが有効
□ proxy key/secret環境変数あり
□ endpoint URL正しい
□ 1回VLMテストしてwarm-up済み
□ targetが正しい
```

## EOS RP

```text
□ USB認識
□ カード3枚とservo pivotが映る
□ WB/露出が安定
□ カメラ位置固定
□ バッテリー/AC電源十分
```

## Pico/UART

```text
□ Pico USB給電
□ USB-UART COM番号正しい
□ PING/PONG
□ 60/90/120°動作
```

## SG90

```text
□ 外部5V
□ 共通GND
□ 指示針の干渉なし
□ 端点へ押し付けていない
```

## Vision

```text
□ RED検出
□ BLUE検出
□ GREEN検出
□ pivot設定
□ 左右方向正しい
```

---

# 20. トラブル時の切り分け順

動かないときは上から順に確認。

```text
1 Modal API
2 EOS RP capture
3 OpenCV target detection
4 geometry
5 PC→USB-UART
6 Pico UART
7 Pico PWM
8 SG90 power/mechanics
```

「全部を同時に直そうとしない」。

---

# 21. 実験記録

各EXPで最低限残す:

```text
Date
Git commit SHA
PC
Python version
Modal deployment
Model
Cold-start time
Warm request time
Camera index
Image resolution
HSV
Pivot x/y
Servo pulse range
Servo safe range
COM port
Success/Fail
Observed failure
Change made
```

秘密情報は記録しない。

---

# 22. 現時点での最初の作業

最初にやるのはハード配線ではありません。

```text
PRE-001
Modal VLM smoke test
```

順序:

```text
1 repository clone
2 Python venv
3 modal token new
4 model download to Volume
5 modal deploy
6 proxy token
7 静止画2枚で「一番左」テスト
8 PASSを記録
```

これがPASSしてからPicoへ進みます。

---

# 23. 主要な一次情報

確認日: 2026-09-28

## Modal

- FastAPI endpoint:
  https://modal.com/docs/sdk/py/latest/fastapi_endpoint
- Proxy Tokens:
  https://modal.com/docs/cli/latest/workspace
- App / autoscaler parameters:
  https://modal.com/docs/sdk/py/latest/App
- Volumes:
  https://modal.com/docs/sdk/py/latest/Volume
- CLI token:
  https://modal.com/docs/cli/latest/token
- deploy:
  https://modal.com/docs/cli/latest/deploy
- pricing:
  https://modal.com/pricing

## Qwen3-VL

- Qwen3-VL-2B-Instruct:
  https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct

## Raspberry Pi Pico H

- Pico series documentation:
  https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html
- Official pinout PDF:
  https://datasheets.raspberrypi.com/pico/Pico-2-Pinout.pdf
- MicroPython installation:
  https://www.raspberrypi.com/documentation/microcontrollers/micropython.html
- MicroPython RP2 UART/PWM:
  https://docs.micropython.org/en/latest/rp2/quickref.html

## Canon EOS RP

- EOS RP specifications:
  https://personal.canon.jp/product/camera/eos/rp/spec
- EOS Webcam Utility Pro:
  https://personal.canon.jp/product/camera/software/webcam-utility

## SG90

- TowerPro SG90 Analog:
  https://towerpro.com.tw/product/sg90-analog/
- TowerPro SG90 Digital:
  https://towerpro.com.tw/product/sg90-7/
- TowerPro SG90 360° version:
  https://towerpro.com.tw/product/sg90-360-degree-continuous-rotation-servo/

---

# 24. 設計変更ルール

この手順書と異なる実装を採用する場合は、先にGitHubへ理由を記録する。

特に次は無断で変えない。

- Modal API response contract
- fail-closed rule
- SG90の外部給電
- 共通GND
- servo safe range
- VLMに直接servo angleを出させない設計
