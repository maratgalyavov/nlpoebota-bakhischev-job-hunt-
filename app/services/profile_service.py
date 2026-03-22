from __future__ import annotations

from app.domain.models import UserProfile


class ProfileService:
    @staticmethod
    def from_answers(user_id: int, answers: list[dict]) -> UserProfile:
        def get(idx: int) -> str:
            return answers[idx]["answer_text"] if idx < len(answers) else ""

        return UserProfile(
            user_id=user_id,
            experience=get(0),
            skills=get(1),
            education=get(2),
            role=get(3),
            salary_expectation=get(4),
            preferred_location=get(5),
            employment_type=get(6),
            characteristics=get(7),
        )
