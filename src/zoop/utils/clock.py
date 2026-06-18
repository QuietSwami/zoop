from datetime import datetime, timezone


def to_microsecs(ts: datetime) -> int:
    """Converts a datatime object into a int, representing the datetime as microsends since UNIX epoch."""
    if ts.tzinfo is None:
        raise ValueError("Sample.ts must be timezone-aware (UTC)")
    return int(ts.timestamp() * 1_000_000)

def now_micros() -> int:
    return to_microsecs(datetime.now(timezone.utc))
