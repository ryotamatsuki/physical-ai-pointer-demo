# EXP-011 — Public-demo soak test

## Objective

公開実演と同じ構成を連続運用し、危険動作・通信ずれ・カメラ停止・Modal待ちの問題を事前検出する。

## Preconditions

EXP-008 / EXP-009 PASS。

## Procedure

100回の操作を実施する。

最低限:
- 固定色指示
- 左右中央
- カード再配置
- NONEケース
- 休止後の再実行
を混ぜる。

## Pass criterion

- 危険動作: 0
- 誤った対象への物理動作: 0
- system fault時のANGLE送信: 0
- 正常ケース成功: 98%以上
- Pico reset: 0
- カメラ停止: 0
- 継続的なサーボ異音/発熱: なし

失敗した全ケースについて画像・停止理由・ログを保存する。

## Status

BLOCKED
