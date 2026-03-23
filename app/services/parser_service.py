from __future__ import annotations

import datetime
from typing import Any

from app.core.config import settings
from app.services.vacancy_service import VacancyService
from app.storage.db import get_connection
from app.storage.hh_parser import run

DEFAULT_QUERIES = [
    "Python developer",
    "Python backend developer",
    "Python engineer",
    "Java developer",
    "Java backend developer",
    "Backend developer",
    "backend engineer",
    "data engineer",
    "аналитик данных",
    "data analyst",
    "системный аналитик",
    "business analyst",
    "QA engineer",
    "тестировщик",
    "DevOps",
    "SRE",
    "ML engineer",
    "data scientist",
]

class ParserService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.vacancy_service = VacancyService(db_path)

    def get_existing_vacancy_ids(self) -> set[str]:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vacancy_id FROM vacancies")
            return {row[0] for row in cursor.fetchall()}

    @staticmethod
    def _queries() -> list[str]:
        raw = settings.parser_queries_raw.strip()
        if not raw:
            return DEFAULT_QUERIES
        parts = [item.strip() for item in raw.replace("\n", "|").split("|")]
        return [item for item in parts if item]

    @staticmethod
    def _max_vacancies() -> int | None:
        return settings.parser_max_vacancies or None

    def parse_and_store_vacancies(self, queries: list[str], area: str = "1", pages: int = 1) -> int:
        vacancies = run(
            queries=queries,
            area=area,
            pages_per_query=pages,
            delay=settings.parser_delay_seconds,
            max_vacancies=self._max_vacancies(),
            order_by="publication_time",
            search_period=settings.parser_search_period_days,
        )

        self.vacancy_service.save_vacancies(vacancies)
        return len(vacancies)

    def daily_update(self) -> None:
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        vacancies = run(
            queries=self._queries(),
            area=settings.parser_area,
            pages_per_query=settings.parser_daily_pages_per_query,
            delay=settings.parser_delay_seconds,
            max_vacancies=self._max_vacancies(),
            order_by="publication_time",
            search_period=settings.parser_daily_search_period_days,
            posted_since=yesterday,
            skip_if_no_posted_date=True,
        )

        if vacancies:
            self.vacancy_service.save_vacancies(vacancies)

    def run_parser(self) -> dict[str, Any]:
        parsed_count = self.parse_and_store_vacancies(
            queries=self._queries(),
            area=settings.parser_area,
            pages=settings.parser_pages_per_query,
        )

        return {
            "status": "success",
            "message": "Vacancy parsing completed",
            "vacancies_parsed": parsed_count,
            "vacancies_total": len(self.vacancy_service.load_vacancies()),
            "queries_used": len(self._queries()),
            "pages_per_query": settings.parser_pages_per_query,
            "search_period_days": settings.parser_search_period_days,
        }
