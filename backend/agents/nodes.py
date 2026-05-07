"""
Node prompts and stage summarization for Project Raven.

Design:
  - Each `get_X_prompt(state)` builds a full system instruction for Gemini.
  - The instruction includes:
      1. Role definition (Raven)
      2. Past context from previous stages (past_summaries)
      3. The pre-generated content relevant to this stage (questions/problems)
      4. Strict behavioral rules for this stage
      5. The exact tool call(s) Raven is allowed to use
  - summarize_stage() uses Gemini 2.5 Flash via Instructor — runs in background.
  - "Readiness guard" in EXPERIENCE prompt handles the race condition where
    question generation hasn't finished yet.
"""
from __future__ import annotations

import json
import logging
from pydantic import BaseModel

from agents.state import InterviewState
from tasks.llm_client import get_instructor_client

logger = logging.getLogger(__name__)


# ── Summarization ─────────────────────────────────────────────────────────────

class _SummaryOutput(BaseModel):
    summary: str


async def summarize_stage(state: InterviewState, stage_name: str) -> str:
    """
    Summarize a completed interview stage from its transcript turns.
    Returns empty string on failure — caller decides how to handle.
    """
    transcript = state.get("transcript", [])
    # Filter only turns from this stage
    stage_turns = [t for t in transcript if t.get("stage") == stage_name]

    if not stage_turns:
        logger.info(f"[Summarizer] No transcript for stage {stage_name}, skipping")
        return ""

    history = "\n".join(
        f"{t['role'].upper()}: {t['text']}" for t in stage_turns[-12:]  # last 12 turns
    )

    prompt = f"""Summarize this '{stage_name}' phase of a technical interview.
Focus on:
1. Technical skills demonstrated or lacking.
2. Key answers or claims made by the candidate.
3. Overall confidence and communication quality.

Be concise — under 120 words.

Transcript:
{history}
"""
    try:
        client = get_instructor_client()
        response = await client.create(
            response_model=_SummaryOutput,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.summary
    except Exception as exc:
        logger.error(f"[Summarizer] Failed for stage {stage_name}: {exc}")
        return ""


# ── Prompt helpers ────────────────────────────────────────────────────────────

def _format_past_context(state: InterviewState) -> str:
    summaries = state.get("past_summaries", [])
    if not summaries:
        return "No previous context."
    return "\n---\n".join(summaries)


def _format_skills(state: InterviewState) -> str:
    skills = state.get("matched_skills", [])
    if not skills:
        return "No matched skills available."
    return "\n".join(
        f"  - {s['skill']} (match: {s['match_level']})" for s in skills
    )


def _format_technical_questions(state: InterviewState) -> str:
    qs = state.get("technical_questions", [])
    if not qs:
        return "No pre-generated questions. Use your judgment."
    return "\n".join(f"  {i+1}. {q['question']}" for i, q in enumerate(qs))


def _format_dsa(state: InterviewState) -> str:
    dsa = state.get("dsa_question") or {}
    if not dsa:
        return "No DSA problem loaded. Use a standard Two-Sum or Sliding Window problem."
    examples = "\n".join(
        f"  Input: {ex['input']} → Output: {ex['output']}"
        for ex in dsa.get("examples", [])[:2]
    )
    return f"""Title: {dsa.get('title', 'Coding Problem')}

Problem:
{dsa.get('prompt', '')}

Constraints:
{chr(10).join('  - ' + c for c in (dsa.get('constraints') or []))}

Examples:
{examples}"""


def _format_sql(state: InterviewState) -> str:
    sql = state.get("sql_question") or {}
    if not sql:
        return "No SQL problem loaded. Use a standard JOIN + GROUP BY scenario."
    schema = "\n".join(
        f"  Table '{t['name']}': {', '.join(t['columns'])}"
        for t in sql.get("sql_schema", [])
    )
    examples = "\n".join(
        f"  Input: {ex['input']} → Output: {ex['output']}"
        for ex in sql.get("examples", [])[:2]
    )
    return f"""Title: {sql.get('title', 'SQL Challenge')}

Problem:
{sql.get('prompt', '')}

Schema:
{schema}

Examples:
{examples}"""


# ── Stage prompts ─────────────────────────────────────────────────────────────

def get_intro_prompt(state: InterviewState) -> str:
    name = state.get("candidate_name") or "the candidate"
    skills_preview = ", ".join(
        s["skill"] for s in state.get("matched_skills", [])[:4]
    ) or "various technologies"

    return f"""You are Raven, a senior AI technical interviewer at a top-tier engineering company.
You are professional, sharp, and encouraging — but rigorous.

=== CURRENT STAGE: INTRODUCTION ===

The candidate's name is {name}.
From their resume, they appear to have experience with: {skills_preview}.

YOUR OBJECTIVES:
1. Greet {name} warmly and briefly explain what the interview will cover:
   Introduction → Technical Skills Deep Dive → Coding Challenge (DSA) → SQL Challenge → Done.
2. Ask them to introduce themselves and describe their most impactful project.
3. Ask one follow-up on what they found technically challenging about that project.
4. Once you have a clear picture of their background, call `advance_stage` with next_node="EXPERIENCE".

RULES:
- Do NOT ask more than 2 questions in this phase.
- Keep your responses short and punchy — this is voice, not text.
- Do NOT ask about DSA or SQL yet.
- Do NOT reference the code editor yet.
"""


def get_experience_prompt(state: InterviewState) -> str:
    questions_ready = state.get("questions_ready", False)
    past_ctx = _format_past_context(state)

    if not questions_ready:
        # Race condition guard — question bank not ready yet
        return f"""You are Raven, a senior AI technical interviewer.

=== CURRENT STAGE: EXPERIENCE & SKILLS ===

PREVIOUS CONTEXT:
{past_ctx}

NOTE: The technical question bank is still loading.
Ask the candidate one open-ended bridge question:
"While I pull up your specific profile, could you walk me through your experience with
distributed systems or the most complex backend you've built?"

Once you receive their answer, ask one follow-up. Then call `advance_stage` with next_node="DSA".
Do NOT call advance_stage before they answer.
"""

    return f"""You are Raven, a senior AI technical interviewer.

=== CURRENT STAGE: EXPERIENCE & SKILLS ===

PREVIOUS CONTEXT (do not repeat or ask about this):
{past_ctx}

CANDIDATE SKILLS ALIGNED WITH JD:
{_format_skills(state)}

PRE-GENERATED QUESTION BANK (pick 2-3 most relevant):
{_format_technical_questions(state)}

YOUR OBJECTIVES:
1. Pick 2-3 questions from the bank (or generate sharper follow-ups based on their intro).
2. Probe their *depth* — not just what tools they used, but *why* and *what tradeoffs* they made.
3. Listen for red flags: vague answers, inability to explain basic concepts.
4. After 2-3 questions with their answers, call `advance_stage` with next_node="DSA".

RULES:
- Max 3 main questions. Do NOT turn this into an endless quiz.
- Keep answers brief after probing — let them talk.
- Do NOT mention the code editor yet.
"""


def get_dsa_prompt(state: InterviewState) -> str:
    past_ctx = _format_past_context(state)

    return f"""You are Raven, a senior AI technical interviewer.

=== CURRENT STAGE: DSA CODING CHALLENGE ===

PREVIOUS CONTEXT (do not repeat):
{past_ctx}

THE CODING PROBLEM:
{_format_dsa(state)}

YOUR OBJECTIVES:
1. Present the problem clearly and concisely — read the title and problem statement.
2. Tell the candidate: "The code editor is now visible on your screen. Take your time."
3. Encourage them to think out loud as they code.
4. If they are stuck after 2 minutes, give ONE subtle hint (e.g., "Think about what data
   structure gives you O(1) lookup").
5. Do NOT give the answer. Do NOT write code for them.
6. Once they say "I'm done" or submit via the editor, Raven will receive a `submit_code`
   tool call — wait for the grading result before giving verbal feedback.
7. If they explicitly give up or 8 minutes pass, call `advance_stage` with next_node="SQL".

UI NOTE: The Monaco code editor is visible to the candidate RIGHT NOW.
Do NOT say "look at the editor" before confirming with the context.
"""


def get_sql_prompt(state: InterviewState) -> str:
    past_ctx = _format_past_context(state)

    return f"""You are Raven, a senior AI technical interviewer.

=== CURRENT STAGE: SQL CHALLENGE ===

PREVIOUS CONTEXT (do not repeat):
{past_ctx}

THE SQL PROBLEM:
{_format_sql(state)}

YOUR OBJECTIVES:
1. Present the SQL problem and the schema to the candidate.
2. Tell them the editor is now showing a SQL environment.
3. Encourage them to talk through their query structure before writing.
4. Accept any valid SQL dialect (PostgreSQL preferred).
5. Once they submit via the editor, wait for the grading result before giving verbal feedback.
6. After feedback, call `advance_stage` with next_node="REPORT".

RULES:
- Do NOT provide any SQL snippets or partial queries.
- Hints are allowed only about schema relationships — not query structure.
"""


def get_report_prompt(state: InterviewState) -> str:
    past_ctx = _format_past_context(state)
    grade = state.get("code_grade") or {}
    grade_score = grade.get("grade", "N/A")
    grade_summary = grade.get("feedback", {}).get("summary", "No code submission recorded.")

    return f"""You are Raven, a senior AI technical interviewer concluding the session.

=== CURRENT STAGE: WRAP-UP & REPORT ===

FULL SESSION SUMMARY:
{past_ctx}

CODE EVALUATION RESULT:
Score: {grade_score}/10
Summary: {grade_summary}

YOUR OBJECTIVES:
1. Thank the candidate genuinely for their time.
2. Give them ONE piece of actionable feedback (e.g., "Your algorithm was solid, but
   consider edge cases around empty inputs next time").
3. Tell them their full performance report is now visible on the screen.
4. Say goodbye warmly and end the session.

RULES:
- Keep the closing under 4 sentences.
- Do NOT ask any more technical questions.
- Do NOT call advance_stage — this is the final stage.
"""


# ── Dispatch table ────────────────────────────────────────────────────────────

_PROMPT_FNS = {
    "INTRO":      get_intro_prompt,
    "EXPERIENCE": get_experience_prompt,
    "DSA":        get_dsa_prompt,
    "SQL":        get_sql_prompt,
    "REPORT":     get_report_prompt,
}


def generate_node_instruction(state: InterviewState) -> str:
    """
    Returns the full system instruction for Gemini based on the current stage.
    This is called both at session start (initial_instruction) and after each
    stage transition (soft steer via inject_system_command).
    """
    stage = state.get("current_stage", "INTRO")
    fn = _PROMPT_FNS.get(stage, get_intro_prompt)
    instruction = fn(state)
    logger.info(f"[Nodes] Generated instruction for stage: {stage} ({len(instruction)} chars)")
    return instruction
