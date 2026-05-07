"""
Shared LLM client helpers.
"""
from __future__ import annotations

import os
from typing import Any

import instructor

_client_cache: dict[str, Any] = {}


def resolve_provider(override: str | None, env_var: str, default: str) -> str:
	"""Resolve provider from explicit override or environment variable."""
	return override or os.getenv(env_var, default)


def get_instructor_client(provider: str):
	"""Return a cached Instructor async client for a provider."""
	provider = resolve_provider(provider, "JD_MATCH_PROVIDER", "groq/llama-3.3-70b-versatile")
	client = _client_cache.get(provider)
	if client is None:
		client = instructor.from_provider(provider, async_client=True)
		_client_cache[provider] = client
	return client

