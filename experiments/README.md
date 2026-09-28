# Experiments

前段階がPASSするまで次へ進まない。

| ID | Test | Pass criterion |
|---|---|---|
| PRE-001 | Modal VLM smoke test | 静止画＋自然言語→正しい対象色 |
| EXP-001 | Pico basic | LED blinks reliably |
| EXP-002 | Servo basic | 60/90/120° movement |
| EXP-003 | PC → Pico | PC controls target angle |
| EXP-004 | Camera | EOS RP continuous capture |
| EXP-005 | Vision | RGB card centers detected |
| EXP-006 | Geometry | Pointer reaches card centers |
| EXP-007 | EOS RP → Modal VLM | live image + language → target |
| EXP-008 | Integration | natural-language command causes physical pointing |
| EXP-009 | Repositioning | moving cards changes action correctly |
| EXP-010 | Language generalization | relative/spatial instructions work |

現在の最初の作業は [PRE-001](PRE-001_modal_vlm_smoke_test.md)。

各実験結果には可能な限りcommit SHA、設定値、実測時間、PASS/FAILを残す。
