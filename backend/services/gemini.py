import asyncio
import logging
from google import genai
from google.genai import types
import os

logger = logging.getLogger(__name__)

class GeminiLive:
    """
    Project Raven: High-fidelity voice engine with state-aware injection.
    Leverages Gemini 2.5 Flash Native Audio via Vertex AI.
    """
    def __init__(self, api_key: str, project_id: str = None, model: str = "gemini-live-2.5-flash-native-audio", input_sample_rate: int = 16000):
        self.api_key = api_key
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.model = model
        self.input_sample_rate = input_sample_rate
        
        # Initialize Client: Vertex AI (GCP) and AI Studio (API Key) are mutually exclusive
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
                api_key=api_key
            )
        self.session = None

    async def start_session(self, audio_input_queue, audio_output_callback, interrupt_callback=None, ui_callback=None):
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text="You are Raven, an expert AI technical interviewer. Be professional, concise, and helpful. Focus on technical depth and natural conversation.")]
            ),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    silence_duration_ms=2000,  # Max allowed by SDK
                ),
                activity_handling="START_OF_ACTIVITY_INTERRUPTS",
            ),
        )

        logger.info(f"Project Raven: Connecting to {self.model} (Vertex AI: {bool(self.project_id)})")
        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                self.session = session
                
                async def send_audio_loop():
                    try:
                        while True:
                            chunk = await audio_input_queue.get()
                            # SDK uses VAD for turn detection - just send audio chunks
                            await session.send_realtime_input(
                                audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={self.input_sample_rate}")
                            )
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error in send_audio_loop: {e}")

                async def receive_loop():
                    try:
                        while True:
                            async for message in session.receive():
                                # 1. Handle Audio Output (24kHz PCM)
                                if message.server_content and message.server_content.model_turn:
                                    for part in message.server_content.model_turn.parts:
                                        if part.inline_data:
                                            await audio_output_callback(part.inline_data.data)
                                
                                # 2. Handle Server-Side Interruption (Barge-in)
                                if message.server_content and message.server_content.interrupted:
                                    logger.info("User interrupted - stopping playback")
                                    if interrupt_callback:
                                        await interrupt_callback()
                                
                                # 3. Handle Tool Calls (for future state transitions)
                                if message.tool_call and ui_callback:
                                    await self._handle_tool_call(message.tool_call, ui_callback)
                                
                                # 4. Log transcriptions for debugging
                                if message.server_content and message.server_content.input_transcription:
                                    logger.info(f"User: {message.server_content.input_transcription.text}")
                                if message.server_content and message.server_content.output_transcription:
                                    logger.info(f"Gemini: {message.server_content.output_transcription.text}")
                                
                                # 5. Check for turn complete - session stays open
                                if message.server_content and message.server_content.turn_complete:
                                    logger.info("Turn complete - continuing to listen")
                            
                            # Re-enter receive loop to keep session alive (reference pattern)
                            logger.info("Receive iterator ended, re-entering to keep session alive")
                    except asyncio.CancelledError:
                        logger.info("Receive loop cancelled")
                    except Exception as e:
                        logger.error(f"Error in receive_loop: {e}")

                await asyncio.gather(send_audio_loop(), receive_loop())

        except Exception as e:
            logger.error(f"Gemini Session Error: {e}")
            raise

    async def inject_context(self, new_instruction: str):
        """
        Steer the agent mid-session using system overrides.
        """
        if self.session:
            await self.session.send(
                input=f"[SYSTEM OVERRIDE]: {new_instruction}",
                end_of_turn=True
            )

    async def _handle_tool_call(self, tool_call, ui_callback):
        """
        Processes tool calls to trigger UI transitions (e.g., opening the code editor).
        """
        for call in tool_call.function_calls:
            logger.info(f"Tool call received: {call.name}")
            # Logic for stage transitions will go here
            if call.name == "advance_stage":
                await ui_callback({"type": "stage_transition", "next": call.args.get("next_node")})
