"""
Candidate API endpoints for resume + job description alignment
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["candidate"])


@router.post("/resume/analyze_with_jd")
async def analyze_resume_with_jd(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    jd_text: str = Form(...),
):
    """
    Extract interview-relevant resume skills that align with the job description.

    Accepts:
    - ``file`` — a PDF resume upload (optional)
    - ``text`` — raw resume text pasted by the candidate (optional)
    - ``jd_text`` — raw job description text (required)

    Returns ``{"matched_skills": [{"skill": "Python", "match_level": "high"}], "resume_text": "..."}``
    """
    from app.adk_agents.resume_jd_matcher_agent import extract_aligned_skills

    resume_text: str = ""

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
    if not jd_text:
        raise HTTPException(status_code=422, detail="Job description text is empty.")

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume content is empty.")

    matched_skills = await extract_aligned_skills(resume_text, jd_text)
    logger.info("Resume+JD analysis complete. Matched skills: %s", matched_skills)
    return {"matched_skills": matched_skills, "resume_text": resume_text}
