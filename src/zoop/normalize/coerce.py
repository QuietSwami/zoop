from datetime import datetime, timezone

from zoop.contracts.mapping import MappingSpec
from zoop.contracts.model import Field, Sample


def _to_dt(value, unit: str) -> datetime:
    if unit == "iso":
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    divisor = {"s": 1, "ms": 1_000, "us": 1_000_000}[unit]
    return datetime.fromtimestamp(value / divisor, tz=timezone.utc)   # tz-aware


def apply_spec(
    data: dict,
    spec: MappingSpec
) -> Sample:
    return Sample(
        device_id=data[spec.device_key],
        ts=_to_dt(data[spec.ts_key], spec.ts_unit),
        tags={tag_key: spec.tags[tag_key] for tag_key in spec.tags},
        fields=[Field(
            metric=field.key,
            value=data[field.key],
            value_type=field.type,
            unit=field.unit,
        ) for field in spec.fields],
        idempotency_key=data[spec.idem_key] if spec.idem_key else None,
    )
