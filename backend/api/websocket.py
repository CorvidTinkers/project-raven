import asyncio
import json
import logging
import base64
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.gemini import GeminiLive

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket):
    logger.info("New WebSocket connection attempt on /ws/interview")
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
    # Fetch env vars inside the handler to ensure they are loaded
    api_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    logger.info(f"Client connected. Project: {project_id}")

    audio_input_queue = asyncio.Queue()
    # Initialize Gemini with API Key and Project ID for Vertex AI credits
    gemini_client = GeminiLive(api_key=api_key, project_id=project_id)

    async def audio_output_callback(audio_data):
        # Send raw bytes to client (Next.js expects binary for playback)
        await websocket.send_bytes(audio_data)

    async def interrupt_callback():
        # Send interrupt signal to client to clear playback buffer
        await websocket.send_json({"type": "interrupted"})

    async def ui_callback(ui_event):
        # Send UI synchronization events (e.g., stage transitions)
        await websocket.send_json({"type": "ui_event", "data": ui_event})

    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()
                
                # Check for binary data (direct PCM from frontend)
                if "bytes" in message:
                    logger.debug(f"Received binary audio: {len(message['bytes'])} bytes")
                    await audio_input_queue.put(message["bytes"])
                
                # Check for JSON data (audio chunks or control signals)
                elif "text" in message:
                    data = json.loads(message["text"])
                    logger.info(f"Received JSON: {list(data.keys())}")
                    
                    if data.get("type") == "audio":
                        audio_data = base64.b64decode(data["data"])
                        logger.debug(f"Decoded audio type=audio: {len(audio_data)} bytes")
                        await audio_input_queue.put(audio_data)
                    
                    elif "realtimeInput" in data:
                        chunks = data.get("realtimeInput", {}).get("mediaChunks", [])
                        logger.info(f"Received realtimeInput with {len(chunks)} chunks")
                        for i, chunk in enumerate(chunks):
                            audio_data = base64.b64decode(chunk["data"])
                            logger.debug(f"Chunk {i}: {len(audio_data)} bytes, mime: {chunk.get('mimeType')}")
                            await audio_input_queue.put(audio_data)
                    
                    elif data.get("type") == "control":
                        action = data.get("action")
                        logger.info(f"Received control command: {action}")
                    else:
                        logger.warning(f"Unknown message type: {data}")

        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error receiving from client: {e}")

    receive_task = asyncio.create_task(receive_from_client())

    try:
        await gemini_client.start_session(
            audio_input_queue=audio_input_queue,
            audio_output_callback=audio_output_callback,
            interrupt_callback=interrupt_callback,
            ui_callback=ui_callback
        )
    except Exception as e:
        logger.error(f"Error in Gemini session: {e}")
    finally:
        receive_task.cancel()
        try:
            await websocket.close()
        except:
            pass
