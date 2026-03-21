from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import container
from app.api.schemas import CoverLetterRequest, ResumeGenerateRequest, SkillGapsRequest

router = APIRouter(prefix="/v1/generate", tags=["generation"])


def _get_profile_text(user_id: int) -> tuple[int, str]:
    session = container.session_repo.get_last_session(user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    answers = container.answer_repo.list_answers(session.session_id)
    if not answers:
        raise HTTPException(status_code=400, detail="Interview answers are empty")
    profile = container.profile_service.from_answers(user_id, answers)
    return session.session_id, profile.to_text()


@router.post("/resume")
def generate_resume(payload: ResumeGenerateRequest) -> dict:
    session_id, profile_text = _get_profile_text(payload.user_id)
    resume = container.llm_service.generate_resume(profile_text)
    container.artifact_repo.save_artifact(
        user_id=payload.user_id,
        session_id=session_id,
        artifact_type="resume",
        content=resume,
    )
    return {"resume": resume}


@router.post("/cover-letter")
def generate_cover_letter(payload: CoverLetterRequest) -> dict:
    session_id, profile_text = _get_profile_text(payload.user_id)
    vacancies = container.vacancy_service.load_vacancies()
    selected = next((v for v in vacancies if v.id == payload.vacancy_id), None)
    if selected is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    vacancy_text = f"{selected.title}. {selected.company}. {selected.description}"
    cover = container.llm_service.generate_cover_letter(profile_text, vacancy_text)
    container.artifact_repo.save_artifact(
        user_id=payload.user_id,
        session_id=session_id,
        artifact_type="cover_letter",
        content=cover,
        meta_json=f'{{"vacancy_id":"{selected.id}"}}',
    )
    return {"cover_letter": cover}


@router.post("/skill-gaps")
def generate_skill_gaps(payload: SkillGapsRequest) -> dict:
    session_id, profile_text = _get_profile_text(payload.user_id)
    vacancies = container.vacancy_service.load_vacancies()
    selected = next((v for v in vacancies if v.id == payload.vacancy_id), None)
    if selected is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    vacancy_text = f"{selected.title}. {selected.company}. {selected.description}"
    gaps = container.llm_service.generate_skill_gaps(profile_text, vacancy_text)
    container.artifact_repo.save_artifact(
        user_id=payload.user_id,
        session_id=session_id,
        artifact_type="skill_gaps",
        content=gaps,
        meta_json=f'{{"vacancy_id":"{selected.id}"}}',
    )
    return {"skill_gaps": gaps}

