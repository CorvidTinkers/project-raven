"""
WebSocket router for Project Raven — voice interview endpoint.

Responsibilities:
  - Accept, validate, and deduplicate WS connections
  - Receive binary PCM audio from browser → queue → Gemini
  - Receive JSON control messages from browser → dispatch to handlers
  - Forward binary PCM audio from Gemini → browser
  - Forward JSON state events from handlers → browser

NOT responsible for:
  - LangGraph state transitions (→ api/handlers.py)
  - Prompt generation (→ agents/nodes.py)
  - Code grading (→ tasks/code_grader.py via handlers.py)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from agents.state import store
from agents.nodes import generate_node_instruction
from api.handlers import handle_advance_stage, handle_submit_code
from services.gemini import GeminiLive

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Session registries (deduplication guards) ────────────────────────────────
_active_sessions: Dict[str, GeminiLive] = {}
_connecting_sessions: Set[str] = set()

# ── ui_ready event store (cross-coroutine signalling) ───────────────────────
_ui_ready_events: Dict[str, asyncio.Event] = {}


@router.websocket("/ws/interview")
async def interview_websocket(
    websocket: WebSocket,
    candidate_id: str = Query(...),
):
    """
    Main voice interview WebSocket.

    URL: ws://host/ws/interview?candidate_id=<uuid>

    Binary frames: raw PCM 16-bit 16kHz mono (mic → Gemini)
    Binary frames: raw PCM 16-bit 24kHz mono (Gemini → speaker)

    Text frames (browser → server):
      {type: "ping"}
      {type: "ui_ready", node: "DSA"}
      {type: "submit_code", code: "..."}  ← fallback if tool call not used

    Text frames (server → browser):
      {type: "connected"}
      {type: "ui_event", view: "monaco", stage: "DSA"}
      {type: "code_received", stage: "DSA"}
      {type: "interrupted"}
      {type: "error", message: "..."}
    """
    logger.info(f"[WS] Connection request: candidate={candidate_id[:8]}")

    # ── 1. Load and validate state ────────────────────────────────────────────
    state = store.get(candidate_id)
    if not state:
        await websocket.accept()
        await _send_json(websocket, {"type": "error", "message": "Session not found. Upload resume first."})
        await websocket.close(code=4401)
        return

    if state.get("status") != "ready":
        await websocket.accept()
        await _send_json(websocket, {
            "type": "error",
            "message": f"Session not ready (status={state.get('status')}). Please wait.",
        })
        await websocket.close(code=4402)
        return

    # ── 2. Deduplication guard ────────────────────────────────────────────────
    if candidate_id in _connecting_sessions:
        await websocket.accept()
        await _send_json(websocket, {"type": "error", "message": "Connection already in progress."})
        await websocket.close(code=4409)
        return

    if candidate_id in _active_sessions:
        logger.info(f"[WS] Replacing existing session for {candidate_id[:8]}")
        old = _active_sessions.pop(candidate_id)
        await old.close()

    _connecting_sessions.add(candidate_id)
    await websocket.accept()
    logger.info(f"[WS] Accepted: {candidate_id[:8]}")

    # ── 3. Build Gemini client ────────────────────────────────────────────────
    gemini = GeminiLive(
        api_key=os.getenv("GEMINI_API_KEY"),
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
    )
    audio_input_queue: asyncio.Queue[bytes] = asyncio.Queue()

    # ── 4. Define I/O callbacks ───────────────────────────────────────────────

    async def on_audio_out(pcm: bytes) -> None:
        try:
            await websocket.send_bytes(pcm)
        except Exception:
            pass

    async def on_interrupted() -> None:
        await _send_json(websocket, {"type": "interrupted"})

    async def on_tool_call(call) -> None:
        if call.name == "advance_stage":
            await handle_advance_stage(
                call=call,
                candidate_id=candidate_id,
                gemini_client=gemini,
                send_to_client=lambda payload: _send_json(websocket, payload),
                ui_ready_events=_ui_ready_events,
            )
        elif call.name == "submit_code":
            await handle_submit_code(
                call=call,
                candidate_id=candidate_id,
                gemini_client=gemini,
                send_to_client=lambda payload: _send_json(websocket, payload),
            )
        else:
            logger.warning(f"[WS] Unknown tool call: {call.name}")

    # ── 5. Start receive loop (browser → server) ──────────────────────────────

    async def receive_loop() -> None:
        try:
            while True:
                message = await websocket.receive()

                if message.get("type") == "websocket.disconnect":
                    break

                # Binary: raw PCM mic audio
                if "bytes" in message and message["bytes"]:
                    await audio_input_queue.put(message["bytes"])

                # Text: JSON control
                elif "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue

                    msg_type = data.get("type")

                    if msg_type == "ping":
                        await _send_json(websocket, {"type": "pong"})

                    elif msg_type == "ui_ready":
                        # Signal the handler that the UI component has mounted
                        node = data.get("node", "")
                        logger.info(f"[WS] ui_ready: {node}")
                        event = _ui_ready_events.get(candidate_id)
                        if event:
                            event.set()

                    elif msg_type == "submit_code":
                        # Client-side submission (fallback when tool call isn't used)
                        code = data.get("code", "")
                        # Wrap as a mock call object
                        mock_call = _MockCall("submit_code", {"code": code})
                        await handle_submit_code(
                            call=mock_call,
                            candidate_id=candidate_id,
                            gemini_client=gemini,
                            send_to_client=lambda payload: _send_json(websocket, payload),
                        )

        except WebSocketDisconnect:
            logger.info(f"[WS] Disconnected: {candidate_id[:8]}")
        except Exception as exc:
            logger.error(f"[WS] receive_loop error: {exc}")

    receive_task = asyncio.create_task(receive_loop(), name=f"ws-recv-{candidate_id[:8]}")

    # ── 6. Start Gemini session ───────────────────────────────────────────────
    try:
        initial_instruction = generate_node_instruction(state)

        # Mark as active (promote from connecting)
        _connecting_sessions.discard(candidate_id)
        _active_sessions[candidate_id] = gemini

        await _send_json(websocket, {"type": "connected"})
        logger.info(f"[WS] Starting Gemini session for {candidate_id[:8]}")

        await gemini.start_session(
            initial_instruction=initial_instruction,
            audio_input_queue=audio_input_queue,
            audio_output_callback=on_audio_out,
            interrupt_callback=on_interrupted,
            tool_call_callback=on_tool_call,
            candidate_id=candidate_id,
        )

    except Exception as exc:
        logger.error(f"[WS] Gemini session error: {exc}", exc_info=True)
        await _send_json(websocket, {"type": "error", "message": f"Session failed: {exc}"})

    finally:
        receive_task.cancel()
        _connecting_sessions.discard(candidate_id)
        _active_sessions.pop(candidate_id, None)
        _ui_ready_events.pop(candidate_id, None)
        await gemini.close()
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(f"[WS] Session fully cleaned up: {candidate_id[:8]}")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_json(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        pass


class _MockCall:
    """Wraps a client-side submission to look like a Gemini tool call."""
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args
        self.id = "client-submit"
