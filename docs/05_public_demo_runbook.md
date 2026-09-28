# 05. Public demo runbook

公開実演時の運用手順。通常開発時のscale-to-zeroと、本番時間帯のwarm保持を分離する。

## Before deployment

コード・モデル・依存関係を本番当日に更新しない。

確認:
- PRE-001 / PRE-002 PASS
- EXP-003 / 004 / 005 / 006 / 007 PASS
- EXP-011 soak test PASS
- EXP-012 cold restart PASS

## Warm deployment

PowerShellで本番時間帯だけ:

```powershell
$env:MODAL_MIN_CONTAINERS="1"
$env:MODAL_SCALEDOWN_WINDOW="900"
modal deploy modal_backend.py
```

この設定はGPUをwarm状態に保つため、通常開発時より費用が発生する。

deploy後、必ず実際の画像で1回成功させる:

```powershell
python pc\vlm_test.py --image C:\path\known-good.jpg --instruction "一番左のカードを指して" --cold-start
```

確認:
- HTTP成功
- target正解
- model_revisionが記録値と一致
- round-trip timeが想定範囲
- inference timeが想定範囲

## 15 minutes before audience

- 会場Wi-FiでModal endpoint到達
- EOS RP 5分以上連続取得済み
- WB / exposure / focus固定
- ROI内に余計な赤青緑物体がない
- USB-UART PING/PONG
- 60/90/120°試験
- 物理的なサーボ電源スイッチ/抜きやすいコネクタを確認
- 指示針がどの角度でも障害物に触れない
- 観客向け表示が最後列から読める

## During demo

推奨:
- 1回目: 「青いカードを指して」
- 2回目: カード配置を変えて「一番左」
- 3回目: 色カード上の意味図柄を使い「雨の日に使うもの」
- 4回目: 存在しない/曖昧な指示でNONE→動かない

禁止:
- 推論待ち中にカードへ触る
- 失敗時に黙って固定角度制御へ切り替える
- 本番中のdeploy / pip update / model download

## Fault handling

System fault:
- Modal timeout/auth/5xx
- stale camera
- scene changed during inference
- duplicate/missing color card
- unsafe angle
- Pico ACK failure

→ PWM STOPを試行し、画面へSTOP理由を表示。原因を直してから再実行。

Semantic NONE:
→ 新しいANGLEは送らない。自動recenterしない。

Mechanical abnormality:
→ ソフトウェア操作より先にSG90の外部5V電源を物理的に切る。

## After demo

通常のscale-to-zeroへ戻す:

```powershell
$env:MODAL_MIN_CONTAINERS="0"
modal deploy modal_backend.py
```

実験ログへ:
- Git commit SHA
- model revision
- environment report
- total requests / successes / stops
- failure reasons
- representative failure images
を記録する。
