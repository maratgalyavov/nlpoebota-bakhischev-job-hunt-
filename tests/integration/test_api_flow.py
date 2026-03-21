from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_interview_to_resume_and_match_flow() -> None:
    app = create_app()
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

