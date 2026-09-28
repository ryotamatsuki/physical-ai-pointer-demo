# EXP-005 — RGB card detection

## Objective

固定ROI内で赤・青・緑カードを各1枚だけ安定検出し、背景や衣服をカードと誤認しない。

## Preconditions

EXP-004 PASS。

## Procedure

```powershell
python pc\vision_test.py
```

校正:
- ROI
- HSV
- 面積範囲
- aspect ratio
- extent
- morphology

テスト:
- 10配置
- 台座外に同色物を置く
- 同色カードを2枚置く
- 1色を撤去
- 手/針で一部遮蔽

## Pass criterion

通常10配置:
- 各色 exactly 1 candidate
- 中心がカード内部
- 10/10

異常条件:
- 台座外同色物はROIで除外
- ROI内同色2候補は停止
- 欠落色は停止
- 不十分な遮蔽は停止または明示的に検出失敗
- 最大contourを無条件採用しない

## HSV / ROI settings

### RED
TBD

### BLUE
TBD

### GREEN
TBD

### ROI
TBD

## Result

未実施。
