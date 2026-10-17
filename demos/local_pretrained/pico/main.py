"""Copy this file AND protocol.py to the root of the Pico filesystem."""
from machine import Pin, PWM
import sys
import select
import time
from protocol import parse_command, angle_to_pulse_us

pwm = PWM(Pin(15))  # GP15, physical pin 20.
pwm.freq(50)
pwm.duty_u16(0)     # No pulse at boot; no automatic centering movement.
led = Pin(25, Pin.OUT)  # Original Pico / Pico H, not Pico W.
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
current_us = 1500
target_us = 1500
enabled = False
last_command = time.ticks_ms()
last_step = time.ticks_ms()
buffer = ""


def stop():
    global enabled
    enabled = False
    pwm.duty_u16(0)
    led.off()


print("READY physical-ai-v1")
try:
    while True:
        now = time.ticks_ms()
        if poller.poll(0):
            ch = sys.stdin.read(1)
            if ch in ("\n", "\r"):
                if buffer:
                    try:
                        action, angle = parse_command(buffer)
                        if action == "HELLO":
                            print("READY physical-ai-v1")
                        elif action == "STOP":
                            stop()
                            print("OK STOP")
                        else:
                            target_us = angle_to_pulse_us(angle)
                            enabled = True
                            led.on()
                            print("OK POINT", angle)
                        last_command = now
                    except (ValueError, OverflowError):
                        stop()
                        print("ERR command")
                    buffer = ""
            elif ch:
                buffer += ch
                if len(buffer) > 48:
                    buffer = ""
                    stop()
                    print("ERR length")
        if enabled and time.ticks_diff(now, last_command) > 2000:
            stop()
        if enabled and time.ticks_diff(now, last_step) >= 20:
            delta = target_us - current_us
            current_us += max(-12, min(12, delta))
            pwm.duty_ns(current_us * 1000)
            last_step = now
        time.sleep_ms(1)
finally:
    stop()
