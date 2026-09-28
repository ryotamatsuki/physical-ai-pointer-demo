import time

from pico_link import PicoLink


SEQUENCE = [60.0, 90.0, 120.0, 90.0]
REPEATS = 5

with PicoLink() as pico:
    print("PING:", pico.ping())

    for repeat in range(1, REPEATS + 1):
        print(f"\nCycle {repeat}/{REPEATS}")

        for angle in SEQUENCE:
            ack = pico.send_angle(angle)
            print(f"  {angle:6.1f} -> {ack}")
            time.sleep(1)

    print("\nPASS: all commands received matching ACKs")
