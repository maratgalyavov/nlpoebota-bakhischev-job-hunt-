from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.errors import ExternalServiceError
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
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.folder_id = settings.yandex_cloud_folder_id
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

    def warmup(self) -> None:
        if self.use_mock:
            return
        if self.provider == "local_hf":
            self._ensure_local_model()

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

    def _model_studio_generate(self, prompt: str) -> Optional[str]:
        if not self.api_key:
            raise ExternalServiceError("Model Studio LLM is not configured: LLM_API_KEY is empty.")

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - runtime dependent
            detail = exc.response.text.strip()
            logger.error(
                "Model Studio generation failed: status=%s body=%s",
                exc.response.status_code,
                detail[:1000],
            )
            raise ExternalServiceError(
                f"Model Studio LLM request failed with HTTP {exc.response.status_code}. "
                "Check API key, region/base URL, and workspace permissions."
            ) from exc
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.exception("Model Studio generation failed: %s", exc)
            raise ExternalServiceError("Model Studio LLM request failed.") from exc

        try:
            choices = body.get("choices") or []
            message = choices[0].get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content.strip() or None
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text")
                        if isinstance(text, str) and text.strip():
                            text_parts.append(text.strip())
                joined = "\n".join(text_parts).strip()
                return joined or None
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.warning("Unexpected Model Studio response format: %s", exc)
        raise ExternalServiceError("Model Studio LLM returned an unexpected response format.")

    def _resolve_yandex_model_uri(self) -> str:
        if self.model_name.startswith("gpt://"):
            return self.model_name
        if not self.folder_id:
            raise ExternalServiceError(
                "Yandex Cloud LLM is not configured: YANDEX_CLOUD_FOLDER_ID is empty."
            )
        return f"gpt://{self.folder_id}/{self.model_name}"

    def _yandex_cloud_generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ExternalServiceError("Yandex Cloud LLM is not configured: LLM_API_KEY is empty.")

        payload = {
            "model": self._resolve_yandex_model_uri(),
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "OpenAI-Project": self.folder_id,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            body = response.json()
            logger.info("Yandex Cloud raw response preview: %s", json.dumps(body, ensure_ascii=False)[:2000])
        except httpx.HTTPStatusError as exc:  # pragma: no cover - runtime dependent
            detail = exc.response.text.strip()
            logger.error(
                "Yandex Cloud generation failed: status=%s body=%s",
                exc.response.status_code,
                detail[:1000],
            )
            raise ExternalServiceError(
                f"Yandex Cloud LLM request failed with HTTP {exc.response.status_code}. "
                "Check API key scope, folder ID, and model URI."
            ) from exc
        except Exception as exc:  # pragma: no cover - runtime dependent
            logger.exception("Yandex Cloud generation failed: %s", exc)
            raise ExternalServiceError("Yandex Cloud LLM request failed.") from exc

        try:
            choices = body.get("choices") or []
            choice = choices[0] if choices else {}
            message = choice.get("message") or {}
            text = message.get("content")
            if isinstance(text, str) and text.strip():
                return text.strip()
            if isinstance(text, list):
                text_parts = []
                for item in text:
                    if isinstance(item, dict):
                        candidate = item.get("text") or item.get("content")
                        if isinstance(candidate, str) and candidate.strip():
                            text_parts.append(candidate.strip())
                    elif isinstance(item, str) and item.strip():
                        text_parts.append(item.strip())
                joined = "\n".join(text_parts).strip()
                if joined:
                    return joined
            reasoning_text = message.get("reasoning_content")
            if isinstance(reasoning_text, str) and reasoning_text.strip():
                finish_reason = choice.get("finish_reason")
                if finish_reason == "length":
                    raise ExternalServiceError(
                        "Yandex Cloud response was truncated by max_tokens. "
                        "Increase LLM_MAX_NEW_TOKENS or switch to a less verbose model."
                    )
                return reasoning_text.strip()
        except Exception as exc:  # pragma: no cover - runtime dependent
            if isinstance(exc, ExternalServiceError):
                raise
            logger.warning("Unexpected Yandex Cloud response format: %s", exc)
        raise ExternalServiceError("Yandex Cloud LLM returned an unexpected response format.")

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

    @staticmethod
    def _to_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            parts = [LLMService._to_text(item) for item in value]
            parts = [p for p in parts if p]
            return "; ".join(parts)
        if isinstance(value, dict):
            preferred_order = [
                "about",
                "summary",
                "title",
                "position",
                "role",
                "degree",
                "company",
                "organization",
                "field",
                "specialization",
                "institution",
                "school_name",
                "duration",
                "period",
                "dates",
                "salary_expectation",
                "salary",
                "location",
                "employment",
                "description",
                "result",
                "details",
            ]
            parts = []
            for key in preferred_order:
                if key in value:
                    text = LLMService._to_text(value.get(key))
                    if text:
                        parts.append(text)
            if not parts:
                for raw in value.values():
                    text = LLMService._to_text(raw)
                    if text:
                        parts.append(text)
            return " — ".join(parts)
        return str(value)

    @staticmethod
    def _normalize_text_list(raw: Any) -> list[str]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raw = [raw]
        result: list[str] = []
        for item in raw:
            text = LLMService._to_text(item).strip()
            if text:
                result.append(text)
        return result

    def _normalize_payload(self, payload: dict[str, Any], mode: str) -> dict[str, Any]:
        normalized = dict(payload)
        if mode == "resume":
            summary = normalized.get("summary")
            normalized["summary"] = self._to_text(summary)

            if isinstance(summary, dict):
                extra_parts = []
                for key in ("salary_expectation", "salary", "location", "employment"):
                    text = self._to_text(summary.get(key))
                    if text:
                        extra_parts.append(text)
                if extra_parts:
                    existing_additional = self._normalize_text_list(normalized.get("additional"))
                    normalized["additional"] = [*existing_additional, *extra_parts]

            for field in ("experience", "skills", "education", "projects", "additional"):
                normalized[field] = self._normalize_text_list(normalized.get(field))
            return normalized
        if mode == "cover":
            normalized["greeting"] = self._to_text(normalized.get("greeting"))
            normalized["body"] = self._normalize_text_list(normalized.get("body"))
            normalized["closing"] = self._to_text(normalized.get("closing"))
            return normalized
        if mode == "gaps":
            gaps = normalized.get("gaps")
            if not isinstance(gaps, list):
                gaps = [gaps] if gaps else []
            normalized_gaps = []
            for item in gaps:
                if isinstance(item, dict):
                    normalized_gaps.append(
                        {
                            "skill": self._to_text(item.get("skill") or item.get("name")),
                            "priority": self._to_text(item.get("priority") or item.get("level")),
                            "recommendation": self._to_text(
                                item.get("recommendation") or item.get("action")
                            ),
                        }
                    )
                else:
                    text = self._to_text(item)
                    normalized_gaps.append(
                        {
                            "skill": text,
                            "priority": "medium",
                            "recommendation": "Уточнить план развития по этому навыку.",
                        }
                    )
            normalized["gaps"] = normalized_gaps
            return normalized
        return normalized

    def _validate_contract(self, payload: dict[str, Any], mode: str) -> dict[str, Any]:
        payload = self._normalize_payload(payload, mode)
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

        if self.provider == "model_studio":
            generated = self._model_studio_generate(prompt_with_schema)
            try:
                parsed = json.loads(self._extract_json_candidate(generated))
                if isinstance(parsed, dict):
                    return self._validate_contract(parsed, mode)
                raise ExternalServiceError("Model Studio returned non-dict JSON.")
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ExternalServiceError(
                    "Model Studio returned a response that did not match the expected JSON schema."
                ) from exc

        if self.provider == "yandex_cloud":
            generated = self._yandex_cloud_generate(prompt_with_schema)
            try:
                parsed = json.loads(self._extract_json_candidate(generated))
                if isinstance(parsed, dict):
                    return self._validate_contract(parsed, mode)
                raise ExternalServiceError("Yandex Cloud returned non-dict JSON.")
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.error(
                    "Yandex Cloud JSON/schema parse failed. Raw response preview: %s",
                    generated[:2000],
                )
                raise ExternalServiceError(
                    "Yandex Cloud returned a response that did not match the expected JSON schema."
                ) from exc

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
