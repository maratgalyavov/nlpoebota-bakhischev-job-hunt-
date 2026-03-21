from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("APP_NAME", "HR Career Assistant")
    app_env: str = getenv("APP_ENV", "dev")
    log_level: str = getenv("LOG_LEVEL", "INFO")

    telegram_bot_token: str = getenv("TELEGRAM_BOT_TOKEN", "")
    llm_api_key: str = getenv("LLM_API_KEY", "")
    llm_model: str = getenv("LLM_MODEL", "Qwen3.5-Flash")

    embedding_model: str = getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    sqlite_path: str = getenv("SQLITE_PATH", "data/app.db")
    faiss_index_path: str = getenv("FAISS_INDEX_PATH", "data/faiss/vacancies.index")
    vacancies_path: str = getenv("VACANCIES_PATH", "data/mock_vacancies.json")

    use_mock_llm: bool = getenv("USE_MOCK_LLM", "true").lower() == "true"
    use_mock_embeddings: bool = getenv("USE_MOCK_EMBEDDINGS", "true").lower() == "true"


settings = Settings()

