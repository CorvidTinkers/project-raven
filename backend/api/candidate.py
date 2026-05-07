"""
Candidate API endpoints for resume + job description alignment.
Implements the "Warming Up" pattern by pre-generating questions in the background.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional
import logging
import uuid
import asyncio

from agents.state import store, InterviewState
from tasks.resume_parser import ResumeSkillMatcher
from tasks.q_generator import QuestionGenerator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["candidate"])

async def generate_interview_questions_task(candidate_id: str, resume_text: str, jd_text: str):
    """
    Background task to extract skills and pre-generate technical, DSA, and SQL questions.
    """
    try:
        logger.info(f"Starting pre-generation for candidate {candidate_id}")
        
        # Update status to processing
        store.update(candidate_id, status="processing", current_stage="PROCESSING")
        
        matcher = ResumeSkillMatcher()
        q_gen = QuestionGenerator()
        
        # 1. Extract Aligned Skills
        matched_skills = await matcher.extract_aligned_skills(resume_text, jd_text)
        skill_list = [s["skill"] for s in matched_skills]
        
        # 2. Generate Question Bank (Technical, DSA, SQL)
        # We run these in parallel to save time
        tech_task = q_gen.generate_technical_questions(skill_list, n=5)
        dsa_task = q_gen.generate_dsa_question(skill_list)
        sql_task = q_gen.generate_sql_question(skill_list)
        
        tech_qs, dsa_q, sql_q = await asyncio.gather(tech_task, dsa_task, sql_task)
        
        # 3. Update Store with results
        store.update(
            candidate_id,
            status="ready",
            current_stage="INTRO",
            matched_skills=matched_skills,
            technical_questions=tech_qs,
            dsa_question=dsa_q,
            sql_question=sql_q
        )
        logger.info(f"Pre-generation complete for candidate {candidate_id}")
        
    except Exception as e:
        logger.error(f"Error in background pre-generation for {candidate_id}: {str(e)}")
        # Update status to error so frontend can show retry option
        store.update(candidate_id, status="error", error_message=str(e), current_stage="ERROR")

@router.post("/resume/analyze_with_jd")
async def analyze_resume_with_jd(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    jd_text: str = Form(...),
):
    """
    Accepts a resume and JD, returns a candidate_id, and starts background question generation.
    """
    resume_text: str = ""

    # 1. Extract text from PDF or Form
    if file is not None:
        try:
            import io
            from PyPDF2 import PdfReader
            contents = await file.read()
            reader = PdfReader(io.BytesIO(contents))
            pages = [page.extract_text() or "" for page in reader.pages]
            resume_text = "\n".join(pages).strip()
        except Exception as e:
            logger.error("Resume PDF extraction error: %s", e)
            raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")
    elif text:
        resume_text = text.strip()
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either a PDF file (field: 'file') or raw text (field: 'text').",
        )

    jd_text = jd_text.strip()
    if not jd_text or not resume_text:
        raise HTTPException(status_code=400, detail="Resume or JD text is empty.")

    # 2. Initialize State in Store
    candidate_id = str(uuid.uuid4())
    initial_state: InterviewState = {
        "candidate_id": candidate_id,
        "current_stage": "INITIALIZING",
        "resume_text": resume_text,
        "jd_text": jd_text,
        "matched_skills": [],
        "technical_questions": [],
        "dsa_question": None,
        "sql_question": None,
        "current_question_index": 0,
        "transcript": [],
        "feedback": [],
        "code_submission": None,
        "code_grade": None,
        "ui_view": "avatar"
    }
    store.set(candidate_id, initial_state)

    # 3. Trigger Background Generation
    background_tasks.add_task(generate_interview_questions_task, candidate_id, resume_text, jd_text)

    return {
        "status": "processing",
        "candidate_id": candidate_id,
        "message": "Resume analysis and question generation started."
    }

@router.get("/status/{candidate_id}")
async def get_interview_status(candidate_id: str):
    """
    Poll this to check if the pre-generation is done.
    """
    state = store.get(candidate_id)
    if not state:
        raise HTTPException(status_code=404, detail="Candidate session not found.")
    
    return {
        "candidate_id": candidate_id,
        "current_stage": state.get("current_stage", "UNKNOWN"),
        "status": state.get("status", "unknown"),
        "is_ready": state.get("status") == "ready",
        "error_message": state.get("error_message"),
        "matched_skills": state.get("matched_skills", []),
        "code_grade": state.get("code_grade")
    }
