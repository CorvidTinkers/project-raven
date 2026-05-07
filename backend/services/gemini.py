"""
GeminiLive — voice session engine for Project Raven.

Steering strategies (per PRD):
  - HARD STEER (session start): system_instruction in LiveConnectConfig.
    Gemini "bakes in" its persona and rules from the very first turn.

  - SOFT STEER (mid-session): inject_system_command() sends a clientContent
    turn with role="user" and a [SYSTEM INSTRUCTION - DO NOT READ ALOUD] prefix.
    This is the ONLY reliable way to update Gemini's behavior mid-session with
    the v2 google-genai SDK. session.send() with a raw session_update dict is
    not supported and will silently fail.

The session proxies bidirectional audio between the FastAPI WS and Gemini Live.
It also:
  - Captures input + output transcriptions → appended to InterviewStore
  - Detects barge-in (interrupted) → notifies frontend
  - Detects tool calls → dispatched to the handler callback
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Callable, Optional

from google import genai
from google.genai import types

from agents.tools import ALL_TOOLS
from agents.state import store

logger = logging.getLogger(__name__)

# ── Gemini model config ──────────────────────────────────────────────────────
_DEFAULT_MODEL = "gemini-live-2.5-flash-native-audio"
_VOICE_NAME = "Puck"
_SILENCE_MS = 1800  # ms of silence before Gemini treats as end-of-turn


class GeminiLive:
    """
    Manages one Gemini Multimodal Live session per candidate.
    Lifecycle: instantiate → start_session() → (running) → close()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        input_sample_rate: int = 16000,
    ):
        self.model = model
        self.input_sample_rate = input_sample_rate
        self._session = None
        self._send_task: Optional[asyncio.Task] = None
        self._recv_task: Optional[asyncio.Task] = None
        self._closed = False

        # Client selection: Vertex AI preferred (uses GCP credits), fallback AI Studio
        resolved_project = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if resolved_project:
            logger.info(f"[Gemini] Using Vertex AI (project={resolved_project})")
            self.client = genai.Client(
                vertexai=True,
                project=resolved_project,
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
        elif api_key:
            logger.info("[Gemini] Using AI Studio (API key)")
            self.client = genai.Client(
                api_key=api_key,
                http_options={"api_version": "v1alpha"},
            )
        else:
            raise ValueError(
                "[Gemini] No credentials: set GOOGLE_CLOUD_PROJECT or GEMINI_API_KEY"
            )

    # ── Session start ─────────────────────────────────────────────────────────

    async def start_session(
        self,
        initial_instruction: str,         # HARD STEER — baked in at connect time
        audio_input_queue: asyncio.Queue,
        audio_output_callback: Callable,   # async (pcm_bytes: bytes) -> None
        interrupt_callback: Optional[Callable] = None,  # async () -> None
        tool_call_callback: Optional[Callable] = None,  # async (call) -> None
        candidate_id: Optional[str] = None,
    ) -> None:
        """
        Opens the Gemini Live session and runs until closed.
        Blocks until the session ends (use asyncio.create_task to run concurrently).
        """
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=ALL_TOOLS,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_VOICE_NAME
                    )
                )
            ),
            # HARD STEER: locked in at session creation
            system_instruction=types.Content(
                parts=[types.Part(text=initial_instruction)]
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    silence_duration_ms=_SILENCE_MS,
                )
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        logger.info(f"[Gemini] Connecting to model: {self.model}")

        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                self._session = session
                logger.info("[Gemini] Session established")

                # Kickstart: send a silent greeting trigger so Gemini speaks first
                await session.send_client_content(
                    turns=[types.Content(
                        role="user",
                        parts=[types.Part(text="[SESSION_START]")]
                    )],
                    turn_complete=True,
                )

                # ── Audio send loop ───────────────────────────────────────────
                async def _send_loop():
                    try:
                        while not self._closed:
                            chunk = await asyncio.wait_for(
                                audio_input_queue.get(), timeout=5.0
                            )
                            if self._closed:
                                break
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=chunk,
                                    mime_type=f"audio/pcm;rate={self.input_sample_rate}",
                                )
                            )
                    except asyncio.TimeoutError:
                        pass  # No audio — keep waiting
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        if not self._closed:
                            logger.error(f"[Gemini] send_loop error: {exc}")

                # ── Receive loop ──────────────────────────────────────────────
                async def _recv_loop():
                    try:
                        async for message in session.receive():
                            if self._closed:
                                break
                            await self._handle_message(
                                message,
                                audio_output_callback,
                                interrupt_callback,
                                tool_call_callback,
                                session,
                                candidate_id,
                            )
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        if not self._closed:
                            logger.error(f"[Gemini] recv_loop error: {exc}")

                self._send_task = asyncio.create_task(_send_loop(), name="gemini-send")
                self._recv_task = asyncio.create_task(_recv_loop(), name="gemini-recv")
                await asyncio.gather(self._send_task, self._recv_task)

        except Exception as exc:
            logger.error(f"[Gemini] Session error: {exc}")
            raise

    # ── Message handler ───────────────────────────────────────────────────────

    async def _handle_message(
        self,
        message,
        audio_output_callback,
        interrupt_callback,
        tool_call_callback,
        session,
        candidate_id,
    ):
        sc = message.server_content

        # 1. Audio output chunks
        if sc and sc.model_turn:
            for part in sc.model_turn.parts:
                if part.inline_data:
                    await audio_output_callback(part.inline_data.data)

        # 2. Barge-in / interruption
        if sc and sc.interrupted:
            logger.info("[Gemini] Barge-in detected")
            if interrupt_callback:
                await interrupt_callback()

        # 3. Tool calls — dispatch and always ACK
        if message.tool_call:
            for call in message.tool_call.function_calls:
                logger.info(f"[Gemini] Tool call: {call.name}({call.args})")
                if tool_call_callback:
                    await tool_call_callback(call)
                # Always ACK to keep session state valid
                await session.send_tool_response(
                    function_responses=[
                        types.FunctionResponse(
                            name=call.name,
                            id=call.id,
                            response={"status": "ok"},
                        )
                    ]
                )

        # 4. Input transcription (what candidate said)
        if sc and sc.input_transcription and sc.input_transcription.text:
            text = sc.input_transcription.text
            logger.debug(f"[Gemini] Candidate: {text[:80]}")
            if candidate_id:
                state = store.get(candidate_id)
                if state:
                    store.append_transcript(
                        candidate_id, "user", text, state.get("current_stage", "")
                    )

        # 5. Output transcription (what Gemini said)
        if sc and sc.output_transcription and sc.output_transcription.text:
            text = sc.output_transcription.text
            logger.debug(f"[Gemini] Raven: {text[:80]}")
            if candidate_id:
                state = store.get(candidate_id)
                if state:
                    store.append_transcript(
                        candidate_id, "model", text, state.get("current_stage", "")
                    )

        # 6. Turn complete
        if sc and sc.turn_complete:
            logger.debug("[Gemini] Turn complete")

    # ── Steering ──────────────────────────────────────────────────────────────

    async def inject_system_command(self, command: str) -> None:
        """
        SOFT STEER: Inject a hidden system command as a user turn.
        Gemini reads it but is instructed not to read it aloud.
        Use this for all mid-session context updates.
        """
        if not self._session or self._closed:
            logger.warning("[Gemini] inject_system_command called but session is not active")
            return

        payload = f"[SYSTEM INSTRUCTION - DO NOT READ ALOUD]: {command}"
        logger.info(f"[Gemini] Soft steer: {command[:80]}...")

        await self._session.send_client_content(
            turns=[types.Content(
                role="user",
                parts=[types.Part(text=payload)],
            )],
            turn_complete=True,
        )

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Cancel all tasks and close the session gracefully."""
        if self._closed:
            return
        self._closed = True
        logger.info("[Gemini] Closing session")

        tasks = []
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
            tasks.append(self._send_task)
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            tasks.append(self._recv_task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._session = None
        logger.info("[Gemini] Session closed")
