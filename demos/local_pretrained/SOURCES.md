# 出典

確認日：2026-10-17。講義資料の転載は行わず、今回の配線・説明・コードを新規作成しました。

- 松尾・岩澤研 Physical AI 基礎編 第1回資料、7・21ページ：現実世界の認識・判断・動作とパイプライン。
- Physical AI 応用編1 第1回講義スライド、57ページ：AI画像認識とルールベース制御の組み合わせ。
- OpenCV Zoo YOLOX-sモデル・前処理・後処理・ライセンス。
  https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox
  取得元リビジョンは third_party/opencv_zoo_revision.txt、モデルのSHA256は models/model_manifest.json。
- YOLOXオリジナル実装。
  https://github.com/Megvii-BaseDetection/YOLOX
- COCOクラス一覧・COCO8の説明と配布URL。
  https://docs.ultralytics.com/datasets/detect/coco8/
- TrashNet元作者のデータセット説明。
  https://github.com/garythung/trashnet
- Raspberry Pi Pico公式資料。
  https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html
- MicroPythonの導入・PWM・mpremote。
  https://micropython.org/download/RPI_PICO/
  https://docs.micropython.org/en/latest/library/machine.PWM.html
  https://docs.micropython.org/en/latest/reference/mpremote.html
- Canon EOS Webcam Utility Proの無料基本機能と対応機種。
  https://personal.canon.jp/product/camera/software/webcam-utility-pro
  https://app.ssw.imaging-saas.canon/app/ja/ewup.html
- Gemini画像理解と構造化出力（発展版のAPIコード）。
  https://ai.google.dev/gemini-api/docs/image-understanding
  https://ai.google.dev/gemini-api/docs/structured-output

## 実装の由来

third_party/opencv_yolox_reference.py と opencv_demo_reference.py は、上記リビジョンのOpenCV Zooファイルを変更せず同梱しています。
detector.pyは、それに対応するRGB変換・640角への左上詰め・114でのパディングを行います。
新規作成したPC制御、Pico制御、教材説明は同梱ライセンスの条件で再利用できます。

このデモは、既存の画像認識と固定したモーター制御を組み合わせたものです。モーターの制御方策をデータから学習するVLAや模倣学習の再現ではありません。
