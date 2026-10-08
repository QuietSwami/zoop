import asyncio
import logging
from typing import ClassVar

import aiomqtt
import msgspec

from zoop.contracts.bridge import OptionsSchema
from zoop.contracts.handoff import HandoffRecord, LogProducer
from zoop.utils.clock import now_micros

log = logging.getLogger(__name__)


class MQTTOptions(msgspec.Struct, forbid_unknown_fields=True):
    host: str
    port: int = 1883
    topic: str = "zoop/#"

class MQTTBridge:
    type: ClassVar[str] = "mqtt"
    options_schema: ClassVar[OptionsSchema] = MQTTOptions  # used by `check` to validate options
    def __init__(self, producer: LogProducer, **options) -> None:
        opts = msgspec.convert(options, MQTTOptions)  # validate + type the options
        self._producer = producer
        self._host, self._port, self._topic = opts.host, opts.port, opts.topic

    async def run(self) -> None:
        while True:
            try:
                async with aiomqtt.Client(
                    self._host,
                    self._port,
                    identifier=f"zoop-{self.type}"
                ) as client:
                    await client.subscribe(self._topic, qos=1)
                    log.info(
                        "MQTT bridge connected to %s:%d, subscribed to %r",
                        self._host, self._port, self._topic,
                    )
                    async for message in client.messages:
                        source = message.topic.value.split("/")[1]
                        record = HandoffRecord(
                            source=source,
                            payload=message.payload,
                            received_at=now_micros()
                        )

                        self._producer.append(
                            msgspec.msgpack.encode(record)
                        )

                        self._producer.commit()
            except aiomqtt.MqttError as e:
                log.warning("MQTT connection lost (%s); reconnecting in 5s", e)
                await asyncio.sleep(5)
