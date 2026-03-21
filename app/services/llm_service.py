from __future__ import annotations

from app.core.config import settings
from app.domain.prompts import (
    build_cover_letter_prompt,
    build_resume_prompt,
    build_skill_gaps_prompt,
)


class LLMService:
    def __init__(self) -> None:
        self.model_name = settings.llm_model
        self.use_mock = settings.use_mock_llm

    def _mock_generate(self, prompt: str, mode: str) -> str:
        if mode == "resume":
            return (
                "# Резюме\n\n"
                "## О себе\nКандидат мотивирован развиваться и применять опыт на практике.\n\n"
                "## Опыт\nОпыт сформирован на основе ответов интервью.\n\n"
                "## Навыки\nКлючевые технические и soft skills из профиля пользователя.\n\n"
                "## Образование\nУказано пользователем в интервью."
            )
        if mode == "cover":
            return (
                "Здравствуйте! Меня заинтересовала ваша вакансия. "
                "Мой опыт и навыки соответствуют ключевым требованиям позиции. "
                "Умею быстро погружаться в задачи, работать в команде и брать ответственность за результат. "
                "Буду рад обсудить, как могу принести пользу вашей команде."
            )
        return (
            "1) Недостающие навыки: уточнить стек вакансии и углубить профильные знания.\n"
            "2) Приоритет: высокий.\n"
            "3) План: пройти профильный курс, сделать проект, добавить кейсы в резюме."
        )

    def _generate(self, prompt: str, mode: str) -> str:
        if self.use_mock:
            return self._mock_generate(prompt, mode)
        # Placeholder for real provider integration in next iteration.
        return self._mock_generate(prompt, mode)

    def generate_resume(self, profile_text: str) -> str:
        prompt = build_resume_prompt(profile_text)
        return self._generate(prompt, mode="resume")

    def generate_cover_letter(self, profile_text: str, vacancy_text: str) -> str:
        prompt = build_cover_letter_prompt(profile_text, vacancy_text)
        return self._generate(prompt, mode="cover")

    def generate_skill_gaps(self, profile_text: str, vacancy_text: str) -> str:
        prompt = build_skill_gaps_prompt(profile_text, vacancy_text)
        return self._generate(prompt, mode="gaps")

