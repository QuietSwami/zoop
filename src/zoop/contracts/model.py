from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from zoop.utils.clock import to_microsecs


@dataclass
class Field:
    """Class for describing a single measurement within a message."""
    metric: str                     # name of the measurement, e.g. temperature
    value: float | int | str | bool # the actual measurement
    value_type: str                 # "double" | "int" | "str" | "bool"
    unit: str | None = None         # normalized name, e.g. "Cel" -> celcius

@dataclass
class Sample:
    """Class to represent a messsage from the device, which can contain several fields."""
    device_id: str
    ts: datetime
    # `tags` map the same metadata through all field entries.
    # this allows for better metadata management and faster searching.
    tags: Mapping[str, str] # metadata shared by all "fields" entries.
    fields: list[Field]     # 1..N measurements sent by device.
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class Reading:
    """Class to represent the storage shape.
        Converts 1 Sample with N Fields into N Readings.
    """
    device_id: str
    ts: int             # microseconds since epoch
    observation_id: str # shared across rows of the same Sample
    metric: str
    value: float | int | str | bool
    value_type: str
    unit: str | None
    tags: Mapping[str,str]
    received_at: int   # ingest time - distinct from ts. microseconds since epoch.


def fan_out(
    sample: Sample,
    *, # ensurs that observation_id and received_at are keyword-only.
    observation_id: str,
    received_at: int
) -> list[Reading]:
    """Splits a Sample into a list of Readings"""

    ts = to_microsecs(sample.ts)
    device_id = sample.device_id
    readings = []

    for field in sample.fields:
        reading = Reading(
            device_id = device_id,
            ts = ts,
            observation_id = observation_id,
            metric = field.metric,
            value = field.value,
            value_type = field.value_type,
            unit = field.unit,
            tags = sample.tags,
            received_at = received_at
        )

        readings.append(reading)

    return readings
