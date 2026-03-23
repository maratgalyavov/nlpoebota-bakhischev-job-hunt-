from app.services.llm_service import LLMService


def test_llm_generate_returns_contract_and_text_for_resume() -> None:
    service = LLMService()
    service.use_mock = True

    payload = service._generate("profile prompt", mode="resume")
    assert "summary" in payload
    assert "skills" in payload

    text = service.generate_resume("profile text")
    assert "# Резюме" in text


def test_llm_generate_returns_contract_for_gaps() -> None:
    service = LLMService()
    service.use_mock = True

    payload = service._generate("gaps prompt", mode="gaps")
    assert "gaps" in payload
    assert isinstance(payload["gaps"], list)


def test_resume_normalization_keeps_nested_fields() -> None:
    service = LLMService()

    payload = service._normalize_payload(
        {
            "summary": {
                "title": "Резюме",
                "about": "Опытный специалист по автоматизации процессов.",
                "salary_expectation": "300000",
                "location": "Москва",
                "employment": "Полная занятость",
            },
            "experience": [
                {
                    "position": "Тимлид",
                    "duration": "10 лет",
                    "description": "Руководил процессами и командой.",
                }
            ],
            "skills": ["Python", "SQL"],
            "education": [
                {
                    "degree": "Бакалавриат",
                    "field": "Информатика",
                    "institution": "ДГТУ",
                }
            ],
            "projects": [
                {
                    "title": "Карьерный помощник",
                    "description": "Telegram-бот и API на FastAPI.",
                }
            ],
            "additional": ["Эмпатия"],
        },
        mode="resume",
    )

    assert "Опытный специалист" in payload["summary"]
    assert payload["experience"] == ["Тимлид — 10 лет — Руководил процессами и командой."]
    assert payload["education"] == ["Бакалавриат — Информатика — ДГТУ"]
    assert payload["projects"] == ["Карьерный помощник — Telegram-бот и API на FastAPI."]
    assert "300000" in payload["additional"]
    assert "Москва" in payload["additional"]
