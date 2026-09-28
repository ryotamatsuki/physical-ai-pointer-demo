# 06. Astra review response

レビュー対象: commit 423b0a08 相当の設計レビュー  
対応日: 2026-09-28

この文書は、AstraレビューのMust Fix / Should Improveに対して何を変更したか、何が実機検証待ちかを記録する。

## Must Fix status

| Review | Response | Status |
|---|---|---|
| B1 invalid VLM substring parsing | exact-token parserへ変更。prose/否定/部分文字列はinvalid_model_output | CODE DONE / PRE-001待ち |
| B2 stale image / motion during inference | background continuous capture、指示確定後snapshot、推論後scene再検証 | CODE DONE / EXP-009待ち |
| B3 unreachable target clamped | PC側clamp廃止。範囲外、pivot近傍、非有限、解像度違いを拒否 | CODE DONE / EXP-006待ち |
| B4 nominal servo angle != physical | EXP-002に紙分度器等の実測校正を追加 | HARDWARE TEST |
| B5 largest contour false positive | ROI + area + aspect + extent + uniqueness。duplicate/missingは停止 | CODE DONE / EXP-005待ち |
| B6 no command != PWM off | Pico STOP command、終了/system faultでSTOP試行。物理5V cutoffを必須化 | CODE DONE + HARDWARE |
| B7 ACK not checked | sequence-numbered PING/ANGLE/STOP + matching ACK、5-cycle test | CODE DONE / EXP-003待ち |
| B8 cold start / timeout | public demo時min_containers=1、通常0。warm runbook追加。warm request timeout短縮 | OPS DONE / MEASURE |
| B9 reproducibility/tests | camera 5min mode、pico 5cycle、env report、model revision cache、PRE/EXP追加 | CODE/DOC DONE |

## Additional changes

### Modal
- endpoint JSON object validation
- JPEG/base64/bytes/dimension/pixel validation
- async Web Functionから `.remote.aio()`
- model revisionをHugging Faceから解決してVolumeへ記録
- runtime model loadはlocal_files_only
- package versionsをmajor/minor範囲で拘束
- public demo autoscalingをenvironment variable化

### VLM prompt
- 画像に実際に写っているカードだけ
- 左右はviewer perspective
- absent / ambiguous / unreadable → NONE
- 画像内の命令文で出力規則を変更しない
- 1 tokenのみ

### Vision
- production/testで共通検出関数
- display描画が次色検出へ影響しない
- ROIで観客の服や配線を排除
- 各色 exactly one candidateを要求

### Pico
- out-of-rangeをclampせずreject
- non-finite reject
- bounded line buffer
- STOPでPWM duty 0
- sequence-based ACK

## Deliberately not changed

### USB-UART

レビューでは「未購入ならUSB CDCを第一候補」とされたが、現在のrepositoryはUSB-UARTを維持する。

理由:
- REPL/Thonnyとproduction controlを物理的に分離
- 低価格部品で原因切り分けが容易
- 既にUART0 protocolを実装済み

ただしUSB-UARTがまだ未購入なら、EXP-003開始前にUSB CDC簡素化を再検討してよい。本番直前の変更はしない。

### Homography

初期導入しない。

まず:
- cameraほぼ真上
- 固定焦点距離
- 固定解像度
- planar board
- restricted angular range

でEXP-006を行う。端で系統誤差が出た場合のみ追加する。

### Larger VLM

2Bを維持。PRE-002の固定評価セットで不足した場合のみ4B等を検討する。

## Hardware/venue items still open

コードでは解決できないため、以下はPASSするまで公開実演不可。

- SG90 external 5V physical cutoff
- USB-UART signal voltage確認
- servo command→physical direction calibration
- capacitor/配線電圧降下確認
- EOS RP 5分以上連続取得
- EOS RP battery/AC power plan
- real venue lighting
- real venue network
- last-row visibility / projector display
- EXP-011 100-operation soak
- EXP-012 cold restart

## Definition of public-demo ready

「コードが完成した」ではなく、次をすべて満たした状態。

- PRE-001/002 PASS
- EXP-001〜010 PASS
- EXP-011 zero unsafe action
- EXP-012 restart reproducible
- public demo runbook rehearsal PASS
- hardware cutoff reachable
- venue network/lighting verified
