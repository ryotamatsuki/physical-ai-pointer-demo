import time
import serial
from config import SERIAL_PORT, SERIAL_BAUD

angles = [60, 90, 120, 90]

with serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=2) as ser:
    time.sleep(2)
    ser.reset_input_buffer()

    for angle in angles:
        command = f"ANGLE {angle}\n"
        print("SEND:", command.strip())
        ser.write(command.encode("utf-8"))
        response = ser.readline().decode("utf-8", errors="ignore").strip()
        print("RECV:", response)
        time.sleep(1)
