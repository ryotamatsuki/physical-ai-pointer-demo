# EXP-007 — EOS RP → Modal VLM

## Objective

EOS RPから取得した実画像と自然言語指示を、Windows PCから認証付きModal endpointへ送り、対象カードを選択できることを確認する。

## Preconditions

- PRE-001 PASS
- EXP-004 PASS
- Modal endpoint deployed
- proxy auth configured on Windows

## Pass criterion

- 「赤を指して」→ RED
- 「青を指して」→ BLUE
- 配置変更後「一番左」→ 現在左のカード
- 同一配置で指示変更→出力も変化
- 10試行で通信エラーなし
- API失敗時にサーボ命令が送られない

## Record

- Endpoint deployment/version:
- Model:
- GPU:
- API latency:
- Cold-start latency:
- Warm latency:
- Result:
