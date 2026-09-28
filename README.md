# Physical AI Pointer Demo

EOS RP + VLM + Raspberry Pi Pico H + SG90 を使い、自然言語で指定した色カードを実物の指示針で指す、卓上 Physical AI デモです。

## 目的

このリポジトリでは、Physical AI の基本ループ **Perceive → Reason → Act** を小型の実機で再現します。

- **Perceive**: EOS RP で色カードと指示針を撮影
- **Reason**: VLM が自然言語の指示と画像から対象カードを判断
- **Act**: PC が対象座標を角度へ変換し、Pico H 経由で SG90 を制御

本デモは VLA そのものではなく、**VLM + classical control による Physical AI デモ**として設計します。

## システム構成

```text
自然言語指示
    +
EOS RP 画像
    ↓
VLM
    ↓
対象カードを選択
    ↓
OpenCV で対象中心座標を検出
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

## 開発方針

統合を急がず、各層を単体試験してから次へ進みます。

| Experiment | 内容 | 合格条件 |
|---|---|---|
| EXP-001 | Pico 単体 | LED 点滅 |
| EXP-002 | SG90 制御 | 60° / 90° / 120°へ移動 |
| EXP-003 | PC → Pico | PC 指定角へ移動 |
| EXP-004 | EOS RP | OpenCV で連続取得 |
| EXP-005 | 色検出 | 赤・青・緑の中心座標を取得 |
| EXP-006 | 座標 → 角度 | 各カード中心を指せる |
| EXP-007 | VLM | 自然言語 → 対象カード |
| EXP-008 | 統合 | 「青を指して」で青へ |
| EXP-009 | 配置変更 | カード移動後も追従 |
| EXP-010 | 言語一般化 | 「一番左」等へ対応 |

## ディレクトリ

```text
docs/          セットアップ・設計資料
experiments/   実験計画と結果
pc/            Windows PC 側 Python
pico/          Pico H 側 MicroPython
assets/        配線図・写真・スクリーンショット
```

## 安全上の注意

- SG90 を Pico の 3.3V 端子から給電しない。
- SG90 は仕様に合った外部 5V 電源を使用し、Pico と GND を共通化する。
- 初回は紙の指示針を外した状態で 60° / 90° / 120°程度の安全域を確認する。
- サーボの可動範囲は個体差があるため、最初から 0° / 180°を前提にしない。

## Current status

Repository initialized. Start with [EXP-001](experiments/EXP-001_pico_basic.md).
