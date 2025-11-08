"""SR-VNC client implementation."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import struct
from dataclasses import dataclass

import cv2  # type: ignore
import numpy as np
import websockets
from websockets.client import WebSocketClientProtocol

logging.basicConfig(level=logging.INFO)


@dataclass
class FramePacket:
    size: int
    payload: bytes

    @staticmethod
    def parse(raw: bytes) -> "FramePacket":
        size = struct.unpack("!I", raw[:4])[0]
        payload = raw[4:4 + size]
        return FramePacket(size=size, payload=payload)


class SRVNCClient:
    """Receives screen frames and sends control events."""

    def __init__(
        self,
        server_host: str,
        control_port: int = 8765,
        listen_port: int = 10000,
    ) -> None:
        self.server_host = server_host
        self.control_port = control_port
        self.listen_port = listen_port
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.bind(("0.0.0.0", self.listen_port))

    async def start(self) -> None:
        asyncio.create_task(self.receive_frames())
        await self.register_udp()

    async def register_udp(self) -> None:
        uri = f"ws://{self.server_host}:{self.control_port}"
        async with websockets.connect(uri) as websocket:
            payload = {"type": "register", "payload": {"host": None, "port": self.listen_port}}
            await websocket.send(json.dumps(payload))
            logging.info("Registered UDP endpoint with SR-VNC server")
            await self.forward_controls(websocket)

    async def forward_controls(self, websocket: WebSocketClientProtocol) -> None:
        while True:
            command = await asyncio.get_running_loop().run_in_executor(None, input, "control> ")
            msg = json.dumps({"type": "command", "payload": {"raw": command}})
            await websocket.send(msg)

    async def receive_frames(self) -> None:
        while True:
            data, _ = await asyncio.get_running_loop().run_in_executor(None, self._udp_socket.recvfrom, 2 ** 16)
            packet = FramePacket.parse(data)
            self.display_frame(packet.payload)

    def display_frame(self, frame: bytes) -> None:
        array = np.frombuffer(frame, dtype=np.uint8)
        decoded = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if decoded is None:
            return
        cv2.imshow("SR-VNC", decoded)
        cv2.waitKey(1)


async def main() -> None:
    client = SRVNCClient(server_host="127.0.0.1")
    await client.start()


if __name__ == "__main__":
    asyncio.run(main())
