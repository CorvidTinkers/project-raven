"""
Code grader for interview questions.

Evaluates a user's code or pseudocode against a question prompt
and returns structured feedback and scores.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel

from services.llm_client import get_instructor_client, resolve_provider

logger = logging.getLogger(__name__)

class GraderScores(BaseModel):
	correctness: int
	complexity: int
	edge_cases: int
	clarity: int


class GraderFeedback(BaseModel):
	summary: str
	strengths: list[str]
	weaknesses: list[str]
	fix_suggestions: list[str]


class GraderResult(BaseModel):
	grade: int
	scores: GraderScores
	feedback: GraderFeedback
	alignment: str


SYSTEM_PROMPT = """You are a strict but fair technical interviewer.
You are grading a candidate's answer (code or pseudocode) to a programming question.

Rules:
- Focus on correctness first, then complexity, edge cases, and clarity.
- If the answer is pseudocode, judge intent and algorithmic correctness.
- Compare against the question's expected behavior and examples.
- Be concise and actionable.
- Use integer scores 0-10 for each category and overall grade.
- Return structured data matching the schema.
"""



class CodeGrader:
	def __init__(self, provider: str | None = None) -> None:
		self.provider = provider

	def _client(self, provider: str | None = None):
		
		return get_instructor_client(provider=provider or self.provider)

	async def grade_solution(
		self,
		question: dict,
		answer: str,
		provider: str | None = None,
	) -> dict:
		"""
		Grade a user's solution against a question prompt.

		Args:
			question: Question payload (title/prompt/examples/sample_cases).
			answer: User's code or pseudocode.
			provider: Optional LiteLLM provider string.

		Returns:
			Structured grading result. Returns {} on error.
		"""
		client = self._client(provider)

		logger.info("[CodeGrader] Grading answer (chars=%d)", len(answer))

		try:
			response = await client.create(
				response_model=GraderResult,
				messages=[
					{"role": "system", "content": SYSTEM_PROMPT},
					{
						"role": "user",
						"content": (
							"Question:\n"
							f"{question}\n\n"
							"Answer:\n"
							f"{answer}"
						),
					},
				],
			)
			return response.model_dump()
		except Exception as exc:
			logger.error("[CodeGrader] Failed to grade answer: %s", exc)
			return {}
