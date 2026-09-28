# EXP-007 — Colab VLM target selection

## Objective

Google Colab上のQwen3-VLへ画像と自然言語を送り、対象カードを選択できることを確認する。

## Architecture under test

```text
Windows PC
  image + instruction
        ↓ Internet
Google Colab / Qwen3-VL
        ↓
RED / BLUE / GREEN / NONE
```

## Pass criterion

最低限、次を満たす。

- 「赤を指して」→ RED
- 「青を指して」→ BLUE
- カード配置を変更後「一番左」→ 現在左のカード
- 同じ配置で指示を変えると出力も変わる
- Windows側 `pc/vlm_test.py` からColab APIへ接続して同じ結果が得られる

## Important

色名だけのテストでは画像を無視して正解できるため、位置関係を問うテストを必須とする。

ColabのGradio共有URLはランタイム再起動等で変わり得るため、実験ごとに使用URLと日時を記録する。

## Status

NOT STARTED
