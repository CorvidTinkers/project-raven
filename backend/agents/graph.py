from langgraph.graph import StateGraph, START, END
from agents.state import InterviewState, store
import logging

logger = logging.getLogger(__name__)

# Stage transitions - only valid paths for the interview flow
VALID_TRANSITIONS = {
    "INTRO": ["EXPERIENCE"],
    "EXPERIENCE": ["DSA"],
    "DSA": ["SQL"],
    "SQL": ["REPORT"],
    "REPORT": [END]
}

def validate_transition(current_stage: str, next_stage: str) -> str:
    """Validate and return the next stage, enforcing strict flow."""
    valid_next = VALID_TRANSITIONS.get(current_stage, [])
    if next_stage in valid_next:
        return next_stage
    
    logger.warning(f"Invalid transition attempted: {current_stage} -> {next_stage}. Falling back to default.")
    return valid_next[0] if valid_next else current_stage

def create_interview_graph():
    """
    Creates a functional LangGraph for the technical interview.
    In this MVP, the graph primarily enforces the UI and instruction state shifts.
    """
    workflow = StateGraph(InterviewState)

    # Node functions define what happens when we arrive at a stage
    def intro_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: INTRO")
        return {"current_stage": "INTRO", "ui_view": "avatar"}

    def experience_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: EXPERIENCE")
        return {"current_stage": "EXPERIENCE", "ui_view": "avatar"}

    def dsa_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: DSA")
        return {"current_stage": "DSA", "ui_view": "monaco"}

    def sql_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: SQL")
        return {"current_stage": "SQL", "ui_view": "monaco"}

    def report_node(state: InterviewState) -> dict:
        logger.info("LangGraph Node: REPORT")
        return {"current_stage": "REPORT", "ui_view": "report"}

    # Add Nodes
    workflow.add_node("INTRO", intro_node)
    workflow.add_node("EXPERIENCE", experience_node)
    workflow.add_node("DSA", dsa_node)
    workflow.add_node("SQL", sql_node)
    workflow.add_node("REPORT", report_node)

    # Define edges (Strict sequence)
    workflow.add_edge(START, "INTRO")
    workflow.add_edge("INTRO", "EXPERIENCE")
    workflow.add_edge("EXPERIENCE", "DSA")
    workflow.add_edge("DSA", "SQL")
    workflow.add_edge("SQL", "REPORT")
    workflow.add_edge("REPORT", END)

    return workflow.compile()

interview_graph = create_interview_graph()

async def advance_stage(candidate_id: str, next_node: str):
    """
    Helper to advance the interview stage using the LangGraph.
    Includes context summarization to prevent context bloat.
    """
    state = store.get(candidate_id)
    if not state:
        raise ValueError(f"Candidate session {candidate_id} not found.")

    current = state.get("current_stage", "INTRO")
    target = validate_transition(current, next_node)

    # STEP 1: Summarize current stage conversation
    from agents.nodes import summarize_stage
    summary = await summarize_stage(state)
    
    # FIX: Save context_summary to store BEFORE invoking graph
    # (The graph nodes don't propagate it, so we save it separately)
    if summary:
        store.update(candidate_id, context_summary=summary)
        logger.info(f"Saved context_summary for stage {current}: {summary[:50]}...")
    
    # STEP 2: Invoke the graph
    logger.info(f"Invoking LangGraph: {current} -> {target}")
    result = await interview_graph.ainvoke(
        {"current_stage": target, "candidate_id": candidate_id}
    )

    # Sync result back to store
    store.update(candidate_id, **result)
    return result
