"""
InterviewState — single source of truth for a candidate's session.

Stored in the flat InterviewStore (in-memory dict) and also used as
the LangGraph state schema with MemorySaver checkpointing.
"""
from typing import TypedDict, List, Optional
import logging

logger = logging.getLogger(__name__)

# ── Valid stage names ────────────────────────────────────────────────────────
STAGES = ["INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"]
VALID_STAGES = {"INITIALIZING", "PROCESSING", "ERROR", *STAGES}

# ── Stage → UI view mapping ──────────────────────────────────────────────────
STAGE_UI_VIEW: dict[str, str] = {
    "INTRO":       "avatar",
    "EXPERIENCE":  "avatar",
    "DSA":         "monaco",
    "SQL":         "monaco",
    "REPORT":      "report",
}

# ── Stage → next stage mapping ───────────────────────────────────────────────
STAGE_TRANSITIONS: dict[str, str] = {
    "INTRO":      "EXPERIENCE",
    "EXPERIENCE": "DSA",
    "DSA":        "SQL",
    "SQL":        "REPORT",
}


class InterviewState(TypedDict):
    # Identity
    candidate_id: str
    candidate_name: Optional[str]

    # Lifecycle
    status: str          # "initializing" | "processing" | "ready" | "error"
    current_stage: str   # one of STAGES (or INITIALIZING/PROCESSING/ERROR)
    ui_view: str         # "avatar" | "monaco" | "report"

    # Resume & JD
    resume_text: str
    jd_text: str

    # Pre-generated content (from background tasks)
    matched_skills: List[dict]          # [{skill, match_level}]
    technical_questions: List[dict]     # [{question}]
    dsa_question: Optional[dict]        # {title, prompt, constraints, examples, sample_cases}
    sql_question: Optional[dict]        # {title, prompt, sql_schema, examples, sample_cases}
    questions_ready: bool               # True once background generation is complete

    # Session tracking
    current_question_index: int
    transcript: List[dict]              # [{role, text, stage, timestamp}]

    # Context window — one summary per completed stage (appended, never overwritten)
    past_summaries: List[str]

    # Code submissions
    code_submission: Optional[str]
    code_grade: Optional[dict]

    # Error handling
    error_message: Optional[str]


# ── Singleton in-memory store ────────────────────────────────────────────────
class InterviewStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, InterviewState] = {}
        return cls._instance

    def get(self, candidate_id: str) -> Optional[InterviewState]:
        return self._data.get(candidate_id)

    def set(self, candidate_id: str, state: InterviewState):
        self._data[candidate_id] = state
        logger.info(f"[Store] Set state for candidate: {candidate_id[:8]}")

    def update(self, candidate_id: str, **kwargs):
        if candidate_id not in self._data:
            logger.warning(f"[Store] Candidate {candidate_id[:8]} not found — cannot update")
            return
        if "current_stage" in kwargs:
            stage = kwargs["current_stage"]
            if stage not in VALID_STAGES:
                raise ValueError(f"[Store] Invalid stage: {stage}")
        self._data[candidate_id].update(kwargs)
        logger.debug(f"[Store] Updated {list(kwargs.keys())} for {candidate_id[:8]}")

    def append_transcript(self, candidate_id: str, role: str, text: str, stage: str):
        """Thread-safe transcript append."""
        import time
        state = self._data.get(candidate_id)
        if state is None:
            return
        state["transcript"].append({
            "role": role,
            "text": text,
            "stage": stage,
            "timestamp": time.time(),
        })

    def append_summary(self, candidate_id: str, summary: str):
        """Append a completed stage summary to past_summaries."""
        state = self._data.get(candidate_id)
        if state and summary:
            state["past_summaries"].append(summary)
            logger.info(f"[Store] Appended summary for {candidate_id[:8]}: {summary[:60]}...")

    def delete(self, candidate_id: str):
        if candidate_id in self._data:
            del self._data[candidate_id]
            logger.info(f"[Store] Deleted session for {candidate_id[:8]}")


store = InterviewStore()
