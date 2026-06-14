# Module to write Reading's into a Parquet file

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA = pa.schema([
    ("device_id",      pa.string()),
    ("ts",             pa.int32()),
    ("observation_id", pa.string()),
    ("metric",         pa.string()),
    ("value_double",   pa.float64()),
    ("value_int",      pa.int64()),
    ("value_bool",     pa.bool_()),
    ("value_str",      pa.string()),
    ("value_type",     pa.string()),
    ("unit",           pa.string()),
    ("quality",        pa.string()),
    ("tags",           pa.map_(pa.string(), pa.string())),
    ("received_at",    pa.timestamp("us", tz="UTC"))
])

def _split_value(r) -> dict:
    """The value for the given type, sets the rest as null.
        This is what allows the existance of several types in the same table.
    """
    return {
        "double": (r.value, None, None, None),   # → value_double
        "int":    (None, r.value, None, None),   # → value_int
        "bool":   (None, None, r.value, None),   # → value_bool
        "str":    (None, None, None, r.value),   # → value_str
    }[r.value_type]


def write_parquet(readings, path) -> None:
    """Writes a list of Reading to a parquet file."""

    cols = {name: [] for name in SCHEMA.names}
    for reading in readings:
        d, i, b, s = _split_value(reading)
        cols["device_id"].append(reading.device_id)
        cols["ts"].append(reading.ts)
        cols["observation_id"].append(reading.observation_id)
        cols["metric"].append(reading.metric)
        cols["value_double"].append(d)
        cols["value_int"].append(i)
        cols["value_bool"].append(b)
        cols["value_str"].append(s)
        cols["value_type"].append(reading.value_type)
        cols["unit"].append(reading.unit)
        cols["quality"].append(reading.quality)
        cols["tags"].append(list(reading.tags.items()))   # map ← list of (k,v) tuples
        cols["received_at"].append(reading.received_at)

    table = pa.table(cols, schema=SCHEMA)
    pq.write_table(table, path, compression="zstd")
