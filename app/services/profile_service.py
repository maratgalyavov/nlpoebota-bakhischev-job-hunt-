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
            education_domain=get(3),
            projects=get(4),
            role=get(5),
            salary_expectation=get(6),
            preferred_location=get(7),
            employment_type=get(8),
            characteristics=get(9),
        )
