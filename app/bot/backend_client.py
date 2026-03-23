from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BackendClientError(RuntimeError):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class BackendNotFoundError(BackendClientError):
    pass


@dataclass(frozen=True)
class InterviewStart:
    session_id: int
    stage: str
    question_index: int
    question_text: str


@dataclass(frozen=True)
class InterviewState:
    session_id: int
    stage: str
    question_index: int
    completed: bool
    next_question: Optional[str]


@dataclass(frozen=True)
class MatchItem:
    vacancy_id: str
    title: str
    company: str
    location: str
    url: str
    score: float
    description_preview: str
    salary_from: int
    salary_to: int
    explainability: dict[str, Any]


def _backend_url(path: str) -> str:
    return f"{settings.bot_backend_url.rstrip('/')}{path}"


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    if isinstance(payload, str):
        return payload
    return ""


def _normalize_error_message(status_code: int, detail: str) -> str:
    known_messages = {
        (400, "Interview answers are empty"): "Сначала пройди интервью и ответь на вопросы в чате.",
        (404, "Session not found"): "Сначала нажми /start или «Новое интервью».",
        (404, "Vacancy not found"): "Вакансия не найдена.",
    }
    if (status_code, detail) in known_messages:
        return known_messages[(status_code, detail)]
    if detail:
        return detail
    return "Бэкенд сейчас недоступен. Попробуй ещё раз чуть позже."


async def _request_json(
    method: str,
    path: str,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    url = _backend_url(path)
    timeout = httpx.Timeout(settings.bot_backend_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("Backend request failed: %s %s: %s", method, url, exc)
        raise BackendClientError("Бэкенд сейчас недоступен. Попробуй ещё раз чуть позже.") from exc

    if response.status_code >= 400:
        message = _normalize_error_message(response.status_code, _extract_error_detail(response))
        if response.status_code == 404:
            raise BackendNotFoundError(message)
        raise BackendClientError(message)

    try:
        data = response.json()
    except ValueError as exc:
        logger.warning("Backend returned non-JSON response for %s %s", method, url)
        raise BackendClientError("Бэкенд вернул неожиданный ответ.") from exc
    if not isinstance(data, dict):
        raise BackendClientError("Бэкенд вернул неожиданный ответ.")
    return data


async def start_interview(user_id: int, telegram_username: Optional[str]) -> InterviewStart:
    payload = await _request_json(
        "POST",
        "/v1/interview/start",
        {"user_id": user_id, "telegram_username": telegram_username},
    )
    return InterviewStart(
        session_id=int(payload["session_id"]),
        stage=str(payload["stage"]),
        question_index=int(payload["question_index"]),
        question_text=str(payload["question_text"]),
    )


async def answer_interview(user_id: int, answer_text: str) -> InterviewState:
    payload = await _request_json(
        "POST",
        "/v1/interview/answer",
        {"user_id": user_id, "answer_text": answer_text},
    )
    return InterviewState(
        session_id=int(payload["session_id"]),
        stage=str(payload["stage"]),
        question_index=int(payload["question_index"]),
        completed=bool(payload["completed"]),
        next_question=payload.get("next_question"),
    )


async def get_interview_state(user_id: int) -> InterviewState:
    payload = await _request_json("GET", f"/v1/interview/state/{user_id}")
    return InterviewState(
        session_id=int(payload["session_id"]),
        stage=str(payload["stage"]),
        question_index=int(payload["question_index"]),
        completed=bool(payload["completed"]),
        next_question=payload.get("next_question"),
    )


async def generate_resume(user_id: int) -> str:
    payload = await _request_json("POST", "/v1/generate/resume", {"user_id": user_id})
    return str(payload["resume"])


async def match_vacancies(user_id: int, top_k: int = 5) -> list[MatchItem]:
    payload = await _request_json(
        "POST",
        "/v1/match/vacancies",
        {"user_id": user_id, "top_k": top_k},
    )
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise BackendClientError("Бэкенд вернул неожиданный формат вакансий.")
    return [
        MatchItem(
            vacancy_id=str(item["vacancy_id"]),
            title=str(item["title"]),
            company=str(item["company"]),
            location=str(item.get("location") or ""),
            url=str(item.get("url") or ""),
            score=float(item["score"]),
            description_preview=str(item.get("description_preview") or ""),
            salary_from=int(item.get("salary_from") or 0),
            salary_to=int(item.get("salary_to") or 0),
            explainability=item.get("explainability") or {},
        )
        for item in raw_items
        if isinstance(item, dict)
    ]


async def generate_cover_letter(user_id: int, vacancy_id: str) -> str:
    payload = await _request_json(
        "POST",
        "/v1/generate/cover-letter",
        {"user_id": user_id, "vacancy_id": vacancy_id},
    )
    return str(payload["cover_letter"])


async def generate_skill_gaps(user_id: int, vacancy_id: str) -> str:
    payload = await _request_json(
        "POST",
        "/v1/generate/skill-gaps",
        {"user_id": user_id, "vacancy_id": vacancy_id},
    )
    return str(payload["skill_gaps"])


async def add_feedback(
    user_id: int,
    item_type: str,
    item_id: Optional[str],
    is_positive: bool,
    comment: Optional[str] = None,
    session_id: Optional[int] = None,
) -> None:
    await _request_json(
        "POST",
        "/v1/feedback",
        {
            "user_id": user_id,
            "session_id": session_id,
            "item_type": item_type,
            "item_id": item_id,
            "is_positive": is_positive,
            "comment": comment,
        },
    )
