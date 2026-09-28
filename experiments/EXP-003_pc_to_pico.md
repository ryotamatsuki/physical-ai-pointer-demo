# EXP-003 — PC → USB-UART → Pico control

## Objective

Windows Pythonから専用3.3V TTL USB-UARTを介し、sequence付きcommand/ACKでPicoを安全に制御する。

## Preconditions

EXP-002 PASS。

## Wiring

```text
USB-UART TX → Pico GP1 / UART0 RX / pin 2
USB-UART RX ← Pico GP0 / UART0 TX / pin 1
USB-UART GND ↔ Pico GND / pin 3
```

VCC/5Vは接続しない。

## Protocol

```text
PING <seq>            → PONG <seq>
ANGLE <seq> <angle>   → OK <seq> <angle>
STOP <seq>            → STOPPED <seq>
```

古いACKは成功扱いしない。

## Pass criterion

- 起動時PING/PONG成功。
- 60/90/120/90°を5セット連続でsequence一致ACK。
- 空応答、ERROR、別sequenceを成功扱いしない。
- UART抜線時にtimeoutとして失敗。
- 再接続後はPINGから明示的に復旧。
- 終了時STOPでPWM停止ACK。

## Record

- USB-UART:
- Logic voltage:
- COM:
- Baud: 115200
- 5-cycle result:
- Disconnect test:
- STOP test:
- Result:
