# SRVC Remote Access Solutions

This repository outlines three architectures for remote access and control solutions. Each architecture balances latency, reliability, and deployment complexity to cover distinct use cases.

## 1. Remote Desktop with SR-VNC

**Goal:** Provide remote desktop control over the network, streaming a server's display while capturing keyboard and mouse input from the client.

**Technologies:**
- **SR-VNC Protocol:** Custom enhancement of VNC using UDP for screen streaming and WebSocket/TCP for control channels.
- **UDP:** Low-latency, lossy transport for screen video frames.
- **WebSocket/TCP:** Reliable channel for keyboard and mouse events.

**Implementation Overview:**
1. **Server:**
   - Capture the screen, encode frames, and stream via UDP using SR-VNC.
   - Host a WebSocket/TCP endpoint to receive input events.
   - Apply received keyboard/mouse events to the OS input queue.
2. **Client:**
   - Receive and decode the UDP video stream, displaying it to the user.
   - Forward local keyboard/mouse actions to the server via WebSocket/TCP.

## 2. Peer-to-Peer Remote Control (P2P)

**Goal:** Allow two machines to connect directly without a relay server for video streaming and input control.

**Technologies:**
- **WebRTC:** Real-time media transport with adaptive bitrate and congestion control.
- **STUN/TURN:** NAT traversal helpers for establishing peer connectivity.
- **WebSocket:** Command channel for input events when not embedded within WebRTC data channels.

**Implementation Overview:**
1. **Connection Setup:**
   - Use STUN/TURN to discover public endpoints and traverse NATs.
   - Exchange WebRTC session descriptions (SDP) via a lightweight signaling service.
2. **Media & Control:**
   - Stream desktop capture or webcam via WebRTC media tracks.
   - Send keyboard/mouse events through WebRTC data channels or a fallback WebSocket connection.

## 3. Web-Based Remote Access

**Goal:** Deliver remote desktop access directly in the browser, avoiding dedicated client software.

**Technologies:**
- **WebRTC:** Browser-compatible streaming of video and audio.
- **WebSocket:** Reliable signaling of input events and optional data exchange.
- **HTML5/CSS/JavaScript:** Frontend interface for viewing and controlling the remote machine.

**Implementation Overview:**
1. **Server:**
   - Capture the desktop and feed it into a WebRTC media pipeline.
   - Manage WebSocket connections to receive control signals and inject them into the host OS.
2. **Web Client:**
   - Render the incoming WebRTC stream in an HTML5 `<video>` element.
   - Capture mouse/keyboard events in JavaScript and send them via WebSocket to the server.

## Summary of Deployment Steps

1. **Remote Desktop (SR-VNC):** Build an SR-VNC server that streams desktop frames over UDP and consumes WebSocket/TCP input events from clients. Implement a client capable of decoding the stream and forwarding local input.
2. **Peer-to-Peer (P2P):** Configure a signaling layer for WebRTC negotiation, leverage STUN/TURN for NAT traversal, stream media via WebRTC, and exchange control commands through data channels or WebSocket.
3. **Web-Based Access:** Provide a web frontend that displays the WebRTC stream and transmits user input via WebSocket, with a server-side component that handles media generation and input injection.

These strategies collectively cover remote desktop usage scenarios ranging from dedicated clients to zero-install browser-based access while balancing latency, reliability, and deployment complexity.

## Reference Implementations

Prototype code is provided to demonstrate the three approaches:

- `src/sr_vnc/server.py` and `src/sr_vnc/client.py` implement the SR-VNC server and client pair. The server streams JPEG-encoded screen captures over UDP while consuming WebSocket control events, and the client registers its UDP endpoint, decodes frames, and forwards shell-input commands back to the server.
- `src/p2p/peer.py` creates a WebRTC peer that publishes a desktop capture track and communicates control messages through a data channel while relying on a WebSocket-based signaling exchange.
- `src/webapp/server.py` hosts a FastAPI application that provides a browser client (`src/webapp/static/index.html`). The server responds to `/offer` requests with WebRTC answers and listens for WebSocket control messages emitted by the frontend.

These samples depend on third-party libraries such as `aiortc`, `websockets`, `fastapi`, `mss`, `opencv-python`, and `uvicorn`. Install the required packages in a virtual environment before running any of the demos.
