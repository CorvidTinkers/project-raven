"""
Tool call handlers — business logic extracted from the WebSocket router.

The WebSocket router delegates all tool call processing here so the audio
I/O loop remains clean and non-blocking.

Protocol:
  advance_stage  → transition LangGraph → emit ui_event to frontend → wait for
                   ui_ready handshake → inject new stage instruction (soft steer)
  submit_code    → grade code in background → inject grade result as soft steer
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from agents.graph import advance_stage as graph_advance_stage
from agents.nodes import generate_node_instruction
from agents.state import store, STAGE_UI_VIEW

logger = logging.getLogger(__name__)


async def handle_advance_stage(
    call: Any,
    candidate_id: str,
    gemini_client,                  # GeminiLive instance
    send_to_client: Callable,       # async (dict) -> None — sends JSON to frontend WS
    ui_ready_events: dict,          # {candidate_id: asyncio.Event}
) -> None:
    """
    Full 9-step stage transition protocol (per PRD sequence diagram):

    1.  Gemini calls advance_stage tool                   ← already happened
    2.  Validate + advance LangGraph state
    3.  Send tool ACK to Gemini (done by caller)
    4.  Send ui_event JSON to React frontend
    5.  Wait for ui_ready handshake from React (max 10s)
    6.  Generate new stage instruction (includes context)
    7.  Soft steer Gemini with new instruction
    8.  Background: summarize last stage → inject as context when done
        (graph.advance_stage fires this automatically)
    """
    next_node = call.args.get("next_node", "")
    reason = call.args.get("reason", "stage complete")
    logger.info(f"[Handler] advance_stage → {next_node} (reason: {reason})")

    # 2. Advance LangGraph state (summary fires as bg task automatically)
    result = await graph_advance_stage(
        candidate_id=candidate_id,
        gemini_inject_fn=gemini_client.inject_system_command,
    )
    new_stage = result.get("current_stage", next_node)
    ui_view = result.get("ui_view", STAGE_UI_VIEW.get(new_stage, "avatar"))

    # 4. Tell React to switch its UI view
    await send_to_client({"type": "ui_event", "view": ui_view, "stage": new_stage})
    logger.info(f"[Handler] Sent ui_event: view={ui_view}, stage={new_stage}")

    # 5. Wait for ui_ready handshake (prevents Gemini from talking about UI before it mounts)
    event = asyncio.Event()
    ui_ready_events[candidate_id] = event

    try:
        await asyncio.wait_for(event.wait(), timeout=10.0)
        logger.info(f"[Handler] ui_ready received for {new_stage}")
    except asyncio.TimeoutError:
        logger.warning(f"[Handler] ui_ready timeout for {new_stage} — proceeding anyway")
    finally:
        ui_ready_events.pop(candidate_id, None)

    # 6 + 7. Generate new instruction and soft steer Gemini
    state = store.get(candidate_id)
    if state:
        new_instruction = generate_node_instruction(state)
        await gemini_client.inject_system_command(new_instruction)
        logger.info(f"[Handler] Injected new instruction for stage {new_stage}")


async def handle_submit_code(
    call: Any,
    candidate_id: str,
    gemini_client,
    send_to_client: Callable,
) -> None:
    """
    Grade the submitted code in a background task.
    Gemini receives the grade as a soft steer once ready.
    The frontend is notified so it can show a "grading..." state.
    """
    code = call.args.get("code", "")
    if not code.strip():
        logger.warning("[Handler] submit_code called with empty code")
        await gemini_client.inject_system_command(
            "The candidate submitted an empty solution. Ask them to try again."
        )
        return

    state = store.get(candidate_id)
    if not state:
        return

    current_stage = state.get("current_stage", "")
    question = state.get("dsa_question") if current_stage == "DSA" else state.get("sql_question")

    # Persist the submission immediately
    store.update(candidate_id, code_submission=code)
    await send_to_client({"type": "code_received", "stage": current_stage})

    # Fire grading as background task — do NOT block audio
    asyncio.create_task(
        _grade_and_inject(candidate_id, question, code, gemini_client),
        name=f"grade-{candidate_id[:8]}",
    )


async def _grade_and_inject(
    candidate_id: str,
    question: Optional[dict],
    code: str,
    gemini_client,
) -> None:
    """Background: grade code then inject result into Gemini."""
    from tasks.code_grader import CodeGrader

    grader = CodeGrader()
    try:
        grade_result = await grader.grade_solution(question or {}, code)
    except Exception as exc:
        logger.error(f"[Handler] Grading failed: {exc}")
        grade_result = {}

    store.update(candidate_id, code_grade=grade_result)

    score = grade_result.get("grade", "N/A")
    summary = grade_result.get("feedback", {}).get("summary", "")
    strengths = ", ".join(grade_result.get("feedback", {}).get("strengths", []))

    feedback_msg = (
        f"The candidate's code has been graded. "
        f"Score: {score}/10. {summary} "
        f"Strengths: {strengths or 'not noted'}."
    )
    logger.info(f"[Handler] Grading complete: {score}/10 — injecting into Gemini")
    await gemini_client.inject_system_command(feedback_msg)
