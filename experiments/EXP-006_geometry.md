# EXP-006 — Image coordinate to servo direction

## Objective

カード中心の画像座標を安全なサーボ指令へ変換し、到達不能条件を動作へ丸めない。

## Preconditions

EXP-003 and EXP-005 PASS。

## Calibration

必須:
- fixed frame width/height
- PIVOT_X/Y
- SERVO_MIN/MAX
- ANGLE_SIGN
- ANGLE_SCALE
- ANGLE_OFFSET
- measured command→physical direction from EXP-002

## Pass criterion

- 赤青緑×3配置 = 9/9。
- 評価は「針の延長線が対象カード内部を通る」。
- 可動域外targetはANGLE送信なし。
- pivot近傍targetはANGLE送信なし。
- NaN/InfはANGLE送信なし。
- calibrationと異なる解像度はANGLE送信なし。
- 左右端で系統誤差が大きければhomography/レンズ補正を検討する。

## Status

BLOCKED

## Calibration values

```text
CALIBRATION_FRAME_WIDTH=
CALIBRATION_FRAME_HEIGHT=
PIVOT_X=
PIVOT_Y=
SERVO_CENTER=
ANGLE_SIGN=
ANGLE_SCALE=
ANGLE_OFFSET=
SERVO_MIN=
SERVO_MAX=
```
