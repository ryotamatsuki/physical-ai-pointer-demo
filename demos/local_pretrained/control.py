"""Decisions only: no neural net, camera or motor dependencies."""
from dataclasses import dataclass
from math import isfinite

SLOTS = ("left", "center", "right")


@dataclass(frozen=True)
class Detection:
    label: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center_x(self):
        return (self.x1 + self.x2) / 2

    @property
    def area(self):
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)


def validate_config(config):
    if len(config["classes"]) != 3 or len(set(config["classes"])) != 3:
        raise ValueError("classes must contain three different names")
    for slot in SLOTS:
        angle = config["angles"][slot]
        if type(angle) is not int or not 30 <= angle <= 150:
            raise ValueError("Servo angles must be integer values in 30..150")
    if not 0 < config["confidence"] <= 1:
        raise ValueError("confidence must be in (0, 1]")
    if not 0 <= config["boundary_margin"] < 1 / 6:
        raise ValueError("boundary_margin must be in [0, 1/6)")
    for name in ("stable_seconds", "missing_seconds", "max_gap_seconds"):
        if not isfinite(config[name]) or config[name] < 0:
            raise ValueError("Invalid temporal setting: " + name)
    if config["min_observations"] < 2:
        raise ValueError("At least two observations are required")
    if set(config["meter_slots"]) != set(config["classes"]):
        raise ValueError("meter_slots must cover all three classes")
    if set(config["meter_slots"].values()) != set(SLOTS):
        raise ValueError("meter_slots must use each slot exactly once")


def choose(detections, config, mode="meter", target="bottle"):
    labels = set(config["classes"]) if mode == "meter" else {target}
    candidates = [d for d in detections if d.label in labels
                  and d.score >= config["confidence"]
                  and d.area >= config["min_area_fraction"]]
    if len(candidates) != 1:
        return None, "NO TARGET" if not candidates else "MULTIPLE TARGETS - HOLD"
    det = candidates[0]
    if mode == "meter":
        return config["meter_slots"][det.label], det.label
    x = det.center_x
    margin = config["boundary_margin"]
    if abs(x - 1 / 3) < margin or abs(x - 2 / 3) < margin:
        return None, "NEAR SLOT BOUNDARY - HOLD"
    return SLOTS[min(2, max(0, int(x * 3)))], det.label


class StableDecision:
    """Require repeated evidence; expire old decisions after missing_seconds."""
    def __init__(self, config):
        self.config = config
        self.reset()

    def reset(self):
        self.active = None
        self.last_seen = None
        self.pending = None
        self.pending_since = 0.0
        self.pending_last = 0.0
        self.count = 0

    def update(self, value, now):
        if value is not None and value not in SLOTS:
            raise ValueError("Unknown slot")
        if value is None:
            self.pending = None
            self.count = 0
        elif value == self.active:
            self.last_seen = now
            self.pending = None
            self.count = 0
        else:
            if value != self.pending or now - self.pending_last > self.config["max_gap_seconds"]:
                self.pending, self.pending_since, self.count = value, now, 1
            else:
                self.count += 1
            self.pending_last = now
            if (self.count >= self.config["min_observations"]
                    and now - self.pending_since >= self.config["stable_seconds"]):
                self.active, self.last_seen = value, now
                self.pending, self.count = None, 0
        if self.last_seen is None or now - self.last_seen >= self.config["missing_seconds"]:
            self.active = None
        return self.active
