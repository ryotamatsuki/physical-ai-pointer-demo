# EXP-004 — EOS RP capture endurance

## Objective

EOS RP/EOS Webcam Utility/OpenCVが本番同様の待機・取得条件で安定することを確認する。

## Procedure

まずindex scan:

```powershell
python pc\camera_test.py
```

EOS index確認後:

```powershell
python pc\camera_test.py --index <N> --duration 300
```

さらに入力待ち中にカードを動かし、最新画像保持が現在配置を追うことを確認する。

## Pass criterion

- 5分連続取得。
- read failure 0を目標。1件でも出た場合は原因確認。
- 解像度が途中で変わらない。
- カード3枚・pivotが常時frame内。
- WB/露出/focusが実演中に不安定変動しない。
- sleep/battery切れなし。
- 入力待ち後のsnapshotが最新配置。

## Record

- Camera index:
- Actual resolution:
- Average FPS:
- Read failures:
- Lens/focal length:
- Exposure:
- WB:
- AF/MF:
- Power:
- Result:
