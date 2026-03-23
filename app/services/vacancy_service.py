from __future__ import annotations

import json
from typing import Optional

from app.domain.models import Vacancy
from app.storage.db import get_connection


class VacancyService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def load_vacancies(self) -> list[Vacancy]:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vacancies")
            rows = cursor.fetchall()
            mapped_rows = []
            for row in rows:
                payload = dict(row)
                # Domain model expects stable external vacancy id, not DB autoincrement id.
                payload["id"] = payload.get("vacancy_id", payload.get("id"))
                mapped_rows.append(payload)
            return [Vacancy.from_dict(payload) for payload in mapped_rows]

    def save_vacancies(self, vacancies: list[dict]) -> None:
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            for vac in vacancies:
                cursor.execute(
                    "INSERT OR IGNORE INTO vacancies "
                    "(vacancy_id, title, company, location, url, description, "
                    "salary_from, salary_to, posted_date, skills, active_flg) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        vac["id"],
                        vac["title"],
                        vac["company"],
                        vac["location"],
                        vac["url"],
                        vac["description"],
                        vac.get("salary_from"),
                        vac.get("salary_to"),
                        vac["posted_date"],
                        json.dumps(vac.get("skills", []), ensure_ascii=False),
                        vac["active_flg"],
                    ),
                )
            conn.commit()

    def get_vacancy(self, vacancy_id: str) -> Optional[Vacancy]:
        for vac in self.load_vacancies():
            if vac.id == vacancy_id:
                return vac
        return None
