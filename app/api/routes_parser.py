from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import container

router = APIRouter(prefix="/v1/parser", tags=["parser"])


@router.post("/run")
def run_parser() -> dict:
    return container.parser_service.run_parser()


@router.post("/daily-update")
def daily_update() -> dict:
    container.parser_service.daily_update()
    return {
        "status": "success",
        "message": "Daily update completed",
        "vacancies_total": len(container.vacancy_service.load_vacancies()),
    }

