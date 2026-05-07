"""
Shared LLM client helpers - using Instructor with Vertex AI (v2 SDK pattern).
"""
from __future__ import annotations

import os
import logging
from typing import Any
import instructor
from google import genai

logger = logging.getLogger(__name__)

_client_cache: dict[str, Any] = {}

# Use the latest gemini-2.5-flash for Vertex AI
DEFAULT_PROVIDER = "vertexai/gemini-2.5-flash"

def resolve_provider(override: str | None, env_var: str, default: str) -> str:
    """Resolve provider from explicit override or environment variable."""
    return override or os.getenv(env_var, default)

def get_instructor_client(provider: str = None):
    """Return a cached Instructor async client for Gemini using Vertex AI (Recommended Way)."""
    provider = resolve_provider(provider, "JD_MATCH_PROVIDER", DEFAULT_PROVIDER)
    
    client = _client_cache.get(provider)
    if client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if project_id and "vertexai" in provider:
            logger.info(f"Initializing Instructor via from_provider (Vertex AI: {project_id})")
            # Pattern: instructor.from_provider("vertexai/model", project=..., location=..., async_client=True)
            client = instructor.from_provider(
                provider,
                project=project_id,
                location=location,
                async_client=True
            )
        else:
            # Fallback for standard AI Studio or non-vertex providers
            logger.info(f"Initializing Instructor via from_provider (Standard/AI Studio: {provider})")
            client = instructor.from_provider(
                provider,
                async_client=True
            )
            
        _client_cache[provider] = client
        
    return client
