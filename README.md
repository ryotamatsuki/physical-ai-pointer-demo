# Physical AI Pointer Demo

EOS RP + Google Colab上のVLM + Raspberry Pi Pico H + SG90 を使い、自然言語で指定した色カードを実物の指示針で指す卓上 Physical AI デモです。

## 目的

Physical AI の基本ループ **Perceive → Reason → Act** を小型の実機で再現します。

- **Perceive**: Windows PCにつないだEOS RPで色カードを撮影
- **Reason**: Google Colab上のQwen3-VLが、画像＋自然言語から対象カードを判断
- **Act**: Windows PCが対象座標をサーボ角へ変換し、Pico H経由でSG90を制御

本デモはVLAそのものではなく、**VLM + classical control による Physical AI デモ**です。

## Architecture

```text
[Windows PC]
EOS RP → 1フレーム取得
     +
自然言語指示
     ↓ Internet
[Google Colab GPU]
Qwen3-VL-2B-Instruct
     ↓
RED / BLUE / GREEN / NONE
     ↓ Internet
[Windows PC]
OpenCVで対象中心座標
     ↓
画像座標 → サーボ角度
     ↓
USB Serial
     ↓
Raspberry Pi Pico H
     ↓
SG90
     ↓
紙の指示針
```

この構成では古いノートPCにVLM推論を負わせず、GPU推論だけをColabへ分離します。

## First step

**実機を組む前にColab単体を確認します。**

1. [colab/qwen3_vl_server.ipynb](colab/qwen3_vl_server.ipynb) をGoogle Colabで開く。
2. ランタイムを **T4 GPU** にする。
3. 上からセルを実行する。
4. 赤・青・緑カードを並べた写真を1枚アップロードする。
5. 「一番左のカードを指して」で正しい色が返ることを確認する。

ここが成功したらPico/SG90側へ進みます。

## Experiment roadmap

| Experiment | 内容 | 合格条件 |
|---|---|---|
| PRE-001 | Colab VLM単体 | 画像＋指示→対象色 |
| EXP-001 | Pico単体 | LED点滅 |
| EXP-002 | SG90制御 | 60° / 90° / 120°へ移動 |
| EXP-003 | PC → Pico | PC指定角へ移動 |
| EXP-004 | EOS RP | OpenCVで連続取得 |
| EXP-005 | 色検出 | 赤・青・緑の中心座標を取得 |
| EXP-006 | 座標 → 角度 | 各カード中心を指せる |
| EXP-007 | PC → Colab VLM | Windowsから画像＋指示→対象色 |
| EXP-008 | 統合 | 自然言語指示で実機が対象を指す |
| EXP-009 | 配置変更 | カード移動後も追従 |
| EXP-010 | 言語一般化 | 「一番左」等へ対応 |

## Repository structure

```text
colab/         Qwen3-VL GPU推論・Gradio API
docs/          セットアップ・設計資料
experiments/   実験計画と結果
pc/            Windows PC側 Python
pico/          Pico H側 MicroPython
assets/        配線図・写真・スクリーンショット
```

## Safety

- SG90をPicoの3.3V端子から給電しない。
- SG90は仕様に合った外部5V電源を使用し、PicoとGNDを共通化する。
- 初回は紙の指示針を外した状態で安全域を確認する。
- サーボの可動範囲には個体差があるため、最初から0°/180°を使用しない。

## Current status

Architecture changed to **Windows + Google Colab hybrid**.

Start with the Colab smoke test, then [EXP-001](experiments/EXP-001_pico_basic.md).
