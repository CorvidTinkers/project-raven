from agents.state import InterviewState
import json

def get_test_intro_prompt(state: InterviewState) -> str:
    return f"""DEBUG MODE: INTRO
    Matched Skills: {len(state['matched_skills'])}
    
    INSTRUCTION:
    1. Greet the user: "System ready. I have found {len(state['matched_skills'])} skills."
    2. Tell the user: "Say 'Next' to move to the Experience check."
    3. Call 'advance_stage(next_node="EXPERIENCE")' ONLY when the user says "Next".
    """

def get_test_experience_prompt(state: InterviewState) -> str:
    questions = [q['question'] for q in state['technical_questions']]
    return f"""DEBUG MODE: EXPERIENCE
    Question Bank: {json.dumps(questions)}
    
    INSTRUCTION:
    1. Say: "I will now read all generated questions for this session."
    2. Read every question in the bank: {questions}
    3. Say: "Say 'Next' to move to the DSA coding phase."
    4. Call 'advance_stage(next_node="DSA")' ONLY when the user says "Next".
    """

def get_test_dsa_prompt(state: InterviewState) -> str:
    dsa = state['dsa_question'] or {}
    return f"""DEBUG MODE: DSA
    Problem: {dsa.get('title')}
    Prompt: {dsa.get('prompt')}
    
    INSTRUCTION:
    1. Read the problem title and prompt.
    2. Say: "The Monaco editor is now open. Submit your code, then say 'Next' to move to SQL."
    3. Call 'advance_stage(next_node="SQL")' ONLY when the user says "Next".
    """

def get_test_sql_prompt(state: InterviewState) -> str:
    sql = state['sql_question'] or {}
    return f"""DEBUG MODE: SQL
    Problem: {sql.get('title')}
    Prompt: {sql.get('prompt')}
    
    INSTRUCTION:
    1. Read the SQL prompt.
    2. Say: "Submit your query, then say 'Next' to see the final report."
    3. Call 'advance_stage(next_node="REPORT")' ONLY when the user says "Next".
    """

def get_test_report_prompt(state: InterviewState) -> str:
    return """DEBUG MODE: REPORT
    
    INSTRUCTION:
    1. Say: "Sequence complete. Generating radar chart and analysis now. Goodbye."
    2. End the session.
    """

TEST_NODE_PROMPTS = {
    "INTRO": get_test_intro_prompt,
    "EXPERIENCE": get_test_experience_prompt,
    "DSA": get_test_dsa_prompt,
    "SQL": get_test_sql_prompt,
    "REPORT": get_test_report_prompt
}
