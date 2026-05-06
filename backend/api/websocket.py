import asyncio
import json
import logging
import base64
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.gemini import GeminiLive
from agents.state import store
from agents.graph import interview_graph
from agents.nodes import generate_node_instruction

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, candidate_id: str = Query(...)):
    """
    Project Raven WebSocket: Orchestrates the live voice session with LangGraph.
    """
    logger.info(f"New connection for candidate: {candidate_id}")
    
    # 1. Load Pre-generated State
    state = store.get(candidate_id)
    if not state:
        logger.error(f"Candidate session {candidate_id} not found in store.")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Session not found. Please upload resume again."})
        await websocket.close()
        return
    
    # Check if pre-generation is complete
    status = state.get("status")
    if status != "ready":
        logger.error(f"Candidate session not ready. Status: {status}")
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": f"Interview not ready. Status: {status}. Please wait for analysis to complete."})
        await websocket.close()
        return

    await websocket.accept()
    logger.info(f"WebSocket accepted for {candidate_id}")

    # 2. Setup Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    gemini_client = GeminiLive(api_key=api_key, project_id=project_id)
    
    audio_input_queue = asyncio.Queue()

    # Callback Helpers
    async def audio_output_callback(audio_data):
        await websocket.send_bytes(audio_data)

    async def interrupt_callback():
        await websocket.send_json({"type": "interrupted"})

    async def handle_tool_call(call):
        """
        Handles tools like 'advance_stage' and 'submit_code'.
        """
        nonlocal state
        if call.name == "advance_stage":
            next_node = call.args.get("next_node")
            logger.info(f"Advancing to stage: {next_node}")
            
            # Determine UI view for this stage
            ui_view = "avatar"
            if next_node in ["DSA", "SQL"]:
                ui_view = "monaco"
            elif next_node == "REPORT":
                ui_view = "report"
            
            # STEP 1: Send ui_event FIRST (frontend mounts UI - fast)
            if ui_view != "avatar":
                await websocket.send_json({"type": "ui_event", "view": ui_view})
            
            # STEP 2: Update state
            state["current_stage"] = next_node
            store.update(candidate_id, current_stage=next_node)
            
            # STEP 3: THEN do hard steer (Gemini takes time to generate audio)
            new_instruction = generate_node_instruction(state)
            await gemini_client.update_session(new_instruction)

        elif call.name == "submit_code":
            code = call.args.get("code")
            logger.info(f"Code submitted: {len(code)} chars")
            
            # Get the question from state
            current_stage = state.get("current_stage")
            question = state.get("dsa_question") if current_stage == "DSA" else state.get("sql_question")
            
            if question:
                # Integrate CodeGrader
                from tasks.code_grader import CodeGrader
                grader = CodeGrader()
                grade_result = await grader.grade_solution(question, code)
                state["code_submission"] = code
                state["code_grade"] = grade_result
                store.update(candidate_id, code_submission=code, code_grade=grade_result)
                
                # Inject the grade feedback into the conversation
                feedback = f"Candidate's code has been graded. Score: {grade_result.get('grade', 'N/A')}/10. {grade_result.get('feedback', {}).get('summary', '')}"
                await gemini_client.inject_context(feedback)
            else:
                state["code_submission"] = code
                store.update(candidate_id, code_submission=code)
                await gemini_client.inject_context("Candidate has submitted their code. Acknowledge and proceed.")

    # 3. Main Communication Loops
    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()
                
                if "bytes" in message:
                    await audio_input_queue.put(message["bytes"])
                
                elif "text" in message:
                    data = json.loads(message["text"])
                    
                    if data.get("type") == "audio":
                        audio_data = base64.b64decode(data["data"])
                        await audio_input_queue.put(audio_data)
                    
                    elif data.get("type") == "ui_ready":
                        # Handshake: AI only speaks the prompt once UI is ready
                        logger.info(f"UI Ready Handshake received for node: {data.get('node')}")
                        await gemini_client.inject_context(f"The candidate is now seeing the {data.get('node')} interface. Please proceed with the task.")

        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error in receive_from_client: {e}")

    receive_task = asyncio.create_task(receive_from_client())

    try:
        # Start the Session with INITIAL instructions
        initial_instruction = generate_node_instruction(state)
        await gemini_client.start_session(
            initial_instruction=initial_instruction,
            audio_input_queue=audio_input_queue,
            audio_output_callback=audio_output_callback,
            interrupt_callback=interrupt_callback,
            tool_call_callback=handle_tool_call
        )
    except Exception as e:
        logger.error(f"Error in Gemini session: {e}")
    finally:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        
        # Clean up store
        store.delete(candidate_id)
        
        try:
            await websocket.close()
        except:
            pass
