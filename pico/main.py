from machine import Pin, PWM, UART
import time

SERVO_PIN = 15

UART_ID = 0
UART_BAUD = 115200
UART_TX_PIN = 0
UART_RX_PIN = 1

# Conservative initial values. Calibrate on the actual servo.
MIN_ANGLE = 30.0
MAX_ANGLE = 150.0
MIN_US = 1000
MAX_US = 2000

servo = PWM(Pin(SERVO_PIN))
servo.freq(50)

uart = UART(
    UART_ID,
    baudrate=UART_BAUD,
    tx=Pin(UART_TX_PIN),
    rx=Pin(UART_RX_PIN),
)


def reply(message):
    uart.write((message + "\n").encode())


def move_servo(angle):
    angle = max(MIN_ANGLE, min(MAX_ANGLE, float(angle)))

    pulse_us = MIN_US + (MAX_US - MIN_US) * angle / 180.0
    duty = int(pulse_us / 20000.0 * 65535)

    servo.duty_u16(duty)
    time.sleep_ms(250)

    reply("OK {:.1f}".format(angle))


def handle_command(line):
    if line == "PING":
        reply("PONG")

    elif line == "CENTER":
        move_servo(90)

    elif line.startswith("ANGLE "):
        parts = line.split()

        if len(parts) != 2:
            reply("ERROR BAD ANGLE COMMAND")
            return

        try:
            move_servo(float(parts[1]))
        except ValueError:
            reply("ERROR INVALID ANGLE")

    else:
        reply("ERROR UNKNOWN COMMAND")


reply("READY")

buffer = b""

while True:
    try:
        if uart.any():
            chunk = uart.read()

            if chunk:
                buffer += chunk

                while b"\n" in buffer:
                    raw_line, buffer = buffer.split(b"\n", 1)

                    try:
                        line = raw_line.decode().strip()
                    except UnicodeError:
                        reply("ERROR INVALID ENCODING")
                        continue

                    if line:
                        handle_command(line)

        time.sleep_ms(5)

    except Exception as exc:
        reply("ERROR {}".format(exc))
        time.sleep_ms(50)
