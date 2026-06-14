# PyArrow Storage Backend

from pathlib import Path

from zoop.reading import Reading
from zoop.utils import split_values
from zoop.contracts.storage import EmptyReadings

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

class ArrowBackend:
    """Arrow Storage Backend. Writes Parquet files into a given filepath."""

    def __init__(self, path: Path):
        self.path = path

    def read(self, *, query) -> list[Reading]:
        pass

    def write(self, readings: list[Reading]) -> None:
        """Writes a list of Reading to a parquet file."""

        if not readings:
            raise EmptyReadings("Provided readings list is empty...")

        cols = {name: [] for name in SCHEMA.names}

        for reading in readings:
            d, i, b, s = split_values(reading)
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
        pq.write_table(table, self.path, compression="zstd")
