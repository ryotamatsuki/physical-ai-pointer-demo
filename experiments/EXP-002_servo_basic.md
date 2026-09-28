# EXP-002 — SG90 basic control and physical calibration

## Objective

SG90を安全に動かし、「nominal command angle」と実際の物理方向が同じとは限らないことを実測する。

## Preconditions

EXP-001 PASS。

## Safety before power

- SG90は外部5V。
- Picoと外部5VはGND共通。
- サーボ電源を手元で即座にOFFできる。
- 指示針は最初は外す。
- 可能ならサーボ電源近傍に470–1000 µF程度の電解コンデンサを追加。

## Procedure

1. 60 → 90 → 120 → 90を5回。
2. 異音、ストッパー接触、Pico reset、異常発熱を確認。
3. 紙の分度器等で、command 60 / 90 / 120に対する実際の方向を記録。
4. 必要なら30/150へ広げず、カード配置側を狭める。
5. 安全な実可動域を確定してconfigへ記録。

## Pass criterion

- 5回連続で異常なし。
- Pico reset 0。
- 継続的な唸り/拘束なし。
- 実測方向を記録済み。
- 公開デモで使う方向範囲が安全域内。
- 電源を物理的に即時OFFできる。

## Record

- Servo manufacturer/model:
- External 5V supply:
- Capacitor:
- Pulse range:
- Command 60 -> measured direction:
- Command 90 -> measured direction:
- Command 120 -> measured direction:
- Safe command range:
- Result:
