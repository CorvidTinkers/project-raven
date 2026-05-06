"""
Resume + Job Description Skill Matcher Agent

Accepts raw resume text (or text extracted from a PDF) plus a job description
and returns the resume skills that align with the job requirements.

Usage:
    from app.adk_agents.resume_jd_matcher_agent import extract_aligned_skills
    matched = await extract_aligned_skills(resume_text, jd_text)
    # -> [{"skill": "Python", "match_level": "high"}, ...]
"""
import os
import json
import re
import logging
from groq import AsyncGroq

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com",
        )
    return _client


SYSTEM_PROMPT = """You are a technical hiring expert.
Given a candidate's resume and a job description, return ONLY the candidate's
resume skills that clearly align with the job requirements.

Rules:
- Focus on technical/engineering skills only (programming languages, databases, frameworks,
  CS fundamentals, domain knowledge, tools, cloud platforms, etc.).
- Exclude soft skills (communication, leadership, teamwork, time management, etc.).
- Only include skills that are present in the resume AND relevant to the job description.
- Deduplicate and keep the list focused (0-8 items).
- Assign a match_level to each skill: "low", "medium", or "high".
- Return ONLY a JSON array of objects with this exact schema:
  [{"skill": "...", "match_level": "low|medium|high"}]

Example output:
[{"skill": "Python", "match_level": "high"}, {"skill": "SQL", "match_level": "medium"}]
"""


async def extract_aligned_skills(resume_text: str, jd_text: str) -> list[dict]:
    """
    Call the Groq LLM to extract resume skills aligned with the job description.

    Args:
        resume_text: Raw text content of the resume (from PDF or pasted).
        jd_text: Raw text content of the job description.

    Returns:
        List of objects with skill and match_level keys.
        Falls back to an empty list on error.
    """
    client = _get_client()
    logger.info(
        "[ResumeJDMatcher] Matching skills (resume=%d chars, jd=%d chars)",
        len(resume_text),
        len(jd_text),
    )

    try:
        chat = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Candidate Resume:\n\n"
                        f"{resume_text}\n\n"
                        "Job Description:\n\n"
                        f"{jd_text}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=512,
        )
        raw = chat.choices[0].message.content.strip()
        logger.debug("[ResumeJDMatcher] LLM raw response: %s", raw)

        # Try to parse JSON array directly
        matches = json.loads(raw)
        if _is_valid_match_list(matches):
            return _clean_match_list(matches)

        # Fallback: extract array from response if wrapped in prose
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            matches = json.loads(match.group())
            if _is_valid_match_list(matches):
                return _clean_match_list(matches)

    except Exception as exc:
        logger.error("[ResumeJDMatcher] Failed to match skills: %s", exc)

    return []


def _is_valid_match_list(matches: object) -> bool:
    if not isinstance(matches, list):
        return False
    for item in matches:
        if not isinstance(item, dict):
            return False
        skill = item.get("skill")
        level = item.get("match_level")
        if not isinstance(skill, str):
            return False
        if level not in {"low", "medium", "high"}:
            return False
    return True


def _clean_match_list(matches: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for item in matches:
        skill = item.get("skill", "").strip()
        level = item.get("match_level")
        if not skill or level not in {"low", "medium", "high"}:
            continue
        cleaned.append({"skill": skill, "match_level": level})
    return cleaned
