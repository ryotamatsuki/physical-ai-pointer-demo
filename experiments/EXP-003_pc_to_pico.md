# EXP-003 — PC → USB-UART → Pico control

## Objective

Windows Pythonから専用3.3V TTL USB-UART adapterを介してPico UART0へ角度指令を送り、SG90を制御する。

## Preconditions

EXP-002 PASS。

## Wiring

```text
USB-UART TX → Pico GP1 / UART0 RX / physical pin 2
USB-UART RX ← Pico GP0 / UART0 TX / physical pin 1
USB-UART GND ↔ Pico GND / physical pin 3
```

USB-UARTのVCC/5Vは接続しない。
PicoはMicro USBから給電する。

## Pass criterion

PCから送った60/90/120/90°の4指令が5セット連続で正しく実行される。

## Status

BLOCKED by EXP-002

## Record

- USB-UART adapter:
- Logic voltage:
- COM port:
- Baud rate: 115200
- Response messages:
- Result:
