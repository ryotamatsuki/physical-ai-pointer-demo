# Experiments

すべてを一本の直列にせず、独立して潰せるリスクは早めに並行確認する。

## Dependency graph

```text
VLM track:
PRE-001 Modal smoke
   ↓
PRE-002 static language/ambiguity eval
   ↓
EXP-007 live EOS RP → Modal

Control track:
EXP-001 Pico
   ↓
EXP-002 Servo + physical calibration
   ↓
EXP-003 PC → USB-UART → Pico ACK

Vision track:
EXP-004 EOS RP endurance
   ↓
EXP-005 ROI / color / uniqueness

Integration:
EXP-003 + EXP-005
   ↓
EXP-006 geometry
   ↓
EXP-007
   ↓
EXP-008 integration
   ↓
EXP-009 repositioning/freshness
   ↓
EXP-010 language generalization
   ↓
EXP-011 public-demo soak
   ↓
EXP-012 cold restart
```

EOS RPのOpenCV接続は大きな実機依存リスクなので、Picoを待たずEXP-004を実施してよい。

## Experiments

| ID | Test | Main pass criterion |
|---|---|---|
| PRE-001 | Modal VLM smoke | strict 4-token contract works |
| PRE-002 | Static language eval | planned demo language is reliable |
| EXP-001 | Pico basic | LED stable |
| EXP-002 | Servo basic/calibration | safe motion + measured directions |
| EXP-003 | PC→Pico | 5 cycles + sequence-matched ACK |
| EXP-004 | EOS RP | 5 min continuous capture |
| EXP-005 | Vision | exactly one valid card per color in ROI |
| EXP-006 | Geometry | pointer ray crosses intended card; unreachable targets rejected |
| EXP-007 | Live camera→Modal | fresh live image + language → target |
| EXP-008 | Integration | correct physical pointing + fault stops |
| EXP-009 | Repositioning | moved scene is re-observed; motion during inference is rejected |
| EXP-010 | Language generalization | predefined evaluation threshold |
| EXP-011 | Public-demo soak | 100 operations; zero unsafe action |
| EXP-012 | Cold restart | reproducible restart from docs |

各結果にcommit SHA、モデルrevision、依存バージョン、実測時間、設定値、PASS/FAILを残す。
