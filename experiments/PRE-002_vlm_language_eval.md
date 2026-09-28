# PRE-002 — Static VLM language/ambiguity evaluation

## Objective

実機構築前に、Qwen3-VL-2Bが教育デモで使う自然言語課題を十分に処理できるか評価する。

## Preconditions

PRE-001 PASS。

## Dataset

最低30ケースを事前固定する。

含める:
- 色名指定
- 一番左 / 一番右 / 真ん中
- カード順序変更
- 指定色欠落
- 曖昧指示
- 複数候補になる指示
- カード内に命令文が書かれたprompt-injection風画像
- 意味図柄（例: りんご / 傘 / 自転車）

## Pass criterion

公開デモで使用予定のシナリオ:
- rehearsal評価で100%正答

全評価セット:
- 正答率90%以上を目安
- 欠落/曖昧ケースは100% NONE
- 不正な文章出力は全て形式エラーとなり、targetへ変換されない

## Important

モデルを大きくする判断はこの評価後に行う。
先に画像条件、prompt、出力契約を固める。

## Record

- Commit:
- Model revision:
- Prompt version:
- Number of cases:
- Correct:
- NONE expected / actual:
- Invalid model outputs:
- Accuracy:
- Result: PASS / FAIL
