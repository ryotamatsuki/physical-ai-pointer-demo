"""MicroPython + CPython compatible. Protocol is deliberately an allow-list."""
MIN_ANGLE = 30
MAX_ANGLE = 150


def parse_command(line):
    if line in ("HELLO", "STOP"):
        return line, None
    parts = line.split()
    if len(parts) == 2 and parts[0] == "POINT":
        if not parts[1].isdigit():
            raise ValueError("integer required")
        angle = int(parts[1])
        if MIN_ANGLE <= angle <= MAX_ANGLE:
            return "POINT", angle
    raise ValueError("invalid command or angle")


def angle_to_pulse_us(angle):
    if type(angle) is not int or not MIN_ANGLE <= angle <= MAX_ANGLE:
        raise ValueError("angle outside allowed range")
    # Conservative pulse range. Actual shaft angle varies by servo.
    return 1000 + angle * 1000 // 180
