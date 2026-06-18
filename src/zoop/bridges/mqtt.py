import asyncio
from typing import ClassVar

import aiomqtt
import msgspec

from zoop.contracts.handoff import HandoffRecord, LogProducer
from zoop.utils.clock import now_micros


class MQTTOptions(msgspec.Struct):
    host: str
    topic: str = "zoop/#"

class MQTTBridge:
    type: ClassVar[str] = "mqtt"
    def __init__(
        self,
        producer: LogProducer,
        *,
        host: str,
        port: int,
        topic: str
    ):
        self._producer, self._host, self._port, self._topic = producer, host, port, topic

        # Check if there's a broker available. If not, break

    async def run(self):
        while True:
            try:
                async with aiomqtt.Client(
                    self._host,
                    self._port,
                    identifier=f"zoop-{self.type}"
                ) as client:
                    await client.subscribe(self._topic, qos=1)
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
            except aiomqtt.MqttError:
                await asyncio.sleep(5)
