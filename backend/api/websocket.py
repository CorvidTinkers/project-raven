import asyncio
import json
import logging
import os
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.gemini import GeminiLive
from agents.state import store
from agents.nodes import generate_node_instruction

router = APIRouter()
logger = logging.getLogger(__name__)

# Registry of active sessions to prevent race conditions and double-mounts
_active_sessions: Dict[str, GeminiLive] = {}
_connecting_sessions: Set[str] = set()

@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, candidate_id: str = Query(...)):
    """
    Project Raven WebSocket: Orchestrates the live voice session with LangGraph.
    """
    logger.info(f"New connection request for candidate: {candidate_id}")
    
    # 1. Load Pre-generated State
    state = store.get(candidate_id)
    if not state:
        logger.error(f"Candidate session {candidate_id} not found in store.")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Session not found. Please upload resume again."})
        await websocket.close(code=4401)
        return
    
    # Check if pre-generation is complete
    status = state.get("status")
    if status != "ready":
        logger.error(f"Candidate session not ready. Status: {status}")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": f"Interview not ready. Status: {status}. Please wait."})
        await websocket.close(code=4402)
        return

    # 2. Deduplication Guard
    if candidate_id in _connecting_sessions:
        logger.warning(f"Setup already in progress for {candidate_id} - rejecting duplicate")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Connection already in progress."})
        await websocket.close(code=4409)
        return

    if candidate_id in _active_sessions:
        logger.info(f"Replacing existing session for {candidate_id}")
        old_session = _active_sessions.pop(candidate_id)
        await old_session.close()

    _connecting_sessions.add(candidate_id)
    
    await websocket.accept()
    logger.info(f"WebSocket accepted for {candidate_id}")

    # 3. Setup Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    gemini_client = GeminiLive(api_key=api_key, project_id=project_id)
    
    audio_input_queue = asyncio.Queue()

    # Callback Helpers
    async def audio_output_callback(audio_data):
        try:
            await websocket.send_bytes(audio_data)
        except Exception:
            pass

    async def interrupt_callback():
        try:
            await websocket.send_json({"type": "interrupted"})
        except Exception:
            pass

    async def handle_tool_call(call):
        nonlocal state
        if call.name == "advance_stage":
            next_node = call.args.get("next_node")
            logger.info(f"Advancing to stage: {next_node}")
            
            from agents.graph import advance_stage
            result = await advance_stage(candidate_id, next_node)
            
            ui_view = result.get("ui_view", "avatar")
            state["current_stage"] = result.get("current_stage")
            
            # Send ui_event
            await websocket.send_json({"type": "ui_event", "view": ui_view})
            
            # Update Gemini Instructions
            new_instruction = generate_node_instruction(state)
            await gemini_client.update_session(new_instruction)

        elif call.name == "submit_code":
            code = call.args.get("code")
            logger.info(f"Code submitted: {len(code)} chars")
            
            current_stage = state.get("current_stage")
            question = state.get("dsa_question") if current_stage == "DSA" else state.get("sql_question")
            
            if question:
                from tasks.code_grader import CodeGrader
                grader = CodeGrader()
                grade_result = await grader.grade_solution(question, code)
                state["code_submission"] = code
                state["code_grade"] = grade_result
                store.update(candidate_id=candidate_id, code_submission=code, code_grade=grade_result)
                
                feedback = f"Candidate's code has been graded. Score: {grade_result.get('grade', 'N/A')}/10. {grade_result.get('feedback', {}).get('summary', '')}"
                await gemini_client.inject_context(feedback)
            else:
                state["code_submission"] = code
                store.update(candidate_id=candidate_id, code_submission=code)
                await gemini_client.inject_context("Candidate has submitted their code.")

    # 4. Main Communication Loops
    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()
                
                if "bytes" in message:
                    # Direct PCM audio
                    await audio_input_queue.put(message["bytes"])
                
                elif "text" in message:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    
                    elif msg_type == "ui_ready":
                        logger.info(f"UI Ready: {data.get('node')}")
                        await gemini_client.inject_context(f"The candidate is now seeing the {data.get('node')} interface.")
                    
                    elif msg_type == "submit_code":
                        # Client-side code submission (if not via tool call)
                        await handle_tool_call(type('obj', (object,), {'name': 'submit_code', 'args': {'code': data.get('code')}}))

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {candidate_id}")
        except Exception as e:
            logger.error(f"Error in receive_loop: {e}")

    receive_task = asyncio.create_task(receive_from_client())

    try:
        # Start Gemini session
        initial_instruction = generate_node_instruction(state)
        
        # Mark as active
        _connecting_sessions.discard(candidate_id)
        _active_sessions[candidate_id] = gemini_client
        
        await websocket.send_json({"type": "connected"})

        await gemini_client.start_session(
            initial_instruction=initial_instruction,
            audio_input_queue=audio_input_queue,
            audio_output_callback=audio_output_callback,
            interrupt_callback=interrupt_callback,
            tool_call_callback=handle_tool_call,
            candidate_id=candidate_id
        )
    except Exception as e:
        logger.error(f"Gemini session error: {e}")
    finally:
        receive_task.cancel()
        _connecting_sessions.discard(candidate_id)
        _active_sessions.pop(candidate_id, None)
        await gemini_client.close()
        try:
            await websocket.close()
        except:
            pass

