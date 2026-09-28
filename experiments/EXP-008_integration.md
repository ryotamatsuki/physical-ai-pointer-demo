# EXP-008 — Full integration

## Objective

EOS RP → Modal VLM → scene revalidation → OpenCV → geometry → Pico → SG90を一連で検証する。

## Preconditions

PRE-002, EXP-003, EXP-005, EXP-006, EXP-007 PASS。

## Normal pass criterion

固定配置で「赤」「青」「緑」を各3回、9/9で正しい方向。

## Fault injection

以下でANGLE送信が発生しないこと:
- Modal URL誤り
- proxy auth誤り
- target NONE
- card欠落
- duplicate color
- calibration resolution mismatch
- unreachable target
- stale/changed scene
- Pico ACK timeout

System faultではPWM STOPを試行する。

## Result

BLOCKED
