# Troubleshooting

## Modal deploy/auth

### `modal token info` fails
- Modal CLI認証をやり直す。
- deploy用トークンとWeb endpoint用proxy tokenを混同しない。

### HTTP 401 / 403
- `MODAL_PROXY_KEY`
- `MODAL_PROXY_SECRET`
- proxy tokenのenvironment権限
を確認する。

キーをログへ表示しない。

### Modal URL error
`pc/config.py` の `MODAL_CLASSIFY_URL` がdeploy後の `classify_api` URLと一致するか確認する。

### First request is slow
scale-to-zero後のcold startの可能性。
展示直前に `pc/vlm_test.py` を1回実行してwarm-upする。

### Modal returns NONE
- 指示が曖昧でないか。
- 3カードが画像に十分大きく写っているか。
- 「一番左」など画像依存テストで確認する。

---

## Pico

### Pico is not visible in Thonny
- USBケーブルがデータ通信対応か確認。
- BOOTSELを押しながら再接続。
- Device Manager確認。

### PC Python cannot open COM port
典型原因: ThonnyがCOMポートを保持。

1. Thonny停止
2. Thonny終了
3. Python再実行

---

## SG90

### SG90 does not move
1. 外部5V ON
2. V+/GND極性
3. Picoと外部電源のGND共通
4. Signal=GP15
5. 50Hz PWM
6. 60/90/120°でテスト

### Pico resets when servo moves
電源系を疑う。
- SG90をPico 3.3Vから給電していないか
- 外部5V容量
- GND接続

---

## EOS RP / OpenCV

### EOS RP does not appear
- EOS Webcam Utility Pro確認
- Zoom/Teams/OBS/ブラウザ等を終了
- `camera_test.py` でindexを順に確認
- USBケーブル確認
- EOS RPを動画モードへ

### Color detection is unstable
- 照明固定
- 光沢・反射を避ける
- HSV範囲を校正
- カードを大きくする
- `MIN_CONTOUR_AREA` を調整

---

## Geometry

### Servo points opposite
`ANGLE_SIGN = -1` を試す。

### Constant offset
`ANGLE_OFFSET` を校正。

### Error grows toward edges
`ANGLE_SCALE` またはカメラ設置・射影の見直し。

---

## VLM validation

「青を指して」だけでは画像を見ている証明にならない。

カードを入れ替えながら:
- 一番左
- 一番右
- 真ん中

を試す。

Modal通信失敗時にサーボが動かないことも必ず確認する。
