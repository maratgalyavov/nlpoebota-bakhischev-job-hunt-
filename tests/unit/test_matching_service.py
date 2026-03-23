from app.domain.models import UserProfile, Vacancy
from app.services.embedding_service import EmbeddingService
from app.services.matching_service import MatchingService


def test_matching_service_returns_ranked_items() -> None:
    embeddings = EmbeddingService()
    embeddings._provider = "mock"
    service = MatchingService(embeddings)

    vacancies = [
        Vacancy(
            id="v1",
            title="Python Developer",
            company="A",
            description="Python FastAPI SQL",
            skills=["Python", "FastAPI", "SQL"],
            salary_from=100,
            salary_to=200,
            location="Remote",
            url="u1",
            posted_date="2026-01-01",
            active_flg=True,
        ),
        Vacancy(
            id="v2",
            title="Designer",
            company="B",
            description="Figma UI UX",
            skills=["Figma", "UI", "UX"],
            salary_from=100,
            salary_to=200,
            location="Remote",
            url="u2",
            posted_date="2026-01-01",
            active_flg=True,
        ),
    ]
    index = service.build_index(vacancies)
    profile = UserProfile(
        user_id=1,
        role="Backend developer",
        experience="2 years Python",
        education="CS",
        education_domain="Computer Science",
        projects="Pet project: HR assistant bot",
        skills="Python, FastAPI, SQL",
        salary_expectation="200000",
        preferred_location="Remote",
        employment_type="full-time",
        characteristics="ответственный",
    )
    recs = service.recommend(profile, index, top_k=2)
    assert len(recs) == 2
    assert recs[0].vacancy_id in {"v1", "v2"}
