from typing import TypedDict, List, Optional
import logging

logger = logging.getLogger(__name__)

class InterviewState(TypedDict):
    candidate_id: str
    current_stage: str  # "INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT"
    status: str  # "initializing", "processing", "ready", "error"
    resume_text: str
    jd_text: str
    matched_skills: List[dict]  # [{"skill": "Python", "match_level": "high"}]
    technical_questions: List[dict]
    dsa_question: Optional[dict]
    sql_question: Optional[dict]
    current_question_index: int
    transcript: List[dict]
    feedback: List[str]
    code_submission: Optional[str]
    code_grade: Optional[dict]
    ui_view: str  # "avatar", "skills", "monaco", "report"
    error_message: Optional[str]  # For error state
    context_summary: Optional[str]  # For sliding window summarization

# Valid stages for type safety
VALID_STAGES = {"INITIALIZING", "PROCESSING", "INTRO", "EXPERIENCE", "DSA", "SQL", "REPORT", "ERROR"}

# Simple In-Memory Store for the Demo
# Keyed by candidate_id
class InterviewStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InterviewStore, cls).__new__(cls)
            cls._instance._data = {}  # Instance-level, not class-level
        return cls._instance

    def get(self, candidate_id: str) -> Optional[InterviewState]:
        return self._data.get(candidate_id)

    def set(self, candidate_id: str, state: InterviewState):
        self._data[candidate_id] = state
        logger.info(f"Stored state for candidate: {candidate_id}")

    def update(self, candidate_id: str, **kwargs):
        if candidate_id not in self._data:
            logger.warning(f"Candidate {candidate_id} not found in store")
            return
        
        # Validate current_stage if being updated
        if "current_stage" in kwargs:
            new_stage = kwargs["current_stage"]
            if new_stage not in VALID_STAGES:
                raise ValueError(f"Invalid stage: {new_stage}. Must be one of {VALID_STAGES}")
        
        self._data[candidate_id].update(kwargs)
        logger.info(f"Updated state for candidate: {candidate_id}")

    def delete(self, candidate_id: str):
        """Clean up store on disconnect"""
        if candidate_id in self._data:
            del self._data[candidate_id]
            logger.info(f"Deleted state for candidate: {candidate_id}")

store = InterviewStore()
