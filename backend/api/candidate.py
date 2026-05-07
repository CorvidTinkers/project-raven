"""
Candidate API — resume + JD upload and interview session management.

Flow:
  1. POST /resume/analyze_with_jd
     → Saves initial state with status="initializing"
     → Returns candidate_id immediately
     → Fires background task to: parse resume, generate questions
     → Sets status="ready" when done, status="error" on failure

  2. GET /status/{candidate_id}
     → Frontend polls this until status="ready"
     → Returns matched skills and readiness flag

  3. DELETE /candidate/{candidate_id}
     → Cleanup on session end or page refresh
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from agents.state import InterviewState, store
from tasks.q_generator import QuestionGenerator
from tasks.resume_parser import ResumeSkillMatcher

logger = logging.getLogger(__name__)
router = APIRouter(tags=["candidate"])


# ── Background task ────────────────────────────────────────────────────────────

async def _generate_interview_content(
    candidate_id: str,
    resume_text: str,
    jd_text: str,
) -> None:
    """
    Runs after /resume/analyze_with_jd returns.
    Generates matched skills + question bank in parallel.
    Sets state.status = "ready" on success, "error" on failure.
    """
    logger.info(f"[Candidate] Starting pre-generation for {candidate_id[:8]}")
    store.update(candidate_id, status="processing", current_stage="PROCESSING")

    try:
        matcher = ResumeSkillMatcher()
        q_gen = QuestionGenerator()

        # ── Step 1: Skill matching ────────────────────────────────────────────
        matched_skills = await matcher.extract_aligned_skills(resume_text, jd_text)
        skill_list = [s["skill"] for s in matched_skills]
        logger.info(f"[Candidate] Matched {len(skill_list)} skills for {candidate_id[:8]}")

        # ── Step 2: Parallel question generation ─────────────────────────────
        tech_task = q_gen.generate_technical_questions(skill_list, n=5)
        dsa_task = q_gen.generate_dsa_question(skill_list)
        sql_task = q_gen.generate_sql_question(skill_list)

        tech_qs, dsa_q, sql_q = await asyncio.gather(
            tech_task, dsa_task, sql_task,
            return_exceptions=True,  # don't let one failure kill the others
        )

        # Handle partial failures gracefully
        if isinstance(tech_qs, Exception):
            logger.error(f"[Candidate] tech_qs failed: {tech_qs}")
            tech_qs = []
        if isinstance(dsa_q, Exception):
            logger.error(f"[Candidate] dsa_q failed: {dsa_q}")
            dsa_q = {}
        if isinstance(sql_q, Exception):
            logger.error(f"[Candidate] sql_q failed: {sql_q}")
            sql_q = {}

        # ── Step 3: Extract candidate name from resume text ───────────────────
        candidate_name = _extract_name(resume_text)

        # ── Step 4: Finalize state ────────────────────────────────────────────
        store.update(
            candidate_id,
            status="ready",
            current_stage="INTRO",
            candidate_name=candidate_name,
            matched_skills=matched_skills,
            technical_questions=tech_qs,
            dsa_question=dsa_q if isinstance(dsa_q, dict) and dsa_q else None,
            sql_question=sql_q if isinstance(sql_q, dict) and sql_q else None,
            questions_ready=True,
            ui_view="avatar",
        )
        logger.info(f"[Candidate] Pre-generation complete for {candidate_id[:8]}")

    except Exception as exc:
        logger.error(f"[Candidate] Pre-generation failed for {candidate_id[:8]}: {exc}", exc_info=True)
        store.update(
            candidate_id,
            status="error",
            current_stage="ERROR",
            error_message=str(exc),
        )


def _extract_name(resume_text: str) -> Optional[str]:
    """
    Heuristic: the candidate name is often the first non-empty line of the resume.
    Falls back to None if it looks like a heading/label.
    """
    for line in resume_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip lines that look like section headers or email/URLs
        if any(kw in line.lower() for kw in ["resume", "curriculum", "cv", "@", "http", "www", "linkedin"]):
            continue
        # Accept lines that look like a name (1-4 words, mostly alpha)
        words = line.split()
        if 1 <= len(words) <= 4 and all(re.match(r"^[A-Za-z'\-\.]+$", w) for w in words):
            return line
    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/resume/analyze_with_jd")
async def analyze_resume_with_jd(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    jd_text: str = Form(...),
):
    """
    Accepts a resume (PDF or raw text) + job description.
    Returns a candidate_id immediately and starts background question generation.
    Poll GET /status/{candidate_id} until status="ready".
    """
    # ── Extract resume text ───────────────────────────────────────────────────
    resume_text: str = ""

    if file is not None:
        try:
            import io
            from PyPDF2 import PdfReader
            contents = await file.read()
            reader = PdfReader(io.BytesIO(contents))
            pages = [page.extract_text() or "" for page in reader.pages]
            resume_text = "\n".join(pages).strip()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {exc}")
    elif text:
        resume_text = text.strip()
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide a PDF file (field: 'file') or raw text (field: 'text').",
        )

    jd_text = jd_text.strip()

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume text is empty after extraction.")
    if not jd_text:
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")

    # ── Initialize state ──────────────────────────────────────────────────────
    candidate_id = str(uuid.uuid4())

    initial_state: InterviewState = {
        "candidate_id": candidate_id,
        "candidate_name": None,
        "status": "initializing",          # set BEFORE store.set()
        "current_stage": "INITIALIZING",
        "ui_view": "avatar",
        "resume_text": resume_text,
        "jd_text": jd_text,
        "matched_skills": [],
        "technical_questions": [],
        "dsa_question": None,
        "sql_question": None,
        "questions_ready": False,
        "current_question_index": 0,
        "transcript": [],
        "past_summaries": [],
        "code_submission": None,
        "code_grade": None,
        "error_message": None,
    }
    store.set(candidate_id, initial_state)

    # ── Trigger background generation ─────────────────────────────────────────
    background_tasks.add_task(
        _generate_interview_content,
        candidate_id,
        resume_text,
        jd_text,
    )

    return {
        "status": "processing",
        "candidate_id": candidate_id,
        "message": "Resume analysis started. Poll /status/{candidate_id} until ready.",
    }


@router.get("/status/{candidate_id}")
async def get_interview_status(candidate_id: str):
    """Poll this endpoint until status='ready' before connecting the WebSocket."""
    state = store.get(candidate_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {
        "candidate_id": candidate_id,
        "status": state.get("status", "unknown"),
        "current_stage": state.get("current_stage", "UNKNOWN"),
        "is_ready": state.get("status") == "ready",
        "candidate_name": state.get("candidate_name"),
        "matched_skills": state.get("matched_skills", []),
        "questions_ready": state.get("questions_ready", False),
        "error_message": state.get("error_message"),
        "code_grade": state.get("code_grade"),
    }


@router.delete("/candidate/{candidate_id}")
async def delete_candidate_session(candidate_id: str):
    """Explicitly clean up the in-memory session (call on session end or logout)."""
    state = store.get(candidate_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found.")
    store.delete(candidate_id)
    return {"status": "deleted", "candidate_id": candidate_id}
