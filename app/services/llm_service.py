from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.domain.prompts import (
    build_cover_letter_prompt,
    build_resume_prompt,
    build_skill_gaps_prompt,
)

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except Exception:  # pragma: no cover - optional runtime dependency behavior
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None

logger = logging.getLogger(__name__)


class ResumeContract(BaseModel):
    summary: str
    experience: list[str]
    skills: list[str]
    education: list[str]
    projects: list[str]
    additional: list[str]


class CoverLetterContract(BaseModel):
    greeting: str
    body: list[str]
    closing: str


class SkillGapItem(BaseModel):
    skill: str
    priority: str
    recommendation: str


class SkillGapsContract(BaseModel):
    gaps: list[SkillGapItem]


class LLMService:
    def __init__(self) -> None:
        self.model_name = settings.llm_model
        self.use_mock = settings.use_mock_llm
        self.provider = settings.llm_provider
        self.device = self._resolve_device()
        self.max_new_tokens = settings.llm_max_new_tokens
        self.temperature = settings.llm_temperature
        self._tokenizer = None
        self._model = None

    def _resolve_device(self) -> str:
        if settings.llm_device != "auto":
            return settings.llm_device
        if torch is not None:
            if torch.backends.mps.is_available():
                return "mps"
            if torch.cuda.is_available():
                return "cuda"
        return "cpu"

    def _ensure_local_model(self) -> bool:
        if self._model is not None and self._tokenizer is not None:
            return True
        if AutoModelForCausalLM is None or AutoTokenizer is None or torch is None:
            logger.warning("Local HF backend unavailable: transformers/torch import failed")
            return False

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            dtype = torch.float16 if self.device in {"mps", "cuda"} else torch.float32
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
            )
            self._model.to(self.device)
            self._model.eval()
            logger.info("Local HF model loaded: model=%s device=%s", self.model_name, self.device)
            return True
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.exception("Failed to load local HF model: %s", exc)
            self._model = None
            self._tokenizer = None
            return False

    def _local_hf_generate(self, prompt: str) -> Optional[str]:
        if not self._ensure_local_model():
            return None
        assert self._tokenizer is not None
        assert self._model is not None
        try:
            messages = [{"role": "user", "content": prompt}]
            input_text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            encoded = self._tokenizer(input_text, return_tensors="pt")
            encoded = {key: value.to(self.device) for key, value in encoded.items()}

            do_sample = self.temperature > 0.0
            with torch.no_grad():
                output = self._model.generate(
                    **encoded,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature if do_sample else None,
                    do_sample=do_sample,
                    pad_token_id=self._tokenizer.eos_token_id,
                )

            prompt_tokens = encoded["input_ids"].shape[1]
            generated_tokens = output[0][prompt_tokens:]
            text = self._tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
            return text or None
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.exception("Local HF generation failed: %s", exc)
            return None

    def _mock_generate_structured(self, mode: str) -> dict[str, Any]:
        if mode == "resume":
            return {
                "summary": "Кандидат мотивирован развиваться и применять опыт на практике.",
                "experience": ["Опыт сформирован на основе ответов интервью."],
                "skills": ["Python", "SQL", "Командная работа"],
                "education": ["Указано пользователем в интервью."],
                "projects": ["Пет-проект: карьерный помощник"],
                "additional": ["Готовность к обучению"],
            }
        if mode == "cover":
            return {
                "greeting": "Здравствуйте!",
                "body": [
                    "Меня заинтересовала ваша вакансия и я хочу предложить свою кандидатуру.",
                    "Мои навыки и опыт соответствуют ключевым требованиям позиции.",
                    "Быстро погружаюсь в задачи и довожу инициативы до результата.",
                ],
                "closing": "Буду рад обсудить, как могу принести пользу вашей команде.",
            }
        return {
            "gaps": [
                {
                    "skill": "Системный дизайн",
                    "priority": "high",
                    "recommendation": "Пройти практический курс и сделать 1-2 архитектурных кейса.",
                },
                {
                    "skill": "CI/CD",
                    "priority": "medium",
                    "recommendation": "Собрать pipeline для pet-проекта и задокументировать шаги.",
                },
            ]
        }

    @staticmethod
    def _extract_json_candidate(raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
        return text

    def _validate_contract(self, payload: dict[str, Any], mode: str) -> dict[str, Any]:
        if mode == "resume":
            return ResumeContract.model_validate(payload).model_dump()
        if mode == "cover":
            return CoverLetterContract.model_validate(payload).model_dump()
        return SkillGapsContract.model_validate(payload).model_dump()

    @staticmethod
    def _render_resume(contract: ResumeContract) -> str:
        sections = [
            "# Резюме",
            "",
            "## О себе",
            contract.summary,
            "",
            "## Опыт",
            *[f"- {item}" for item in contract.experience],
            "",
            "## Навыки",
            ", ".join(contract.skills),
            "",
            "## Образование",
            *[f"- {item}" for item in contract.education],
            "",
            "## Проекты",
            *[f"- {item}" for item in contract.projects],
            "",
            "## Дополнительно",
            *[f"- {item}" for item in contract.additional],
        ]
        return "\n".join(sections)

    @staticmethod
    def _render_cover(contract: CoverLetterContract) -> str:
        return " ".join([contract.greeting, *contract.body, contract.closing]).strip()

    @staticmethod
    def _render_gaps(contract: SkillGapsContract) -> str:
        lines = []
        for idx, item in enumerate(contract.gaps, start=1):
            lines.append(
                f"{idx}) {item.skill} — приоритет: {item.priority}. Рекомендация: {item.recommendation}"
            )
        return "\n".join(lines)

    def _generate(self, prompt: str, mode: str) -> dict[str, Any]:
        schema_hint = (
            "\n\nВерни строго JSON без markdown. "
            "Для resume: {summary, experience[], skills[], education[], projects[], additional[]}. "
            "Для cover: {greeting, body[], closing}. "
            "Для gaps: {gaps:[{skill, priority, recommendation}]}."
        )
        prompt_with_schema = f"{prompt}{schema_hint}"

        if self.use_mock:
            return self._validate_contract(self._mock_generate_structured(mode), mode)

        if self.provider == "local_hf":
            generated = self._local_hf_generate(prompt_with_schema)
            if generated:
                try:
                    parsed = json.loads(self._extract_json_candidate(generated))
                    if isinstance(parsed, dict):
                        return self._validate_contract(parsed, mode)
                    logger.warning("LLM returned non-dict JSON, using mock contract")
                except (json.JSONDecodeError, ValidationError) as exc:
                    logger.warning("LLM JSON schema validation failed: %s", exc)
            logger.warning("Falling back to mock LLM output after local_hf failure")

        # Placeholder for remote provider integration in next iteration.
        return self._validate_contract(self._mock_generate_structured(mode), mode)

    def generate_resume(self, profile_text: str) -> str:
        prompt = build_resume_prompt(profile_text)
        contract = ResumeContract.model_validate(self._generate(prompt, mode="resume"))
        return self._render_resume(contract)

    def generate_cover_letter(self, profile_text: str, vacancy_text: str) -> str:
        prompt = build_cover_letter_prompt(profile_text, vacancy_text)
        contract = CoverLetterContract.model_validate(self._generate(prompt, mode="cover"))
        return self._render_cover(contract)

    def generate_skill_gaps(self, profile_text: str, vacancy_text: str) -> str:
        prompt = build_skill_gaps_prompt(profile_text, vacancy_text)
        contract = SkillGapsContract.model_validate(self._generate(prompt, mode="gaps"))
        return self._render_gaps(contract)
