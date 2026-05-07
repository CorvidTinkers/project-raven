from agents.state import InterviewState
from tasks.llm_client import get_instructor_client
# Prompts are defined locally below to ensure stability
# Toggle TEST_NODE_PROMPTS if needed for automated testing
import json
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SummaryOutput(BaseModel):
    summary: str


async def summarize_stage(state: InterviewState) -> str:
    """
    Summarizes the conversation from the current stage.
    Implements the 'Summarize & Swap' pattern to prevent context bloat.
    Uses Instructor + Gemini 3 Flash Preview for structured output.
    """
    stage = state.get("current_stage", "UNKNOWN")
    transcript = state.get("transcript", [])
    
    if not transcript:
        return ""

    logger.info(f"Summarizing stage: {stage}")
    
    # Use Instructor with Gemini 2.5 Flash via Vertex AI
    client = get_instructor_client("vertexai/gemini-2.5-flash")
    
    # Prepare transcript snippet
    recent_turns = transcript[-10:]  # Last 10 turns
    history_str = "\n".join([f"{t['role']}: {t['text']}" for t in recent_turns])
    
    prompt = f"""
    Summarize the following technical interview phase: {stage}.
    Focus on:
    1. Key technical skills demonstrated or missing.
    2. Any interesting follow-ups discussed.
    3. The candidate's overall confidence.
    
    Keep the summary under 150 words.
    
    Transcript:
    {history_str}
    """
    
    try:
        response = await client.create(
            response_model=SummaryOutput,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.summary
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return ""

def get_intro_prompt(state: InterviewState) -> str:
    return f"""You are Raven, a professional technical interviewer.
    
    Current Phase: INTRODUCTION
    Candidate Context: {len(state['matched_skills'])} relevant skills found.
    
    Rules:
    1. Greet the candidate warmly.
    2. Briefly explain the interview structure: Experience check, then a DSA problem, then SQL.
    3. Start by asking them to introduce themselves and their most significant project.
    4. When you feel the introduction is complete, call 'advance_stage(next_node="EXPERIENCE")'.
    
    Tone: Encouraging, professional, and observant.
    """

def get_experience_prompt(state: InterviewState) -> str:
    skills = [s['skill'] for s in state['matched_skills']]
    questions = [q['question'] for q in state['technical_questions']]
    prev_context = state.get("context_summary", "The candidate just introduced themselves.")
    
    return f"""You are Raven, a professional technical interviewer.
    
    Current Phase: EXPERIENCE & SKILLS
    Previous Phase Summary: {prev_context}
    
    Candidate Skills: {", ".join(skills)}
    Question Bank: {json.dumps(questions)}
    
    Rules:
    1. Pick 2-3 questions from the bank or ask your own follow-ups based on their resume.
    2. Deep dive into their technical understanding of the tools they claim to know.
    3. Keep it conversational but rigorous.
    4. When you have enough signal, call 'advance_stage(next_node="DSA")'.
    
    Constraint: Do not ask more than 3 main questions in this phase.
    """

def get_dsa_prompt(state: InterviewState) -> str:
    dsa = state['dsa_question'] or {}
    prev_context = state.get("context_summary", "Finished discussing their background.")
    
    return f"""You are Raven, a professional technical interviewer.
    
    Current Phase: DSA CODING
    Previous Context: {prev_context}
    
    Task: {dsa.get('title', 'Coding Challenge')}
    Problem Statement: {dsa.get('prompt', 'Please solve a coding problem.')}
    
    Rules:
    1. Present the problem clearly to the candidate.
    2. Wait for them to think through the logic. Encourage them to speak their thoughts.
    3. If they are stuck, provide subtle hints but do not give the answer.
    4. Once they have typed their solution in the editor, they will call 'submit_code'.
    5. If they refuse to code or give up, call 'advance_stage(next_node="SQL")'.
    
    UI Status: The Monaco Editor is now visible to the candidate.
    """

def get_sql_prompt(state: InterviewState) -> str:
    sql = state['sql_question'] or {}
    prev_context = state.get("context_summary", "Completed the DSA coding session.")
    
    return f"""You are Raven, a professional technical interviewer.
    
    Current Phase: SQL CHALLENGE
    Previous Context: {prev_context}
    
    Task: {sql.get('title', 'SQL Challenge')}
    Problem Statement: {sql.get('prompt', 'Please solve an SQL problem.')}
    
    Rules:
    1. Present the SQL problem and the schema.
    2. Wait for them to provide the query.
    3. Once they have typed their solution, they will call 'submit_code'.
    4. When finished, call 'advance_stage(next_node="REPORT")'.
    """

def get_report_prompt(state: InterviewState) -> str:
    prev_context = state.get("context_summary", "Finished the technical evaluation.")
    
    return f"""You are Raven, a professional technical interviewer.
    
    Current Phase: WRAP-UP & FEEDBACK
    Overall Evaluation: {prev_context}
    
    Rules:
    1. Thank the candidate for their time.
    2. Inform them that the interview session is complete.
    3. Tell them they can see their detailed performance report on the dashboard now.
    4. Say goodbye and end the session.
    """

NODE_PROMPTS = {
    "INTRO": get_intro_prompt,
    "EXPERIENCE": get_experience_prompt,
    "DSA": get_dsa_prompt,
    "SQL": get_sql_prompt,
    "REPORT": get_report_prompt
}

def generate_node_instruction(state: InterviewState) -> str:
    stage = state.get("current_stage", "INTRO")
    
    # TOGGLE THIS FOR TESTING:
    # prompt_gen = TEST_NODE_PROMPTS.get(stage) 
    prompt_gen = NODE_PROMPTS.get(stage, get_intro_prompt)
    
    return prompt_gen(state)
