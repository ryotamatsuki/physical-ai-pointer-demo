from machine import Pin, PWM, UART
import math
import time

SERVO_PIN = 15

UART_ID = 0
UART_BAUD = 115200
UART_TX_PIN = 0
UART_RX_PIN = 1

MIN_ANGLE = 30.0
MAX_ANGLE = 150.0
MIN_US = 1000
MAX_US = 2000

MAX_LINE_BYTES = 128
MAX_SEQ_LENGTH = 16

servo = PWM(Pin(SERVO_PIN))
servo.freq(50)
servo.duty_u16(0)

uart = UART(
    UART_ID,
    baudrate=UART_BAUD,
    tx=Pin(UART_TX_PIN),
    rx=Pin(UART_RX_PIN),
)


def reply(message):
    uart.write((message + "\n").encode())


def valid_seq(seq):
    return (
        1 <= len(seq) <= MAX_SEQ_LENGTH
        and all(ch.isdigit() for ch in seq)
    )


def pulse_for_angle(angle):
    return MIN_US + (MAX_US - MIN_US) * angle / 180.0


def move_servo(seq, angle):
    if not math.isfinite(angle):
        reply("ERROR {} NON_FINITE".format(seq))
        return

    # Reject rather than clamp. The PC also rejects out-of-range targets.
    if not (MIN_ANGLE <= angle <= MAX_ANGLE):
        reply("ERROR {} OUT_OF_RANGE".format(seq))
        return

    pulse_us = pulse_for_angle(angle)
    duty = int(pulse_us / 20000.0 * 65535)
    servo.duty_u16(duty)

    time.sleep_ms(250)
    reply("OK {} {:.2f}".format(seq, angle))


def stop_pwm(seq):
    servo.duty_u16(0)
    reply("STOPPED {}".format(seq))


def handle_command(line):
    parts = line.split()

    if not parts:
        return

    command = parts[0]

    if command == "PING":
        if len(parts) != 2 or not valid_seq(parts[1]):
            reply("ERROR 0 BAD_PING")
            return

        reply("PONG {}".format(parts[1]))
        return

    if command == "STOP":
        if len(parts) != 2 or not valid_seq(parts[1]):
            reply("ERROR 0 BAD_STOP")
            return

        stop_pwm(parts[1])
        return

    if command == "CENTER":
        if len(parts) != 2 or not valid_seq(parts[1]):
            reply("ERROR 0 BAD_CENTER")
            return

        move_servo(parts[1], 90.0)
        return

    if command == "ANGLE":
        if len(parts) != 3 or not valid_seq(parts[1]):
            reply("ERROR 0 BAD_ANGLE_COMMAND")
            return

        try:
            angle = float(parts[2])
        except ValueError:
            reply("ERROR {} INVALID_ANGLE".format(parts[1]))
            return

        move_servo(parts[1], angle)
        return

    reply("ERROR 0 UNKNOWN_COMMAND")


reply("READY")

buffer = b""

while True:
    try:
        if uart.any():
            chunk = uart.read()

            if chunk:
                buffer += chunk

                if len(buffer) > MAX_LINE_BYTES and b"\n" not in buffer:
                    buffer = b""
                    reply("ERROR 0 LINE_TOO_LONG")
                    continue

                while b"\n" in buffer:
                    raw_line, buffer = buffer.split(b"\n", 1)

                    if len(raw_line) > MAX_LINE_BYTES:
                        reply("ERROR 0 LINE_TOO_LONG")
                        continue

                    try:
                        line = raw_line.decode("ascii").strip()
                    except UnicodeError:
                        reply("ERROR 0 INVALID_ENCODING")
                        continue

                    if line:
                        handle_command(line)

        time.sleep_ms(5)

    except Exception as exc:
        servo.duty_u16(0)
        reply("ERROR 0 INTERNAL")
        time.sleep_ms(50)
