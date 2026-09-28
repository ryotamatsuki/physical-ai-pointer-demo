from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone


class RunLogger:
    def __init__(self, directory="logs"):
        os.makedirs(directory, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(directory, f"session_{stamp}.jsonl")

    def write(self, event, **fields):
        record = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "monotonic_s": time.monotonic(),
            "event": event,
            **fields,
        }
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
