from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import Vacancy


class VacancyService:
    def __init__(self, vacancies_path: str) -> None:
        self.vacancies_path = vacancies_path

    def load_vacancies(self) -> list[Vacancy]:
        raw = Path(self.vacancies_path).read_text(encoding="utf-8")
        payload = json.loads(raw)
        return [Vacancy.from_dict(item) for item in payload]

