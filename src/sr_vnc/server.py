"""SR-VNC server implementation.

This module streams screen captures over UDP while receiving
mouse/keyboard commands via WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import logging
import struct
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2  # type: ignore
import mss  # type: ignore
import numpy as np
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)


@dataclass
class ControlMessage:
    """Represents a control command received from a client."""

    type: str
    payload: dict

    @staticmethod
    def from_json(message: str) -> "ControlMessage":
        data = json.loads(message)
        return ControlMessage(type=data["type"], payload=data.get("payload", {}))


class SRVNCServer:
    """Streams screen frames to a client and processes control events."""

    def __init__(
        self,
        control_host: str = "0.0.0.0",
        control_port: int = 8765,
        video_host: str = "0.0.0.0",
        video_port: int = 9999,
        monitor: int = 0,
        frame_interval: float = 1 / 30,
    ) -> None:
        self.control_host = control_host
        self.control_port = control_port
        self.video_host = video_host
        self.video_port = video_port
        self.monitor = monitor
        self.frame_interval = frame_interval
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._client_addr: Optional[Tuple[str, int]] = None
        self._sct = mss.mss()

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        await websockets.serve(self.handle_control, self.control_host, self.control_port)
        transport, _ = await loop.create_datagram_endpoint(
            lambda: asyncio.DatagramProtocol(), local_addr=(self.video_host, self.video_port)
        )
        self._transport = transport
        logging.info("SR-VNC server ready on udp://%s:%d and ws://%s:%d",
                     self.video_host, self.video_port, self.control_host, self.control_port)
        while True:
            await self.send_frame()
            await asyncio.sleep(self.frame_interval)

    async def handle_control(self, websocket: WebSocketServerProtocol) -> None:
        logging.info("Control client connected: %s", websocket.remote_address)
        async for message in websocket:
            control = ControlMessage.from_json(message)
            if control.type == "register":
                host = control.payload.get("host") or websocket.remote_address[0]
                port = int(control.payload["port"])
                self._client_addr = (host, port)
                logging.info("Registered client UDP endpoint: %s", self._client_addr)
            else:
                await self.apply_control(control)

    async def send_frame(self) -> None:
        if self._client_addr is None or self._transport is None:
            return
        frame = self.capture_frame()
        header = struct.pack("!I", len(frame))
        self._transport.sendto(header + frame, self._client_addr)

    def capture_frame(self) -> bytes:
        monitor = self._sct.monitors[self.monitor]
        sct_img = self._sct.grab(monitor)
        img = np.array(sct_img)
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not success:
            raise RuntimeError("Failed to encode frame")
        return encoded.tobytes()

    async def apply_control(self, control: ControlMessage) -> None:
        # Placeholder for actual system control integration.
        logging.debug("Received control command: %s", control)


async def main() -> None:
    server = SRVNCServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
