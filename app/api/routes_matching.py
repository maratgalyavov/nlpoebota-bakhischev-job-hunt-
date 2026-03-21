from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import container
from app.api.schemas import FeedbackRequest, VacancyMatchRequest

router = APIRouter(prefix="/v1", tags=["matching"])


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

