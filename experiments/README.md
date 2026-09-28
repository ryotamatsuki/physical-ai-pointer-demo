# Experiments

実験は順番に実施し、前段階がPASSするまで次へ進まない。

| ID | Test | Pass criterion |
|---|---|---|
| PRE-001 | Colab VLM smoke test | Image + language → correct target |
| EXP-001 | Pico basic | LED blinks reliably |
| EXP-002 | Servo basic | 60/90/120° movement |
| EXP-003 | PC → Pico | PC controls target angle |
| EXP-004 | Camera | EOS RP continuous capture |
| EXP-005 | Vision | RGB card centers detected |
| EXP-006 | Geometry | Pointer reaches card centers |
| EXP-007 | PC → Colab VLM | Windows image + language → target |
| EXP-008 | Integration | Natural-language command causes physical pointing |
| EXP-009 | Repositioning | Moving cards changes physical action correctly |
| EXP-010 | Language generalization | Relative/spatial instructions work |

各実験は [TEMPLATE.md](TEMPLATE.md) を複製して記録する。

**現在の最初の作業は [PRE-001](PRE-001_colab_vlm_smoke_test.md)。**
