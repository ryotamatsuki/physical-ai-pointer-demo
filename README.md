# Physical AI Pointer Demo

EOS RP + Modal上のVLM + Raspberry Pi Pico H + SG90を使い、自然言語で指定したカードを実物の指示針で指す卓上Physical AIデモです。

## Current architecture

```text
[Windows PC]
EOS RP → continuous latest-frame capture
      +
natural-language instruction
      ↓ freeze fresh frame
ROI / unique-card precheck
      ↓
JPEG / authenticated HTTPS
      ↓
[Modal T4]
Qwen3-VL-2B-Instruct
      ↓ strict exact token only
RED / BLUE / GREEN / NONE
      ↓
[Windows PC]
re-observe current scene
      ↓
scene unchanged?
      ↓ yes
OpenCV unique target center
      ↓
geometry: reject unreachable / uncalibrated target
      ↓
sequence-numbered USB-UART command
      ↓
[Pico H]
range check + ACK
      ↓
GP15 PWM → SG90 → pointer
```

本デモはVLAそのものではなく、**VLM + classical controlによるPhysical AIデモ**です。

## Astra review hardening

外部レビューを受け、公開実演前に問題になりやすい経路を以下のように強化しました。

- VLM出力は `RED/BLUE/GREEN/NONE` の完全一致のみ受理。部分文字列は禁止。
- カメラはバックグラウンドで連続取得し、指示確定後の最新frameを使用。
- Modal推論後にsceneを再観測し、カード移動・並び替えがあれば動作中止。
- OpenCVは台座ROI、面積、縦横比、矩形充足率でカード候補を検証。
- 同色候補が複数、または欠落なら動作中止。
- 到達不能角を30/150°へ丸めず、PC側で拒否。
- 校正解像度、pivot近傍、NaN/Infも拒否。
- Pico通信はsequence付きACKを必須化。
- `STOP` commandでPWMを停止可能。
- PicoのUART受信長を制限し、範囲外/非有限角を拒否。
- Modal request/image型・JPEG・寸法をサーバー側でも検証。
- Qwenモデルrevisionをmodel cache作成時に記録。
- 公開実演時だけ `min_containers=1` でwarm保持するrunbookを追加。

## Documentation

- [Complete build manual](docs/04_modal_demo_machine_build_manual.md)
- [Public demo runbook](docs/05_public_demo_runbook.md)
- [Astra review response](docs/06_astra_review_response.md)
- [Modal architecture](docs/03_modal_architecture.md)
- [Experiment roadmap](experiments/README.md)

## Why Modal

- Colabの手動起動・一時URLに依存しない。
- PCにローカルGPUを要求しない。
- 固定HTTPS endpoint + proxy auth。
- model cacheはModal Volume。
- 通常時はscale-to-zero、本番時間帯だけwarm保持可能。

ModalのWeb Functionはproxy authenticationをサポートし、Proxy Tokenは `Modal-Key` / `Modal-Secret` ヘッダーで送信できます。

## Control transport

現在の本線は3.3V TTL USB-UARTです。

- Pico Micro USB: 給電 / MicroPython / Thonny
- USB-UART: production command channel
- UART0: GP0 TX / GP1 RX
- Servo: GP15 PWM

USB CDCでも構成可能ですが、現段階ではREPLと制御路を分離してトラブル切り分けを優先します。未購入時に簡素化する場合はEXP-003前に方式を決め、本番直前には変更しません。

## Fail-safe semantics

System fault:
- Modal/network/auth/format error
- stale camera
- scene changed during inference
- missing/duplicate color card
- unsafe geometry
- Pico ACK error

→ 新しいANGLEは送らず、可能ならPWM STOP。

Semantic `NONE`:
→ 正常な「対象を一意に選べない」結果。新しいANGLEを送らず、自動recenterもしない。

機械的な異常:
→ ソフトウェアより先にSG90の外部5Vを物理的に切る。

## Experiment roadmap

独立リスクは並行して潰します。

```text
PRE-001 → PRE-002 ───────────────┐
EXP-001 → EXP-002 → EXP-003 ────┼→ EXP-006/007 → EXP-008 → 009 → 010 → 011 → 012
EXP-004 → EXP-005 ───────────────┘
```

EOS RPのOpenCV連続取得（EXP-004）はPicoを待たず、早期に確認してよい。

## First actions

1. PRE-001: Modal strict-token smoke test
2. PRE-002: static language/ambiguity evaluation
3. EXP-004: EOS RP 5-minute capture test
4. EXP-001〜003: Pico / servo / ACK path

実機校正値は初期値を信頼せず、必ず実測して `pc/config.py` とexperiment logへ記録します。
