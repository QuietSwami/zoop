# PyArrow Storage Backend

import uuid
from pathlib import Path
from typing import Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from zoop.contracts.model import Reading
from zoop.contracts.storage import EmptyReadings

SCHEMA = pa.schema([
    ("device_id",      pa.string()),
    ("ts",             pa.timestamp("us", tz="UTC") ),
    ("observation_id", pa.string()),
    ("metric",         pa.string()),
    ("value_double",   pa.float64()),
    ("value_int",      pa.int64()),
    ("value_bool",     pa.bool_()),
    ("value_str",      pa.string()),
    ("value_type",     pa.string()),
    ("unit",           pa.string()),
    ("tags",           pa.map_(pa.string(), pa.string())),
    ("received_at",    pa.timestamp("us", tz="UTC"))
])


def split_values(r) -> tuple:
    """The value for the given type, sets the rest as null.
        This is what allows the existance of several types in the same table.
    """
    return {
        "double": (r.value, None, None, None),   # → value_double
        "int":    (None, r.value, None, None),   # → value_int
        "bool":   (None, None, r.value, None),   # → value_bool
        "str":    (None, None, None, r.value),   # → value_str
    }[r.value_type]


class ParquetBackend:
    """Arrow Storage Backend. Writes Parquet files into a given filepath."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True) # Ensures path exists.

    def read(self, *, location: str) ->  pa.Table:
        """Reads a parquet file from a given location"""

        if not location:
            raise ValueError("location string mustn't be empty.")

        return pa.read_table(location)

    def _next_path(self) -> Path:
        return self.path.joinpath(f"{uuid.uuid4()}.parquet")

    def write(self, readings: list[Reading]) -> str:
        """Writes a list of Reading to a parquet file."""

        if not readings:
            raise EmptyReadings("Provided readings list is empty...")

        cols: Mapping[str, list] = {name: [] for name in SCHEMA.names}

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
            cols["tags"].append(list(reading.tags.items()))   # map ← list of (k,v) tuples
            cols["received_at"].append(reading.received_at)

        pq_location = self._next_path()

        table = pa.table(cols, schema=SCHEMA)
        pq.write_table(table, pq_location, compression="zstd")
        return str(pq_location)

    def kind(self) -> str:
        return self.name
