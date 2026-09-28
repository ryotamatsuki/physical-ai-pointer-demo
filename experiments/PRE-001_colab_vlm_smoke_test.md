# PRE-001 — Colab VLM smoke test

## Objective

実機を組む前に、Google ColabのGPU上でQwen3-VL-2B-Instructが正常に動作し、画像＋自然言語から対象カードを選択できることを確認する。

## Why first?

今回の構成で最も計算負荷・外部依存が大きい部分はVLM推論である。ここを最初にPASSさせてから、Pico、サーボ、カメラへ進む。

## Pass criterion

- ColabでGPUが認識される。
- Qwen3-VL-2B-Instructがロードされる。
- 赤・青・緑カードを含む1枚の画像について推論できる。
- 「一番左のカードを指して」のように画像を見なければ解けない指示へ正しい色を返す。
- 結果が `RED / BLUE / GREEN / NONE` のいずれかに正規化される。

## Procedure

1. `colab/qwen3_vl_server.ipynb` をGoogle Colabで開く。
2. ランタイムをT4 GPUへ変更。
3. セルを上から実行。
4. `CUDA available: True` を確認。
5. モデルロード完了を確認。
6. 赤・青・緑カードを横に並べた写真を用意。
7. 写真をアップロード。
8. 「一番左のカードを指して」でテスト。
9. カード順を変えた別写真でも同じ指示を試す。
10. 結果をこのファイルへ記録。

## Status

NOT STARTED

## Record

- Date:
- Colab runtime:
- GPU:
- Model:
- Test image:
- Instruction:
- Expected:
- Actual:
- Inference time:
- Result: PASS / FAIL
