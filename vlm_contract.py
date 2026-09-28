SCHEMA_VERSION = "1"
ALLOWED_TARGETS = frozenset({"RED", "BLUE", "GREEN", "NONE"})


def parse_target_exact(text):
    """Return an allowed token only on exact normalized equality."""
    normalized = str(text).strip().upper()
    return normalized if normalized in ALLOWED_TARGETS else None
