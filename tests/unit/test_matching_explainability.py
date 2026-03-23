from app.domain.models import UserProfile, Vacancy
from app.services.explainability import build_explainability


def test_build_explainability_contains_skills_and_reasons() -> None:
    profile = UserProfile(
        user_id=1,
        role="Python Developer",
        experience="2 years",
        education="CS",
        skills="Python, FastAPI, SQL",
        salary_expectation="200000",
        preferred_location="Remote",
        employment_type="full-time",
        characteristics="ответственный",
    )
    vacancy = Vacancy(
        id="v1",
        title="Python Developer",
        company="A",
        description="Python backend",
        skills=["Python", "FastAPI", "Docker"],
        salary_from=120,
        salary_to=220,
        location="Remote",
        url="u",
        posted_date="2026-01-01",
        active_flg=True,
    )

    payload = build_explainability(profile, vacancy)
    assert "reasons" in payload
    assert "matched_skills" in payload
    assert "python" in payload["matched_skills"]

