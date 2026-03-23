from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.domain.interview_fsm import InterviewFSM
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.matching_service import MatchingService
from app.services.parser_service import ParserService
from app.services.profile_service import ProfileService
from app.services.vacancy_service import VacancyService
from app.storage.repositories import (
    ArtifactRepository,
    FeedbackRepository,
    InterviewAnswerRepository,
    SessionRepository,
    UserRepository,
)


@dataclass
class Container:
    user_repo: UserRepository
    session_repo: SessionRepository
    answer_repo: InterviewAnswerRepository
    artifact_repo: ArtifactRepository
    feedback_repo: FeedbackRepository
    profile_service: ProfileService
    embedding_service: EmbeddingService
    matching_service: MatchingService
    vacancy_service: VacancyService
    parser_service: ParserService
    llm_service: LLMService
    fsm: InterviewFSM


def build_container() -> Container:
    user_repo = UserRepository(settings.sqlite_path)
    session_repo = SessionRepository(settings.sqlite_path)
    answer_repo = InterviewAnswerRepository(settings.sqlite_path)
    artifact_repo = ArtifactRepository(settings.sqlite_path)
    feedback_repo = FeedbackRepository(settings.sqlite_path)
    profile_service = ProfileService()
    embedding_service = EmbeddingService()
    matching_service = MatchingService(embedding_service)
    vacancy_service = VacancyService(settings.sqlite_path)
    parser_service = ParserService(settings.sqlite_path)
    llm_service = LLMService()
    if settings.preload_models_on_startup:
        embedding_service.warmup()
        llm_service.warmup()
    fsm = InterviewFSM()
    return Container(
        user_repo=user_repo,
        session_repo=session_repo,
        answer_repo=answer_repo,
        artifact_repo=artifact_repo,
        feedback_repo=feedback_repo,
        profile_service=profile_service,
        embedding_service=embedding_service,
        matching_service=matching_service,
        vacancy_service=vacancy_service,
        parser_service=parser_service,
        llm_service=llm_service,
        fsm=fsm,
    )


container = build_container()
