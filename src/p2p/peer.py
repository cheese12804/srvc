"""Peer-to-peer remote desktop using WebRTC and WebSocket signaling."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay
from aiortc.mediastreams import MediaStreamTrack
import websockets

logging.basicConfig(level=logging.INFO)

RELAY = MediaRelay()


@dataclass
class ControlEvent:
    type: str
    payload: dict

    def to_json(self) -> str:
        return json.dumps({"type": self.type, "payload": self.payload})


class WebSocketSignaling:
    def __init__(self, uri: str) -> None:
        self.uri = uri

    async def exchange(self, description: RTCSessionDescription) -> RTCSessionDescription:
        async with websockets.connect(self.uri) as websocket:
            await websocket.send(json.dumps({
                "sdp": description.sdp,
                "type": description.type,
            }))
            response = json.loads(await websocket.recv())
            return RTCSessionDescription(sdp=response["sdp"], type=response["type"])


class DesktopStream(MediaStreamTrack):
    kind = "video"

    def __init__(self, source: MediaPlayer) -> None:
        super().__init__()
        self.relay = RELAY.subscribe(source.video)

    async def recv(self):  # type: ignore[override]
        frame = await self.relay.recv()
        frame.time_base = None
        return frame


class P2PPeer:
    def __init__(self, signaling_uri: str, screen_source: Optional[str] = None) -> None:
        self.pc = RTCPeerConnection()
        self.signaling = WebSocketSignaling(signaling_uri)
        self.screen_source = screen_source or "screen-capture-recorder"
        self.control_channel = self.pc.createDataChannel("control")
        self.control_channel.on("message", self.on_control_message)

    async def start(self) -> None:
        player = MediaPlayer(self.screen_source, format="gdigrab", options={"framerate": "30", "video_size": "1280x720"})
        stream = DesktopStream(player)
        self.pc.addTrack(stream)

        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        logging.info("Created local offer")

        answer = await self.signaling.exchange(self.pc.localDescription)  # type: ignore[arg-type]
        await self.pc.setRemoteDescription(answer)
        logging.info("Applied remote answer")

    def on_control_message(self, message: str) -> None:
        logging.info("Received control message: %s", message)

    def send_control(self, event: ControlEvent) -> None:
        self.control_channel.send(event.to_json())


async def run_peer(args: argparse.Namespace) -> None:
    peer = P2PPeer(signaling_uri=args.signaling)
    await peer.start()
    await asyncio.Future()


def main() -> None:
    parser = argparse.ArgumentParser(description="P2P remote desktop peer")
    parser.add_argument("--signaling", required=True, help="WebSocket signaling server URI")
    args = parser.parse_args()
    asyncio.run(run_peer(args))


if __name__ == "__main__":
    main()
