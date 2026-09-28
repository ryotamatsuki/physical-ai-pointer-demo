# EXP-012 — Cold restart / reproducibility

## Objective

PC、EOS RP、Pico、SG90、Modal運用を一度完全停止した後、手順書だけで再構築・再開できることを確認する。

## Preconditions

EXP-011 PASS。

## Procedure

1. PC側プログラム終了。
2. Pico / SG90 / EOS RPを電源OFF。
3. Modalを通常scale-to-zero状態へ戻す。
4. 可能ならPCを再起動。
5. READMEとrunbookだけを見て再開。
6. environment reportを取得。
7. PING、camera、vision、VLM、統合を順に確認。

## Pass criterion

- 手順書以外の隠れた操作なしで再開できる
- model revision一致
- calibration値が復元される
- COM/camera indexを確認できる
- 代表デモ3シナリオが3/3成功

## Status

BLOCKED
