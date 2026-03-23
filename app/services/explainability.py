from __future__ import annotations

from app.domain.models import UserProfile, Vacancy


def split_tokens(value: str) -> set[str]:
    normalized = value.lower().replace("/", " ").replace(",", " ")
    return {item.strip() for item in normalized.split() if item.strip()}


def build_explainability(profile: UserProfile, vacancy: Vacancy) -> dict:
    profile_skills = split_tokens(profile.skills)
    vacancy_skills = {skill.lower().strip() for skill in vacancy.skills}
    overlap = sorted(profile_skills.intersection(vacancy_skills))

    reasons: list[str] = []
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
