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

