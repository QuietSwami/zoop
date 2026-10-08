import asyncio
import logging
from typing import ClassVar

import msgspec
from aiohttp import web

from zoop.contracts.bridge import OptionsSchema
from zoop.contracts.handoff import HandoffRecord, LogProducer
from zoop.utils.clock import now_micros

log = logging.getLogger(__name__)


class HTTPOptions(msgspec.Struct, forbid_unknown_fields=True):
    host: str
    port: int = 8080
    path: str = "/ingest"          # devices POST to /ingest/{source}
    max_body_bytes: int = 1 << 20  # 1 MiB; aiohttp returns 413 if exceeded

class HTTPBridge:
    type: ClassVar[str] = "http"
    options_schema: ClassVar[OptionsSchema] = HTTPOptions  # used by `check` to validate options

    def __init__(self, producer: LogProducer, **options) -> None:
        self.opts = msgspec.convert(options, HTTPOptions)  # validate + type the options
        self._producer = producer

    async def _handle(self, request: web.Request) -> web.Response:
        source = request.match_info["source"]
        body = await request.read()
        if not body:
            return web.Response(status=400, text="empty body")

        record = HandoffRecord(
            source=source,
            payload=body,
            received_at=now_micros()
        )
        try:
            self._producer.append(msgspec.msgpack.encode(record))
            self._producer.commit()
        except OSError:
            log.exception("failed to persist record from %r", source)
            return web.Response(status=503, text="storage unavailable",
                headers={"Retry-After": "5"})

        return web.Response(status=204)

    async def run(self) -> None:
        app = web.Application(client_max_size=self.opts.max_body_bytes)
        app.router.add_post(f"{self.opts.path}/{{source}}", self._handle)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.opts.host, self.opts.port)
        await site.start()
        log.info(
            "HTTP bridge listening on %s:%d (POST %s/{source})",
            self.opts.host, self.opts.port, self.opts.path,
        )

        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
            log.info("HTTP bridge stopped")
