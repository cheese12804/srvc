"""Web-based remote desktop server leveraging WebRTC and WebSockets."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
import uvicorn

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay

logging.basicConfig(level=logging.INFO)

app = FastAPI()
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
relay = MediaRelay()


@app.get("/")
async def index() -> HTMLResponse:
    html = (static_dir / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.websocket("/ws/control")
async def control_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            logging.info("Control command: %s", data)
    except WebSocketDisconnect:
        logging.info("Control websocket disconnected")


@app.post("/offer")
async def offer(payload: Dict[str, str]) -> Dict[str, str]:
    offer = RTCSessionDescription(sdp=payload["sdp"], type=payload["type"])
    pc = RTCPeerConnection()

    @pc.on("iceconnectionstatechange")
    async def on_state_change() -> None:
        logging.info("ICE state: %s", pc.iceConnectionState)
        if pc.iceConnectionState in ("failed", "closed"):
            await pc.close()

    options = {"framerate": "30", "video_size": "1280x720"}
    player = MediaPlayer("desktop", format="avfoundation", options=options)
    pc.addTrack(relay.subscribe(player.video))

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


def main() -> None:
    uvicorn.run("webapp.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
