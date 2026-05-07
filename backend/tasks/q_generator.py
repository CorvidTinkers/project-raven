"""
Question generator for technical interview prep.

Creates short technical questions and a single DSA-style prompt
based on a list of resume skills.
"""
from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel

from tasks.llm_client import get_instructor_client, resolve_provider

logger = logging.getLogger(__name__)

class TechnicalQuestion(BaseModel):
	question: str


class TechnicalQuestionsResponse(BaseModel):
	questions: list[TechnicalQuestion]


class DsaExample(BaseModel):
	input: str
	output: str
	explanation: str | None = None


class DsaQuestion(BaseModel):
	title: str
	prompt: str
	constraints: list[str] | None = None
	examples: list[DsaExample]
	sample_cases: list[DsaExample]


class DsaQuestionResponse(BaseModel):
	question: DsaQuestion


class SqlTable(BaseModel):
	name: str
	columns: list[str]


class SqlExample(BaseModel):
	input: str
	output: str


class SqlQuestion(BaseModel):
	title: str
	prompt: str
	sql_schema: list[SqlTable]
	examples: list[SqlExample]
	sample_cases: list[SqlExample]


class SqlQuestionResponse(BaseModel):
	question: SqlQuestion


TECH_SYSTEM_PROMPT = """You are a technical interviewer.
Generate concise technical interview questions based on the candidate's skills.

Rules:
- Focus on technical fundamentals, tooling, and frameworks.
- Keep each question short and direct (1-2 sentences).
- Avoid soft-skill or behavioral questions.
- Avoid duplicates.
- Return structured data matching the schema.
"""


DSA_SYSTEM_PROMPT = """You are a technical interviewer.
Generate one simple-to-medium DSA coding question.

Rules:
- Use a classic LeetCode-style format.
- Provide a clear paragraph prompt, then examples and sample cases.
- Keep it simple and solvable in 30-45 minutes.
- Avoid tricky edge cases unless explicitly asked.
- Return structured data matching the schema.
"""


SQL_SYSTEM_PROMPT = """You are a technical interviewer.
Generate one SQL interview question.

Rules:
- Provide a clear prompt and a minimal schema.
- The answer should be a single SQL query.
- Include at least one example and one sample case.
- Keep it solvable in 20-30 minutes.
- Return structured data matching the schema.
"""



class QuestionGenerator:
	def __init__(self, provider: str | None = None) -> None:
		self.provider = provider

	def _client(self, provider: str | None = None):
		return get_instructor_client(provider=provider or self.provider)

	async def generate_technical_questions(
		self,
		skills: list[str],
		provider: str | None = None,
		n: int = 5,
	) -> list[dict]:
		"""
		Generate short technical interview questions from a skill list.

		Args:
			skills: Parsed resume skills to target.
			provider: Optional LiteLLM provider string.
			n: Number of questions (default 5).

		Returns:
			List of objects with a question key. Returns [] on error.
		"""
		client = self._client(provider)

		logger.info(
			"[QuestionGenerator] Generating %d technical questions (skills=%d)",
			n,
			len(skills),
		)

		try:
			response = await client.create(
				response_model=TechnicalQuestionsResponse,
				messages=[
					{"role": "system", "content": TECH_SYSTEM_PROMPT},
					{
						"role": "user",
						"content": (
							"Skills:\n"
							+ "\n".join(f"- {skill}" for skill in skills)
							+ f"\n\nGenerate {n} questions."
						),
					},
				],
			)
			return [item.model_dump() for item in response.questions]
		except Exception as exc:
			logger.error(
				"[QuestionGenerator] Failed to generate questions: %s",
				exc,
			)
			return []

	async def generate_dsa_question(
		self,
		skills: list[str],
		provider: str | None = None,
		topic: Literal[
			"arrays",
			"strings",
			"hashmap",
			"two-pointers",
			"sliding-window",
			"stack",
			"queue",
			"binary-search",
			"sorting",
			"greedy",
			"dynamic-programming",
			"trees",
			"graphs",
		] | None = None,
	) -> dict:
		"""
		Generate a single DSA coding question (LeetCode style).

		Args:
			skills: Parsed resume skills to add context.
			provider: Optional LiteLLM provider string.
			topic: Optional topic hint (e.g. "sliding-window").

		Returns:
			Object with title, prompt, constraints, examples, and sample_cases.
			Returns {} on error.
		"""
		client = self._client(provider)

		logger.info(
			"[QuestionGenerator] Generating DSA question (skills=%d, topic=%s)",
			len(skills),
			topic or "any",
		)

		try:
			topic_line = f"Topic hint: {topic}.\n" if topic else ""
			content = (
				topic_line
				+ "Skills (context only, do not overfit):\n"
				+ "\n".join(f"- {skill}" for skill in skills)
			)
			response = await client.create(
				response_model=DsaQuestionResponse,
				messages=[
					{"role": "system", "content": DSA_SYSTEM_PROMPT},
					{"role": "user", "content": content},
				],
			)
			return response.question.model_dump()
		except Exception as exc:
			logger.error(
				"[QuestionGenerator] Failed to generate DSA question: %s",
				exc,
			)
			return {}

	async def generate_sql_question(
		self,
		skills: list[str],
		provider: str | None = None,
		topic: Literal[
			"joins",
			"aggregation",
			"window-functions",
			"subqueries",
			"cte",
			"date-time",
			"string-manipulation",
		] | None = None,
	) -> dict:
		"""
		Generate a single SQL interview question.

		Args:
			skills: Parsed resume skills to add context.
			provider: Optional LiteLLM provider string.
			topic: Optional topic hint (e.g. "joins").

		Returns:
			Object with title, prompt, schema, examples, and sample_cases.
			Returns {} on error.
		"""
		client = self._client(provider)

		logger.info(
			"[QuestionGenerator] Generating SQL question (skills=%d, topic=%s)",
			len(skills),
			topic or "any",
		)

		try:
			topic_line = f"Topic hint: {topic}.\n" if topic else ""
			content = (
				topic_line
				+ "Skills (context only, do not overfit):\n"
				+ "\n".join(f"- {skill}" for skill in skills)
			)
			response = await client.create(
				response_model=SqlQuestionResponse,
				messages=[
					{"role": "system", "content": SQL_SYSTEM_PROMPT},
					{"role": "user", "content": content},
				],
			)
			return response.question.model_dump()
		except Exception as exc:
			logger.error(
				"[QuestionGenerator] Failed to generate SQL question: %s",
				exc,
			)
			return {}

