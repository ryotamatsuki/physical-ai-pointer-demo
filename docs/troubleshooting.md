# Troubleshooting

## Pico is not visible in Thonny

- USBケーブルがデータ通信対応か確認。
- Picoを抜き、BOOTSELを押しながら再接続。
- Windows Device Managerで認識状況を確認。

## PC Python cannot open COM port

典型原因: ThonnyがCOMポートを保持している。

対処:
1. Thonnyを停止。
2. Thonnyを終了。
3. PC側Pythonを再実行。

## SG90 does not move

確認順:
1. 外部5V電源ON
2. SG90 V+/GNDの極性
3. Picoと外部電源のGND共通
4. SignalがGP15
5. 50 Hz PWM
6. 別の安全角度（60/90/120°）

## Pico resets when servo moves

サーボの電源問題を疑う。
- SG90をPico 3.3Vから給電していないか。
- 外部5V電源容量不足がないか。
- GND配線が確実か。

## EOS RP does not appear in OpenCV

- EOS Webcam Utility Proを確認。
- Zoom/Teams/OBS/ブラウザ等を終了。
- `camera_test.py` でindexを0から順に確認。
- USBケーブル交換。
- EOS RPを動画モードへ。

## Color detection is unstable

- 照明を固定。
- 反射を避ける。
- HSV範囲を調整。
- カードを十分大きくする。
- 最小輪郭面積を調整。
- 変更値をEXP-005へ記録。

## Servo points to the opposite side

`ANGLE_SIGN = -1` を試す。

## Servo is consistently offset

`ANGLE_OFFSET` を校正する。

## VLM returns the correct color name but ignores the image

「青を指して」ではテストにならない。

カード位置を入れ替えて:
- 「一番左」
- 「中央」
- 「一番右」

を使い、画像依存性を確認する。

## VLM output contains explanations

プロンプトで `RED / BLUE / GREEN / NONE` の1語だけを要求し、PC側でも正規化・検証する。
