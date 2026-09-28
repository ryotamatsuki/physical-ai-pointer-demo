# 01. System overview

## Goal

自然言語で「青を指して」「一番左のカードを指して」などと指示すると、EOS RPで撮影した現在の配置をQwen3-VLが解釈し、SG90に取り付けた紙の指示針が対象カードを指す。

## Current architecture: Windows + Google Colab hybrid

```text
User instruction
      +
EOS RP image
      ↓
Windows PC
      ↓ image + instruction
Internet
      ↓
Google Colab GPU
Qwen3-VL-2B-Instruct
      ↓ target class
Internet
      ↓
Windows PC / OpenCV
      ↓ target center (x, y)
geometry
      ↓ servo angle
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
| Windows PC | Camera capture, OpenCV, geometry, Pico serial control |
| Google Colab | GPU execution environment for the VLM |
| Qwen3-VL | Interpret natural language + image and select intended target |
| OpenCV | Measure the selected card center precisely |
| Geometry | Convert target image position to servo angle |
| Pico H | Receive angle commands and generate PWM |
| SG90 | Physical actuation |

## Design decision

VLM推論をColabへ移した理由は、実機側ノートPCの負荷を抑えながら、EOS RPやPicoのようなローカルUSB機器はWindows側で確実に扱うため。

Colabは「判断」だけを行い、USBデバイスを直接制御しない。

## Why not make the VLM output the servo angle directly?

最初のデモでは、AIの意味理解と低レベル制御を分離する。

- VLM: 何を指すか
- OpenCV: どこにあるかを精密計測
- Geometry: 何度動かすか
- Pico: PWMを出す

これにより誤動作時の切り分けが容易になる。

## Definition

このバージョンは **VLM + classical control による Physical AI**。VLAそのものとは呼ばない。
