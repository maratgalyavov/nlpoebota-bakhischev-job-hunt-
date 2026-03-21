from __future__ import annotations

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.matching_service import MatchingService
from app.services.vacancy_service import VacancyService


def main() -> None:
    vacancy_service = VacancyService(settings.vacancies_path)
    embedding_service = EmbeddingService()
    matching_service = MatchingService(embedding_service)

    vacancies = vacancy_service.load_vacancies()
    index = matching_service.build_index(vacancies)
    index.save(settings.faiss_index_path)
    print(f"Built FAISS index with {len(vacancies)} vacancies at {settings.faiss_index_path}")


if __name__ == "__main__":
    main()

