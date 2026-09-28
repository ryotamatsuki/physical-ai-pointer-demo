# Colab VLM

このディレクトリは、VLM推論をGoogle Colab GPUへ分離するためのものです。

## First step

1. `qwen3_vl_server.ipynb` をGoogle Colabで開く。
2. **ランタイム → ランタイムのタイプを変更 → T4 GPU** を選ぶ。
3. 上からセルを実行する。
4. Qwen3-VL-2B-Instructがロードされたことを確認する。
5. 赤・青・緑カードの写真1枚をアップロード。
6. 「一番左のカードを指して」で正しい色が返ることを確認する。
7. 成功後だけGradioサーバーセルを実行する。
8. 表示された `https://...gradio.live` URLを `pc/config.py` の `COLAB_GRADIO_URL` に設定する。

## Responsibility split

```text
Windows PC
  EOS RP / OpenCV / geometry / serial
          ↓ image + language
       Internet
          ↓
Google Colab GPU
      Qwen3-VL
          ↓ target color
       Internet
          ↓
Windows PC
          ↓
Pico H → SG90
```

ColabはUSB機器を直接制御しない。EOS RPとPico HはWindows PCへ接続する。
