"""
Resume + Job Description Skill Matcher (Instructor + LiteLLM)

Returns resume skills that align with the job requirements and a match level
for each skill.
"""
from __future__ import annotations

import logging
from typing import Literal

from fastapi import UploadFile
from pydantic import BaseModel

from tasks.llm_client import get_instructor_client, resolve_provider

logger = logging.getLogger(__name__)

class MatchedSkill(BaseModel):
	skill: str
	match_level: Literal["low", "medium", "high"]


class MatchedSkillsResponse(BaseModel):
	matches: list[MatchedSkill]


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
- Return the response as structured data matching the schema.

eg user metioned working with FastAPI in resume within projects or experience section and the JD mentioned experience with FastAPI or experience with Python and web frameworks then it should be a high match level. If the JD mentioned experience with Python but not FastAPI specifically, it could be also high match level. If the JD mentioned experience with a different web framework (like Django) but not FastAPI or Python, it could be a medium match level.
"""



class ResumeSkillMatcher:
	def __init__(self, provider: str | None = None) -> None:
		self.provider = provider

	def _client(self, provider: str | None = None):
		return get_instructor_client(provider=provider or self.provider)

	async def extract_aligned_skills(
		self,
		resume_text: str,
		jd_text: str,
		provider: str | None = None,
	) -> list[dict]:
		"""
		Extract resume skills aligned with the job description using instructor.

		Args:
			resume_text: Raw text content of the resume (from PDF or pasted).
			jd_text: Raw text content of the job description.
			provider: Optional LiteLLM provider string (e.g. "groq/llama-3.3-70b-versatile").

		Returns:
			List of objects with skill and match_level keys.
			Falls back to an empty list on error.
		"""
		client = self._client(provider)

		logger.info(
			"[ResumeJDMatcher] Matching skills (resume=%d chars, jd=%d chars)",
			len(resume_text),
			len(jd_text),
		)

		try:
			response = await client.create(
				response_model=MatchedSkillsResponse,
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
			)
			return [item.model_dump() for item in response.matches]
		except Exception as exc:
			logger.error("[ResumeJDMatcher] Failed to match skills: %s", exc)
			return []

	async def extract_aligned_skills_from_resume_pdf(
		self,
		resume_file: UploadFile,
		jd_text: str,
		provider: str | None = None,
	) -> list[dict]:
		"""
		Helper function to extract text from a PDF resume and then find aligned skills.

		Args:
			resume_file: Uploaded PDF file of the candidate's resume.
			jd_text: Raw text content of the job description.
			provider: Optional LiteLLM provider string.
		"""
		resume_text = ""
		try:
			import io
			from PyPDF2 import PdfReader
			contents = await resume_file.read()
			reader = PdfReader(io.BytesIO(contents))
			pages = [page.extract_text() or "" for page in reader.pages]
			resume_text = "\n".join(pages).strip()
		except Exception as exc:
			logger.error("Resume PDF extraction error: %s", exc)
			raise ValueError(f"Failed to read PDF: {str(exc)}")

		return await self.extract_aligned_skills(resume_text, jd_text, provider)


