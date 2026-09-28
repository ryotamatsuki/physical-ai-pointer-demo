from machine import Pin, PWM
import sys
import time

SERVO_PIN = 15
MIN_ANGLE = 20.0
MAX_ANGLE = 160.0
MIN_US = 1000
MAX_US = 2000

servo = PWM(Pin(SERVO_PIN))
servo.freq(50)

def move_servo(angle):
    angle = max(MIN_ANGLE, min(MAX_ANGLE, float(angle)))
    pulse_us = MIN_US + (MAX_US - MIN_US) * angle / 180.0
    duty = int(pulse_us / 20000.0 * 65535)
    servo.duty_u16(duty)
    time.sleep_ms(250)
    print("OK", angle)

print("READY")

while True:
    try:
        line = sys.stdin.readline().strip()
        if not line:
            continue
        if line == "PING":
            print("PONG")
        elif line == "CENTER":
            move_servo(90)
        elif line.startswith("ANGLE "):
            move_servo(float(line.split()[1]))
        else:
            print("ERROR UNKNOWN COMMAND")
    except Exception as exc:
        print("ERROR", exc)
