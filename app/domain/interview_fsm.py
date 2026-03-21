from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.models import INTERVIEW_QUESTIONS_RU


@dataclass
class InterviewTransition:
    next_stage: str
    next_question_index: int
    completed: bool
    ask_question: Optional[str]


class InterviewFSM:
    START_STAGE = "ONBOARDING"
    REVIEW_STAGE = "PROFILE_REVIEW"
    COMPLETED_STAGE = "COMPLETED"

    def start(self) -> InterviewTransition:
        return InterviewTransition(
            next_stage="INTERVIEW_Q1",
            next_question_index=0,
            completed=False,
            ask_question=INTERVIEW_QUESTIONS_RU[0],
        )

    def answer(self, question_index: int) -> InterviewTransition:
        next_idx = question_index + 1
        if next_idx >= len(INTERVIEW_QUESTIONS_RU):
            return InterviewTransition(
                next_stage=self.REVIEW_STAGE,
                next_question_index=question_index,
                completed=True,
                ask_question=None,
            )
        return InterviewTransition(
            next_stage=f"INTERVIEW_Q{next_idx + 1}",
            next_question_index=next_idx,
            completed=False,
            ask_question=INTERVIEW_QUESTIONS_RU[next_idx],
        )
