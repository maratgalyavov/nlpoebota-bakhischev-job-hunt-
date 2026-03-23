from __future__ import annotations

import numpy as np

from app.domain.models import Recommendation, UserProfile, Vacancy
from app.services.embedding_service import EmbeddingService
from app.storage.faiss_index import FaissIndex


class MatchingService:
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    @staticmethod
    def _vacancy_to_text(vacancy: Vacancy) -> str:
        return (
            f"{vacancy.title}. {vacancy.company}. {vacancy.description}. "
            f"Навыки: {', '.join(vacancy.skills)}. Локация: {vacancy.location}."
        )

    def build_index(self, vacancies: list[Vacancy]) -> FaissIndex:
        ids = [vacancy.id for vacancy in vacancies]
        texts = [self._vacancy_to_text(vacancy) for vacancy in vacancies]
        matrix = (
            self.embedding_service.encode_many(texts).astype("float32")
            if texts
            else np.zeros((0, 384), dtype="float32")
        )
        dim = int(matrix.shape[1]) if matrix.size else 384
        index = FaissIndex(dim=dim)
        if len(ids) > 0:
            index.add(ids, matrix)
        return index

    def recommend(
        self,
        profile: UserProfile,
        index: FaissIndex,
        top_k: int = 5,
    ) -> list[Recommendation]:
        profile_vec = self.embedding_service.encode_queries([profile.to_text()])[0]
        results = index.search(profile_vec, top_k=top_k)
        return [Recommendation(vacancy_id=vacancy_id, score=score) for vacancy_id, score in results]
