from __future__ import annotations

import logging
from typing import Optional

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

    def _mock_generate(self, prompt: str, mode: str) -> str:
        if mode == "resume":
            return (
                "# Резюме\n\n"
                "## О себе\nКандидат мотивирован развиваться и применять опыт на практике.\n\n"
                "## Опыт\nОпыт сформирован на основе ответов интервью.\n\n"
                "## Навыки\nКлючевые технические и soft skills из профиля пользователя.\n\n"
                "## Образование\nУказано пользователем в интервью."
            )
        if mode == "cover":
            return (
                "Здравствуйте! Меня заинтересовала ваша вакансия. "
                "Мой опыт и навыки соответствуют ключевым требованиям позиции. "
                "Умею быстро погружаться в задачи, работать в команде и брать ответственность за результат. "
                "Буду рад обсудить, как могу принести пользу вашей команде."
            )
        return (
            "1) Недостающие навыки: уточнить стек вакансии и углубить профильные знания.\n"
            "2) Приоритет: высокий.\n"
            "3) План: пройти профильный курс, сделать проект, добавить кейсы в резюме."
        )

    def _generate(self, prompt: str, mode: str) -> str:
        if self.use_mock:
            return self._mock_generate(prompt, mode)

        if self.provider == "local_hf":
            generated = self._local_hf_generate(prompt)
            if generated:
                return generated
            logger.warning("Falling back to mock LLM output after local_hf failure")

        # Placeholder for remote provider integration in next iteration.
        return self._mock_generate(prompt, mode)

    def generate_resume(self, profile_text: str) -> str:
        prompt = build_resume_prompt(profile_text)
        return self._generate(prompt, mode="resume")

    def generate_cover_letter(self, profile_text: str, vacancy_text: str) -> str:
        prompt = build_cover_letter_prompt(profile_text, vacancy_text)
        return self._generate(prompt, mode="cover")

    def generate_skill_gaps(self, profile_text: str, vacancy_text: str) -> str:
        prompt = build_skill_gaps_prompt(profile_text, vacancy_text)
        return self._generate(prompt, mode="gaps")
