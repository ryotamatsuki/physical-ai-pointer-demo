# EXP-007 — VLM target selection

## Objective

画像と自然言語の両方を使って対象カードを選択できることを確認する。

## Pass criterion

少なくとも次を満たす。

- 「赤を指して」→ RED
- 「青を指して」→ BLUE
- カード配置を変更後「一番左」→ 現在左のカード
- 同一配置で指示を変えると出力も変わる

## Important

色名だけのテストでは画像を無視しても正解できるため、位置関係を問うテストを必須とする。

## Status

NOT STARTED
