import asyncio
import logging
from google import genai
from google.genai import types
import os
from typing import Optional, Callable

from agents.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

class GeminiLive:
    """
    Project Raven: High-fidelity voice engine with state-aware injection.
    Leverages Gemini 2.0 Flash Native Audio via Vertex AI.
    """
    def __init__(self, api_key: str, project_id: str = None, model: str = "gemini-2.0-flash-exp", input_sample_rate: int = 16000):
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

    async def start_session(self, 
                            initial_instruction: str,
                            audio_input_queue: asyncio.Queue, 
                            audio_output_callback: Callable, 
                            interrupt_callback: Optional[Callable] = None, 
                            tool_call_callback: Optional[Callable] = None):
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
                activity_handling="START_OF_ACTIVITY_INTERRUPTS",
            ),
        )

        logger.info(f"Project Raven: Connecting to {self.model}")
        try:
            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                self.session = session
                
                async def send_audio_loop():
                    try:
                        while True:
                            chunk = await audio_input_queue.get()
                            await session.send(
                                input=types.LiveClientMessage(
                                    realtime_input=types.RealtimeInput(
                                        media_chunks=[types.Blob(
                                            data=chunk, 
                                            mime_type=f"audio/pcm;rate={self.input_sample_rate}"
                                        )]
                                    )
                                )
                            )
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
                                    await session.send(
                                        input=types.LiveClientMessage(
                                            tool_response=types.ToolResponse(
                                                function_responses=[
                                                    types.FunctionResponse(
                                                        name=call.name,
                                                        id=call.id,
                                                        response={"status": "success"}
                                                    )
                                                ]
                                            )
                                        )
                                    )

                            # 4. Transcriptions
                            if message.server_content and message.server_content.input_transcription:
                                logger.info(f"User: {message.server_content.input_transcription.text}")
                            if message.server_content and message.server_content.output_transcription:
                                logger.info(f"Gemini: {message.server_content.output_transcription.text}")
                            if message.server_content and message.server_content.turn_complete:
                                logger.info("Turn complete - continuing to listen")
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Error in receive_loop: {e}")

                await asyncio.gather(send_audio_loop(), receive_loop())

        except Exception as e:
            logger.error(f"Gemini Session Error: {e}")
            raise

    async def update_session(self, system_instruction: str):
        """
        HARD STEER: Completely update the system instructions mid-session.
        """
        if self.session:
            logger.info("Sending SessionUpdate (Hard Steer)")
            await self.session.send(
                input=types.LiveClientMessage(
                    session_update=types.SessionUpdate(
                        system_instruction=types.Content(
                            parts=[types.Part(text=system_instruction)]
                        )
                    )
                )
            )

    async def inject_context(self, text_context: str):
        """
        SOFT STEER: Inject context as a hidden user turn.
        """
        if self.session:
            logger.info("Sending ClientContent (Soft Steer)")
            await self.session.send(
                input=types.LiveClientMessage(
                    client_content=types.ClientContent(
                        turns=[
                            types.Content(
                                role="user",
                                parts=[types.Part(text=f"[SYSTEM]: {text_context}")]
                            )
                        ],
                        turn_complete=True
                    )
                )
            )
