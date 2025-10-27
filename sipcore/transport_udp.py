# sipcore/transport_udp.py
import asyncio
from typing import Callable
from .logger import get_logger

log = get_logger()

class UDPServer:
    def __init__(self, local=("0.0.0.0", 5060), handler: Callable[[bytes, tuple, asyncio.DatagramTransport], None]=None):
        self.local = local
        self.handler = handler
        self.transport: asyncio.DatagramTransport | None = None

    async def start(self):
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(
            lambda: _UDPProtocol(self.handler),
            local_addr=self.local
        )

class _UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, handler):
        self.handler = handler
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        sock = transport.get_extra_info("sockname")
        log.info(f"UDP server listening on {sock}")

    def datagram_received(self, data, addr):
        if self.handler:
            self.handler(data, addr, self.transport)

    def error_received(self, exc):
        log.error(f"UDP server error: {exc}")
