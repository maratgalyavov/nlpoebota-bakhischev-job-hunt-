from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import container
from app.api.schemas import FeedbackRequest, VacancyMatchRequest

router = APIRouter(prefix="/v1", tags=["matching"])


def _split_tokens(value: str) -> set[str]:
    normalized = value.lower().replace("/", " ").replace(",", " ")
    return {item.strip() for item in normalized.split() if item.strip()}


def _build_explainability(profile, vacancy) -> dict:
    profile_skills = _split_tokens(profile.skills)
    vacancy_skills = {skill.lower().strip() for skill in vacancy.skills}
    overlap = sorted(profile_skills.intersection(vacancy_skills))

    reasons = []
    if overlap:
        reasons.append(f"Совпадающие навыки: {', '.join(overlap[:5])}")

    profile_location = profile.preferred_location.lower().strip()
    vacancy_location = vacancy.location.lower()
    if profile_location and profile_location in vacancy_location:
        reasons.append(f"Подходит локация: {vacancy.location}")

    if profile.role and profile.role.lower() in vacancy.title.lower():
        reasons.append(f"Роль близка к целевой: {profile.role}")

    if not reasons:
        reasons.append("Похоже по общему описанию опыта и требований вакансии")

    missing = sorted(vacancy_skills - profile_skills)
    return {
        "reasons": reasons,
        "matched_skills": overlap,
        "missing_skills_preview": missing[:5],
    }


@router.post("/match/vacancies")
def match_vacancies(payload: VacancyMatchRequest) -> dict:
    session = container.session_repo.get_last_session(payload.user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        raise HTTPException(status_code=400, detail="Interview answers are empty")

    profile = container.profile_service.from_answers(payload.user_id, answers)
    vacancies = container.vacancy_service.load_vacancies()
    index = container.matching_service.build_index(vacancies)
    recommendations = container.matching_service.recommend(profile, index, top_k=payload.top_k)

    by_id = {v.id: v for v in vacancies}
    result = []
    for rec in recommendations:
        vacancy = by_id.get(rec.vacancy_id)
        if vacancy is None:
            continue
        result.append(
            {
                "vacancy_id": vacancy.id,
                "title": vacancy.title,
                "company": vacancy.company,
                "location": vacancy.location,
                "url": vacancy.url,
                "score": round(float(rec.score), 4),
                "explainability": _build_explainability(profile, vacancy),
            }
        )
    return {"items": result}


@router.post("/feedback")
def add_feedback(payload: FeedbackRequest) -> dict:
    container.feedback_repo.add_feedback(
        user_id=payload.user_id,
        session_id=payload.session_id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        is_positive=payload.is_positive,
        comment=payload.comment,
    )
    return {"status": "ok"}
