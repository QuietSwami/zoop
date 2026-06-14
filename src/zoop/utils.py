from datetime import datetime


def to_microsecs(ts: datetime) -> int:
    """Converts a datatime object into a int, representing the datetime as microsends since UNIX epoch."""
    if ts.tzinfo is None:
        raise ValueError("Sample.ts must be timezone-aware (UTC)")
    return int(ts.timestamp() * 1_000_000)


def split_values(r) -> dict:
    """The value for the given type, sets the rest as null.
        This is what allows the existance of several types in the same table.
    """
    return {
        "double": (r.value, None, None, None),   # → value_double
        "int":    (None, r.value, None, None),   # → value_int
        "bool":   (None, None, r.value, None),   # → value_bool
        "str":    (None, None, None, r.value),   # → value_str
    }[r.value_type]
