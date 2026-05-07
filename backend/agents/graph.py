"""
LangGraph orchestration for Project Raven.

Design decisions:
  - MemorySaver: persists state in RAM per candidate_id (thread_id).
  - Nodes are lightweight: they just return the stage + ui_view delta.
    All heavy work (prompts, summarization) happens outside the graph.
  - advance_stage() is the single public entry point called by the WS handler.
  - Summarization runs as a background asyncio.Task — it does NOT block
    the stage transition. The live Gemini session transitions immediately
    with a bridge prompt; the summary is injected as a soft steer once done.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import InterviewState, STAGE_TRANSITIONS, STAGE_UI_VIEW, store

logger = logging.getLogger(__name__)

# ── MemorySaver (one per process — survives for the demo lifecycle) ──────────
_memory = MemorySaver()


# ── Node functions ───────────────────────────────────────────────────────────
# Nodes are intentionally minimal. They exist so LangGraph can checkpoint the
# transition and enforce the stage sequence. All business logic is external.

def _node(stage: str):
    """Factory that creates a named node function for a given stage."""
    def fn(state: InterviewState) -> dict:
        logger.info(f"[Graph] Entering node: {stage}")
        return {
            "current_stage": stage,
            "ui_view": STAGE_UI_VIEW[stage],
        }
    fn.__name__ = stage  # makes LangGraph logging readable
    return fn


# ── Build the graph ──────────────────────────────────────────────────────────
def _build_graph() -> object:
    wf = StateGraph(InterviewState)

    for stage in ["INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"]:
        wf.add_node(stage, _node(stage))

    wf.add_edge(START, "INTRO")
    wf.add_edge("INTRO",       "EXPERIENCE")
    wf.add_edge("EXPERIENCE",  "DSA")
    wf.add_edge("DSA",         "SQL")
    wf.add_edge("SQL",         "REPORT")
    wf.add_edge("REPORT",      END)

    return wf.compile(checkpointer=_memory)


_graph = _build_graph()


# ── Public API ───────────────────────────────────────────────────────────────

def _thread_config(candidate_id: str) -> dict:
    return {"configurable": {"thread_id": candidate_id}}


async def init_stage(candidate_id: str) -> dict:
    """
    Invoke the graph at the very first stage (INTRO).
    Called once after the background question generation completes.
    Returns the new state delta {current_stage, ui_view}.
    """
    state = store.get(candidate_id)
    if not state:
        raise ValueError(f"[Graph] Candidate {candidate_id[:8]} not found in store")

    result = await _graph.ainvoke(state, config=_thread_config(candidate_id))
    store.update(candidate_id, current_stage=result["current_stage"], ui_view=result["ui_view"])
    logger.info(f"[Graph] init_stage → {result['current_stage']}")
    return result


async def advance_stage(
    candidate_id: str,
    gemini_inject_fn,          # async callable(text: str) — soft steer
) -> dict:
    """
    Advance to the next stage. Returns immediately after updating state.
    Summarization is fired as a background task — it will call gemini_inject_fn
    once complete so Gemini gets the context without blocking audio.

    Returns: {"current_stage": str, "ui_view": str}
    """
    state = store.get(candidate_id)
    if not state:
        raise ValueError(f"[Graph] Candidate {candidate_id[:8]} not in store")

    current = state.get("current_stage", "INTRO")
    next_stage = STAGE_TRANSITIONS.get(current)

    if next_stage is None:
        logger.warning(f"[Graph] No transition from {current} — already at end")
        return {"current_stage": current, "ui_view": STAGE_UI_VIEW.get(current, "avatar")}

    logger.info(f"[Graph] Advancing: {current} → {next_stage}")

    # 1. Invoke LangGraph to checkpoint the transition
    result = await _graph.ainvoke(
        {**state, "current_stage": next_stage},
        config=_thread_config(candidate_id),
    )
    store.update(candidate_id, current_stage=result["current_stage"], ui_view=result["ui_view"])

    # 2. Fire summarization as a background task (non-blocking)
    asyncio.create_task(
        _summarize_and_inject(candidate_id, current, gemini_inject_fn),
        name=f"summarize-{current}-{candidate_id[:8]}",
    )

    return result


async def _summarize_and_inject(
    candidate_id: str,
    completed_stage: str,
    gemini_inject_fn,
) -> None:
    """
    Background task: summarizes the just-completed stage and soft-steers Gemini
    with that context. Fires ~1-3 seconds after the stage transition.
    """
    from agents.nodes import summarize_stage

    state = store.get(candidate_id)
    if not state:
        return

    summary = await summarize_stage(state, completed_stage)
    if not summary:
        logger.warning(f"[Graph] Summarization returned empty for stage {completed_stage}")
        return

    store.append_summary(candidate_id, summary)
    logger.info(f"[Graph] Summary ready for {completed_stage}, injecting into Gemini")

    # Soft steer: inject as hidden context, not a user-visible message
    context_msg = (
        f"[CONTEXT UPDATE — previous stage '{completed_stage}' summary]: {summary}"
    )
    try:
        await gemini_inject_fn(context_msg)
    except Exception as exc:
        logger.error(f"[Graph] Failed to inject summary: {exc}")
