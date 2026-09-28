# PRE-001 — Modal VLM smoke test

## Objective

実機を組む前に、Modal上のQwen3-VL-2B-Instructへ静止画＋自然言語を送り、正しい対象カードを返せることを確認する。

## Pass criterion

- model cache作成成功
- Modal deploy成功
- proxy auth付きHTTPS呼び出し成功
- RED / BLUE / GREEN / NONE の4値だけ返る
- 「一番左」のような画像依存指示で正答
- カード順を変えると同じ指示でも正答色が変わる
- 失敗時にWindows clientが非0終了する

## Procedure

1. Python環境構築。
2. `modal token new`。
3. `modal run modal_backend.py::download_model`。
4. `modal deploy modal_backend.py`。
5. classify endpoint URLを `pc/config.py` に設定。
6. Modal proxy tokenを作成。
7. `MODAL_PROXY_KEY` / `MODAL_PROXY_SECRET` をWindows環境変数へ設定。
8. 赤・青・緑カードの静止画を用意。
9. 実行:

```powershell
python pc\vlm_test.py --image C:\path\cards.jpg --instruction "一番左のカードを指して"
```

10. 配置を変えた別画像でも同じ指示を実行。

## Record

- Date:
- Commit:
- Modal App:
- Modal endpoint:
- Model:
- GPU:
- First request total time:
- Warm request total time:
- Image layout 1:
- Expected 1:
- Actual 1:
- Image layout 2:
- Expected 2:
- Actual 2:
- Result: PASS / FAIL
