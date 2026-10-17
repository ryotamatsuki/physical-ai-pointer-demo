# 教材データと学習済みモデルの使い分け

## 結論

今回の目的なら「既存データで自分が学習する」工程自体を省き、学習済みモデルをそのまま使います。
データセットはAIに学習させるための画像と正解ラベル、学習済みモデルはその学習結果を保存したファイルです。
初回セットアップで自動取得するONNXファイルが後者です。モデルの使用にCOCO全画像のダウンロードは不要です。

| 選択肢 | 中身 | 今回の作業 | 向く目的 |
|---|---|---|---|
| COCOで学習済みのYOLOX-s（自動取得） | 80種類を検出する学習済み重み | 追加学習不要 | 最初の実物デモ |
| COCO8 | COCOから8枚の画像と検出ラベル | 任意で取得し、動作確認に使用 | データと正解ラベルの見方を知る教材 |
| TrashNet | ガラス・紙・段ボール・プラスチック・金属・その他ごみ、計2,527画像 | 既存画像で撮影は省けるが、分類器の学習・評価は残る | ごみ分類の学習実習 |
| 画像対応VLMのAPI | 画像と言葉を理解する学習済みモデル | APIキーと接続の設定。追加学習不要 | ペンやティッシュを言葉で選ぶ発展デモ |

COCO: https://cocodataset.org/
OpenCV Zooモデル: https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox
COCO8: https://docs.ultralytics.com/datasets/detect/coco8/
TrashNet: https://github.com/garythung/trashnet

## 標準モデルの対象を変えたい場合

coco_classes.jsonに80種類の名前があります。例：bottle、cup、banana、apple、mouse、remote、cell phone、scissors。
config.json の classes と meter_slots を3種類セットで書き換えると、学習をせずに対象を変更できます。
画像が小さい物、透明な物、反射する物は実演条件によって認識しにくいので、まずボトル・カップ・バナナを推奨します。
単に classes に pen、can、tissue と書いても、モデルにその種類が追加されるわけではありません。

## TrashNetを使う場合の考え方

物体を切り出す／背景を揃える、学習用と評価用を分ける、分類器を学習する、手元の実物で評価する、という工程が必要です。
TrashNetの素材分類は、市町村の収集ルールや汚れの有無などを含む分別判定と同じではありません。
デモを最小作業で成立させる今回のキットには、その学習工程は入れていません。

COCO8取得は download_examples.py を使用します。画像の再配布時は元の画像・データセットの条件を確認してください。
リポジトリにはクラス名と、モデル自動取得コード・固定URL・SHA256を保存しています。COCO/TrashNetの画像データは含めていません。
