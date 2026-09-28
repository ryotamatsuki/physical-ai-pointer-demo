# EXP-009 — Repositioning and scene freshness

## Objective

現在画像に応じて動作が変わること、およびModal推論中にsceneが変わった場合は古い判断で動かないことを確認する。

## Pass criterion

A. 指示前に配置変更:
- 異なる5配置で「青を指して」5/5。
- 「一番左」も配置に応じて選択色が変わる。

B. 推論中に配置変更:
- カードを十分動かす、または左右順を入れ替える。
- scene changedとしてANGLE送信なし。
- PWM STOPを試行。
- 新しい指示で再撮影してからのみ再開。

## Status

BLOCKED by EXP-008
