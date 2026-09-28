# 03. Modal architecture

## Purpose

Google Colabのセッション寿命や一時URLに依存せず、展示時にWindows PCから固定のデプロイ先へVLM推論を依頼できる構成にする。

## Components

### Windows PC

担当:
- EOS RPからフレーム取得
- JPEG縮小・圧縮
- Modal API呼び出し
- OpenCVで対象色カード中心検出
- 画像座標→サーボ角度
- Pico HへのSerial通信

### Modal

担当:
- HTTPS endpoint
- proxy auth
- リクエスト検証
- Qwen3-VL推論
- 出力を4値に正規化

### Pico H

担当:
- `ANGLE <degree>` を受信
- SG90へ50Hz PWM出力
- 安全角度へclamp

---

## Modal resources

予定値:

```text
App:     physical-ai-pointer-vlm
Model:   Qwen/Qwen3-VL-2B-Instruct
GPU:     T4
Volume:  physical-ai-pointer-model-cache
Max GPU containers: 1
Min GPU containers: 0
Scaledown window: 900 sec
```

モデルファイルはVolumeへ事前取得する。

```powershell
modal run modal_backend.py::download_model
modal deploy modal_backend.py
```

## Authentication

Web endpointはproxy authを必須にする。

Windows側の秘密情報:

```text
MODAL_PROXY_KEY=wk-...
MODAL_PROXY_SECRET=ws-...
```

HTTP header:

```text
Modal-Key: <MODAL_PROXY_KEY>
Modal-Secret: <MODAL_PROXY_SECRET>
```

キーはコード、config.py、実験ログ、スクリーンショットへ残さない。

---

## API contract v1

### Request

HTTPS POST。

```json
{
  "schema_version": "1",
  "request_id": "uuid",
  "instruction": "一番左のカードを指して",
  "image_b64": "<base64 encoded JPEG>"
}
```

制約:
- instruction: 200文字以下
- image: JPEG
- PC側で最大幅1280pxへ縮小
- JPEG quality初期値85

### Response: success

```json
{
  "schema_version": "1",
  "request_id": "uuid",
  "target": "BLUE",
  "model": "Qwen/Qwen3-VL-2B-Instruct"
}
```

`target` は次の4値だけ。

```text
RED
BLUE
GREEN
NONE
```

### Client acceptance rule

Windows PCは以下をすべて満たす場合のみ後段へ進む。

- HTTP 200
- JSONとしてparse可能
- schema_version = "1"
- request_id一致
- targetが許可4値
- target != NONE

一つでも満たさなければ**サーボを動かさない**。

---

## VLM prompt contract

モデルにはカードの物理座標やサーボ角度を求めさせない。

役割は対象選択のみ。

例:

```text
画像には赤・青・緑のカードがあります。
ユーザー指示:
「一番左のカードを指して」

画像と指示の両方を確認し、
RED / BLUE / GREEN / NONE の1語だけを返す。
```

これにより、VLMの意味理解とOpenCVの位置計測を分離する。

---

## Cold start policy

通常:
- min_containers = 0
- scaledown_window = 900

これにより常時GPUを保持しない。

展示開始前:
1. テスト画像で1回分類。
2. 正答を確認。
3. 15分以内に本番を開始。

展示が長時間の場合は、必要に応じてautoscaler設定を変更する。ただし常時warm化はコストと引き換えになるため、最初の実装では採用しない。

---

## Failure policy

| Failure | Action |
|---|---|
| HTTP timeout | stop / no servo command |
| 401/403 | stop / auth check |
| 5xx | stop / retry manually |
| malformed JSON | stop |
| target=NONE | stop |
| OpenCV cannot find returned color | stop |
| calculated angle out of safety range | clamp or stop |

AIモードでは自動的にRULEモードへ切り替えない。

---

## Observability

実験ログへ残す:
- request_id
- timestamp
- instruction
- target
- API round-trip time
- OpenCV target coordinate
- calculated servo angle
- final Pico response

残さない:
- proxy key
- proxy secret
- base64 image body

代表画像だけ `assets/` に手動保存する。

---

## Future extensions

API契約を維持すれば、VLMを変更してもWindows側を大きく変えない。

候補:
- Qwen3-VL 4B
- 別VLM
- VLA-style policy
- World Model service

最初のバージョンではQwen3-VL 2Bのみを対象とする。
