# 01. System overview

## Goal

自然言語で「青を指して」「一番左のカードを指して」などと指示すると、EOS RPで撮影した現在の配置をAIが解釈し、SG90に取り付けた紙の指示針が対象カードを指す。

## Architecture

```text
User instruction
      +
EOS RP image
      ↓
Qwen3-VL / VLM
      ↓
target class
      ↓
OpenCV
      ↓
target center (x, y)
      ↓
geometry
      ↓
servo angle
      ↓
USB serial
      ↓
Raspberry Pi Pico H
      ↓
SG90
      ↓
physical pointer
```

## Division of responsibilities

| Layer | Responsibility |
|---|---|
| EOS RP | Real-world RGB observation |
| VLM | Interpret natural language and select the intended target |
| OpenCV | Measure the target card center precisely |
| Geometry | Convert target image position to servo angle |
| Pico H | Receive angle commands and generate PWM |
| SG90 | Physical actuation |

## Why not make the VLM output the servo angle directly?

最初のデモでは、AIの意味理解と低レベル制御を分離する。これにより、誤動作時に「VLM」「画像処理」「角度計算」「通信」「サーボ」のどこに問題があるかを切り分けやすい。

## Definition

このバージョンは **VLM + classical control による Physical AI**。VLAそのものとは呼ばない。
