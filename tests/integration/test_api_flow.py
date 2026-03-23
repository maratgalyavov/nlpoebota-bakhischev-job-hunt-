from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

import app.api.deps as deps_module
import app.api.routes_generation as routes_generation_module
import app.api.routes_interview as routes_interview_module
import app.api.routes_matching as routes_matching_module
import app.core.config as config_module
import app.main as main_module
import app.services.embedding_service as embedding_service_module
import app.services.llm_service as llm_service_module
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService


def test_interview_to_resume_and_match_flow(monkeypatch) -> None:
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK_EMBEDDINGS", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    importlib.reload(config_module)
    importlib.reload(llm_service_module)
    importlib.reload(embedding_service_module)
    importlib.reload(deps_module)
    importlib.reload(routes_interview_module)
    importlib.reload(routes_generation_module)
    importlib.reload(routes_matching_module)
    importlib.reload(main_module)
    deps_module.container.llm_service = LLMService()
    deps_module.container.llm_service.use_mock = True
    deps_module.container.embedding_service = EmbeddingService()
    deps_module.container.embedding_service._provider = "mock"
    deps_module.container.matching_service.embedding_service = deps_module.container.embedding_service
    app = main_module.create_app()
    client = TestClient(app)

    start = client.post(
        "/v1/interview/start",
        json={"user_id": 1001, "telegram_username": "tester"},
    )
    assert start.status_code == 200

    answers = [
        "2 года backend разработки",
        "Python, FastAPI, SQL",
        "ВШЭ",
        "Прикладная информатика",
        "Пет-проект: карьерный помощник на FastAPI и Telegram Bot",
        "Backend Developer",
        "200000",
        "Remote",
        "Полная",
        "Ответственность",
    ]
    for answer in answers:
        response = client.post("/v1/interview/answer", json={"user_id": 1001, "answer_text": answer})
        assert response.status_code == 200

    resume = client.post("/v1/generate/resume", json={"user_id": 1001})
    assert resume.status_code == 200
    assert "resume" in resume.json()

    matched = client.post("/v1/match/vacancies", json={"user_id": 1001, "top_k": 3})
    assert matched.status_code == 200
    assert "items" in matched.json()
    items = matched.json()["items"]
    assert len(items) > 0
    assert "explainability" in items[0]
    assert "reasons" in items[0]["explainability"]


def test_metrics_endpoint_exposes_prometheus_payload() -> None:
    app = main_module.create_app()
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "hr_assistant_http_requests_total" in response.text
