from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class InterviewStartRequest(BaseModel):
    user_id: int
    telegram_username: Optional[str] = None


class InterviewStartResponse(BaseModel):
    session_id: int
    stage: str
    question_index: int
    question_text: str


class InterviewAnswerRequest(BaseModel):
    user_id: int
    answer_text: str = Field(min_length=1, max_length=4000)


class InterviewAnswerResponse(BaseModel):
    session_id: int
    stage: str
    question_index: int
    completed: bool
    next_question: Optional[str] = None


class ResumeGenerateRequest(BaseModel):
    user_id: int


class VacancyMatchRequest(BaseModel):
    user_id: int
    top_k: int = 5


class CoverLetterRequest(BaseModel):
    user_id: int
    vacancy_id: str


class SkillGapsRequest(BaseModel):
    user_id: int
    vacancy_id: str


class FeedbackRequest(BaseModel):
    user_id: int
    session_id: Optional[int] = None
    item_type: str
    item_id: Optional[str] = None
    is_positive: bool
    comment: Optional[str] = None
