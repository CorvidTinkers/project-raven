import asyncio
import logging
from google import genai
from google.genai import types
import os
from typing import Optional, Callable

from agents.tools import ALL_TOOLS
from agents.state import store

logger = logging.getLogger(__name__)

class GeminiLive:
    """
    Project Raven: High-fidelity voice engine with state-aware injection.
    Leverages Gemini 2.0 Flash Native Audio via Vertex AI.
    """
    def __init__(self, api_key: str, project_id: str = None, model: str = "gemini-live-2.5-flash-native-audio", input_sample_rate: int = 16000):
        self.api_key = api_key
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.model = model
        self.input_sample_rate = input_sample_rate
        
        # Initialize Client
        if self.project_id:
            logger.info(f"Initializing Gemini Client with Vertex AI (Project: {self.project_id})")
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location="us-central1"
            )
        else:
            logger.info("Initializing Gemini Client with AI Studio (API Key)")
            self.client = genai.Client(
                api_key=api_key,
                http_options={'api_version': 'v1alpha'}
            )
        self.session = None
        self._receive_task = None
        self._send_task = None


    async def start_session(self, 
                            initial_instruction: str,
                            audio_input_queue: asyncio.Queue, 
                            audio_output_callback: Callable, 
                            interrupt_callback: Optional[Callable] = None, 
                            tool_call_callback: Optional[Callable] = None,
                            candidate_id: Optional[str] = None):
        """
        Starts the multimodal live session with the provided initial instructions and tools.
        """
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=ALL_TOOLS,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=initial_instruction)]
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    silence_duration_ms=2000, 
                ),
            ),
        )

        logger.info(f"Project Raven: Connecting to {self.model}")
        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                self.session = session
                
                # Kickstart: Send initial message to trigger first response
                await session.send_client_content(
                    turns=[types.Content(role="user", parts=[types.Part(text="Hello")])],
                    turn_complete=True
                )
                
                async def send_audio_loop():
                    try:
                        while True:
                            chunk = await audio_input_queue.get()
                            logger.info(f"Sending audio to Gemini: {len(chunk)} bytes")
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=chunk, 
                                    mime_type=f"audio/pcm;rate={self.input_sample_rate}"
                                )
                            )
                            logger.info("Audio sent successfully")
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error in send_audio_loop: {e}")

                async def receive_loop():
                    try:
                        async for message in session.receive():
                            # 1. Handle Audio Output
                            if message.server_content and message.server_content.model_turn:
                                for part in message.server_content.model_turn.parts:
                                    if part.inline_data:
                                        logger.info(f"Gemini audio response: {len(part.inline_data.data)} bytes")
                                        await audio_output_callback(part.inline_data.data)
                            
                            # 2. Handle Interruption
                            if message.server_content and message.server_content.interrupted:
                                logger.info("Barge-in detected")
                                if interrupt_callback:
                                    await interrupt_callback()
                            
                            # 3. Handle Tool Calls
                            if message.tool_call and tool_call_callback:
                                for call in message.tool_call.function_calls:
                                    logger.info(f"Gemini calling tool: {call.name}")
                                    await tool_call_callback(call)
                                    
                                    # Always respond to the tool call to keep the session state valid
                                    await session.send_tool_response(
                                        function_responses=[
                                            types.FunctionResponse(
                                                name=call.name,
                                                id=call.id,
                                                response={"status": "success"}
                                            )
                                        ]
                                    )

                            # 4. Transcriptions
                            if message.server_content and message.server_content.input_transcription:
                                user_text = message.server_content.input_transcription.text
                                logger.info(f"User: {user_text}")
                                # Append to state transcript
                                if candidate_id:
                                    state = store.get(candidate_id)
                                    if state:
                                        transcript = state.get("transcript", [])
                                        transcript.append({"role": "user", "text": user_text, "stage": state.get("current_stage")})
                                        store.update(candidate_id=candidate_id, transcript=transcript)

                            if message.server_content and message.server_content.output_transcription:
                                ai_text = message.server_content.output_transcription.text
                                # Append to state transcript
                                if candidate_id:
                                    state = store.get(candidate_id)
                                    if state:
                                        transcript = state.get("transcript", [])
                                        transcript.append({"role": "model", "text": ai_text, "stage": state.get("current_stage")})
                                        store.update(candidate_id=candidate_id, transcript=transcript)

                            if message.server_content and message.server_content.turn_complete:
                                logger.info("Turn complete - listening for next input")
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error in receive_loop: {e}")

                self._send_task = asyncio.create_task(send_audio_loop())
                self._receive_loop_task = asyncio.create_task(receive_loop())
                
                await asyncio.gather(self._send_task, self._receive_loop_task)


        except Exception as e:
            logger.error(f"Gemini Session Error: {e}")
            raise

    async def update_session(self, system_instruction: str):
        """
        HARD STEER: Completely update the system instructions mid-session.
        """
        if self.session:
            logger.info("Sending SessionUpdate (Hard Steer)")
            # In v2 SDK, using a dict is often safer for structural messages
            await self.session.send(
                input={
                    "session_update": {
                        "system_instruction": {
                            "parts": [{"text": system_instruction}]
                        }
                    }
                }
            )

    async def inject_context(self, text_context: str):
        """
        SOFT STEER: Inject context as a hidden user turn.
        """
        if self.session:
            logger.info("Sending ClientContent (Soft Steer)")
            await self.session.send_client_content(
                turns=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=f"[SYSTEM]: {text_context}")]
                    )
                ],
                turn_complete=True
            )

    async def close(self):
        """
        Gracefully close the session and cancel loops.
        """
        logger.info("Closing Gemini Session")
        if self._send_task:
            self._send_task.cancel()
        if self._receive_loop_task:
            self._receive_loop_task.cancel()
        
        if self.session:
            try:
                # In v2 SDK, the session is usually an async context manager, 
                # but if we started it manually we might need to close it.
                # Since we use 'async with', it should close automatically when the gather finishes.
                pass
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            self.session = None

