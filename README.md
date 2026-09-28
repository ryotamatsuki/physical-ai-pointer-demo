# Physical AI Pointer Demo

EOS RP + Modal上のVLM + Raspberry Pi Pico H + SG90を使い、自然言語で指定した色カードを実物の指示針で指す卓上Physical AIデモです。

## Current architecture

VLM推論はGoogle Colabではなく、**Modalの常設デプロイ型GPUバックエンド**へ分離します。

```text
[Windows PC]
EOS RP → 1フレーム取得
      +
自然言語指示
      ↓
JPEG化 / HTTPS POST
      ↓
[Modal]
authenticated web endpoint
      ↓
Qwen3-VL-2B-Instruct / T4 GPU
      ↓
RED / BLUE / GREEN / NONE
      ↓
[Windows PC]
OpenCVで対象カード中心(x, y)
      ↓
画像座標 → サーボ角度
      ↓
USB-UART (3.3V TTL)
      ↓
UART0 / Raspberry Pi Pico H
      ↓
GP15 / SG90 → 紙の指示針
```

## Build manual

購入・配線・Modal・Windows・Pico・EOS RP・OpenCV・校正・統合・本番前チェックまでの完全手順:

**[Modal方式 Physical AI Pointer Demo — 実機構築・セットアップ完全手順書](docs/04_modal_demo_machine_build_manual.md)**

短い工程一覧は [End-to-end setup](docs/02_full_setup.md)、クラウド設計は [Modal architecture](docs/03_modal_architecture.md) を参照してください。

## Why Modal

- Colabの手動起動・GPU選択・一時URL発行に依存しない。
- デプロイ後のHTTPS endpointをWindows PCから直接呼び出せる。
- GPUコンテナはscale-to-zeroし、展示前の1回目の呼び出しでwarm-upできる。
- モデルをModal Volumeへキャッシュし、毎回Hugging Faceから取得しない。
- ローカルPCはEOS RP、OpenCV、幾何計算、Pico制御だけを担当する。

## Why dedicated USB-UART

本番制御ではPicoのMicro USB REPLをSerial command channelとして兼用せず、3.3V TTL USB-UART adapterを使用します。

- Pico Micro USB: 給電、MicroPython書込み、Thonny
- USB-UART: `PING / CENTER / ANGLE` コマンド専用
- UART0: GP0 TX / GP1 RX
- Servo PWM: GP15

これによりThonny/REPLと本番Serial通信を分離します。

## Security / fail-safe

Modal endpointはproxy authを使用する。

秘密情報はGitHubへ保存せず、Windows環境変数から読む。

```text
MODAL_PROXY_KEY
MODAL_PROXY_SECRET
```

VLM APIがタイムアウト、認証失敗、不正な応答、`NONE`を返した場合は**サーボを動かさない**。

AIモードで自動的にルールベース制御へfallbackしない。デモの意味が変わるため、fallbackを行う場合は別モードとして明示する。

## Responsibility

| Component | Responsibility |
|---|---|
| EOS RP | 現実世界のRGB観測 |
| Windows PC | 撮影、OpenCV、角度計算、HTTPS、Serial |
| Modal web endpoint | 認証、入力検証、VLM呼び出し |
| Qwen3-VL | 画像＋自然言語から対象カードを選択 |
| OpenCV | 選択された色カードの中心を精密測定 |
| USB-UART | PCとPicoの専用制御通信 |
| Pico H | 角度命令を受けPWM生成 |
| SG90 | 物理的な指示針駆動 |

本デモはVLAそのものではなく、**VLM + classical controlによるPhysical AIデモ**です。

## Experiment roadmap

| ID | Test | Pass criterion |
|---|---|---|
| PRE-001 | Modal VLM smoke test | 静止画＋自然言語→正しい対象色 |
| EXP-001 | Pico basic | LED点滅 |
| EXP-002 | Servo basic | 60/90/120°移動 |
| EXP-003 | PC → USB-UART → Pico | PC指定角へ移動 |
| EXP-004 | EOS RP | OpenCV連続取得 |
| EXP-005 | Vision | RGBカード中心検出 |
| EXP-006 | Geometry | Pointer reaches card centers |
| EXP-007 | EOS RP → Modal | 実カメラ画像＋指示→対象色 |
| EXP-008 | Integration | 自然言語指示で実機が対象を指す |
| EXP-009 | Repositioning | カード移動後も追従 |
| EXP-010 | Language generalization | 「一番左」等へ対応 |

## Repository structure

```text
modal_backend.py   Modal GPU/VLM backend
docs/              設計・セットアップ・完全手順書
experiments/       実験計画と結果
pc/                Windows PC側
pico/              Pico H側MicroPython
assets/            配線写真・セットアップ写真
```

## First step

実機を組む前に [PRE-001](experiments/PRE-001_modal_vlm_smoke_test.md) を実施し、ModalへデプロイしたVLMが静止画1枚で動くことを確認します。
