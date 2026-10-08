"""A simulator bridge: emits random IoT readings into its producer.

Useful for demos, load testing, and exercising the pipeline without real
devices or a broker. Each tick it produces one reading per simulated device,
wraps it in a HandoffRecord, and appends it to the durable log.
"""

import asyncio
import logging
import random
from typing import ClassVar

import msgspec

from zoop.contracts.bridge import OptionsSchema
from zoop.contracts.handoff import HandoffRecord, LogProducer
from zoop.utils.clock import now_micros

log = logging.getLogger(__name__)


class DummyOptions(msgspec.Struct, forbid_unknown_fields=True):
    source: str = "dummy"     # source name → matched to a MappingSpec downstream
    interval: float = 1.0     # seconds between ticks
    devices: int = 1          # number of simulated devices per tick


class DummyBridge:
    type: ClassVar[str] = "dummy"                      # registry key / config `type`
    options_schema: ClassVar[OptionsSchema] = DummyOptions

    def __init__(self, producer: LogProducer, **options) -> None:
        self.opts = msgspec.convert(options, DummyOptions)   # validate its own options
        self._producer = producer

    def _reading(self, device_id: str) -> dict:
        """A random device payload (opaque to ingest; typed later via MappingSpec)."""
        return {
            "device": device_id,
            "ts": now_micros() // 1000,                       # milliseconds since epoch
            "temperature": round(random.uniform(15.0, 30.0), 2),
            "humidity": round(random.uniform(30.0, 90.0), 2),
        }

    async def run(self) -> None:
        log.info(
            "dummy bridge: %d device(s) every %.3fs as source %r",
            self.opts.devices, self.opts.interval, self.opts.source,
        )
        while True:
            for i in range(self.opts.devices):
                record = HandoffRecord(
                    source=self.opts.source,
                    payload=msgspec.json.encode(self._reading(f"dummy-{i}")),
                    received_at=now_micros(),
                )
                self._producer.append(msgspec.msgpack.encode(record))
            self._producer.commit()                           # group-commit the tick
            await asyncio.sleep(self.opts.interval)


def register(registry) -> None:
    """Plugin hook: lets this bridge be loaded via `plugins` / `--plugin`."""
    registry.register(DummyBridge)
