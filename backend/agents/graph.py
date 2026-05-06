from langgraph.graph import StateGraph, START, END
from agents.state import InterviewState

def advance_stage_logic(state: InterviewState):
    """
    State transition logic. Most transitions are driven by tool calls,
    but the graph enforces the valid sequence.
    """
    return state

def create_interview_graph():
    workflow = StateGraph(InterviewState)

    # Nodes
    workflow.add_node("INTRO", advance_stage_logic)
    workflow.add_node("EXPERIENCE", advance_stage_logic)
    workflow.add_node("DSA", advance_stage_logic)
    workflow.add_node("SQL", advance_stage_logic)
    workflow.add_node("REPORT", advance_stage_logic)

    # Transitions (Strict sequence for the demo)
    workflow.add_edge(START, "INTRO")
    workflow.add_edge("INTRO", "EXPERIENCE")
    workflow.add_edge("EXPERIENCE", "DSA")
    workflow.add_edge("DSA", "SQL")
    workflow.add_edge("SQL", "REPORT")
    workflow.add_edge("REPORT", END)

    return workflow.compile()

interview_graph = create_interview_graph()
