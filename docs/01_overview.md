# 01. System overview

## Goal

自然言語で「青を指して」「一番左のカードを指して」などと指示すると、EOS RPで撮影した現在の配置をVLMが解釈し、SG90に取り付けた紙の指示針が対象カードを指す。

## Architecture

```text
User instruction
      +
EOS RP image
      ↓
Windows PC
      ↓ JPEG + HTTPS
Modal authenticated endpoint
      ↓
Qwen3-VL-2B-Instruct / T4
      ↓ target class
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

## Design principles

1. **AI判断と低レベル制御を分離する**
   - VLM: 何を指すか
   - OpenCV: その対象が画像のどこか
   - Geometry: 何度動かすか
   - Pico: PWMを出す

2. **クラウド障害時は動かさない**
   - timeout
   - authentication failure
   - invalid JSON
   - target = NONE
   - target not detected by OpenCV

   上記はいずれもサーボ命令を送らない。

3. **秘密情報をリポジトリへ保存しない**
   - Modal proxy key/secretはWindows環境変数。
   - GitHubにはendpoint URLのみ設定可能だが、秘密情報は置かない。

4. **展示時のcold startを制御する**
   - GPUモデルはscale-to-zero。
   - model cacheはModal Volume。
   - model containerのscaledown windowは15分を初期値とする。
   - 展示直前にPRE-001相当の1回の推論を実行してwarm-upする。

## Definition

このバージョンは **VLM + classical control による Physical AI**。VLAそのものとは呼ばない。
