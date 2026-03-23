from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

INTERVIEW_QUESTIONS_RU = [
    "Подробно расскажи про свой опыт работы (сколько лет / какие позиции / какой вклад)",
    "Какими инструментами и технологиями ты владеешь?",
    "Какое у тебя образование?",
    "Какое у тебя направление / профиль образования?",
    "Какие проекты, пет-проекты, кейсы или заметные достижения хочешь добавить в резюме?",
    "Какую роль ты ищешь?",
    "Какая желаемая зарплата (в рублях, от)?",
    "Какой формат работы предпочитаешь (remote / офис / гибрид)?",
    "Какая занятость тебе подходит (полная / частичная)?",
    "Какие основные личностные качества ты считаешь своими сильными сторонами?",
]


@dataclass
class InterviewState:
    user_id: int
    session_id: int
    stage: str
    question_index: int
    completed: bool


@dataclass
class UserProfile:
    user_id: int
    role: str
    experience: str
    education: str
    education_domain: str
    projects: str
    skills: str
    salary_expectation: str
    preferred_location: str
    employment_type: str
    characteristics: str

    def to_text(self) -> str:
        return (
            f"Роль: {self.role}. "
            f"Опыт: {self.experience}. "
            f"Навыки: {self.skills}. "
            f"Образование: {self.education}. "
            f"Профиль образования: {self.education_domain}. "
            f"Проекты и достижения: {self.projects}. "
            f"Ожидаемая зарплата: {self.salary_expectation}. "
            f"Локация: {self.preferred_location}. "
            f"Занятость: {self.employment_type}. "
            f"Личностные качества: {self.characteristics}."
        )


@dataclass
class Vacancy:
    id: str
    title: str
    company: str
    description: str
    skills: list[str]
    salary_from: int
    salary_to: int
    location: str
    url: str
    posted_date: str
    active_flg: bool

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Vacancy":
        raw_skills = payload.get("skills", [])
        if isinstance(raw_skills, str):
            try:
                parsed = json.loads(raw_skills) if raw_skills else []
            except json.JSONDecodeError:
                parsed = []
            skills = [str(s) for s in parsed] if isinstance(parsed, list) else []
        else:
            skills = [str(s) for s in (raw_skills or [])]

        return cls(
            id=str(payload["id"]),
            title=payload["title"],
            company=payload["company"],
            description=payload["description"],
            skills=skills,
            salary_from=payload.get("salary_from", 0) or 0,
            salary_to=payload.get("salary_to", 0) or 0,
            location=payload.get("location", ""),
            url=payload.get("url", ""),
            posted_date=payload.get("posted_date", ""),
            active_flg=bool(payload.get("active_flg", True)),
        )


@dataclass
class Recommendation:
    vacancy_id: str
    score: float
