from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

# До getenv: один раз подхватываем .env из корня репозитория (не зависит от cwd).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("APP_NAME", "HR Career Assistant")
    app_env: str = getenv("APP_ENV", "dev")
    log_level: str = getenv("LOG_LEVEL", "INFO")

    telegram_bot_token: str = getenv("TELEGRAM_BOT_TOKEN", "")
    llm_api_key: str = getenv("LLM_API_KEY", "")
    llm_model: str = getenv("LLM_MODEL", "Qwen3.5-Flash")
    llm_provider: str = getenv("LLM_PROVIDER", "mock")
    llm_base_url: str = getenv("LLM_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    yandex_cloud_folder_id: str = getenv("YANDEX_CLOUD_FOLDER_ID", "")
    llm_device: str = getenv("LLM_DEVICE", "auto")
    llm_max_new_tokens: int = int(getenv("LLM_MAX_NEW_TOKENS", "384"))
    llm_temperature: float = float(getenv("LLM_TEMPERATURE", "0.2"))

    embedding_model: str = getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )
    embedding_query_model: str = getenv("EMBEDDING_QUERY_MODEL", "text-search-query")
    embedding_provider: str = getenv("EMBEDDING_PROVIDER", "local")
    embedding_api_key: str = getenv("EMBEDDING_API_KEY", "")
    embedding_base_url: str = getenv(
        "EMBEDDING_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    embedding_device: str = getenv("EMBEDDING_DEVICE", "auto")
    sqlite_path: str = getenv("SQLITE_PATH", "data/app.db")
    faiss_index_path: str = getenv("FAISS_INDEX_PATH", "data/faiss/vacancies.index")
    parser_area: str = getenv("PARSER_AREA", "113")
    parser_pages_per_query: int = int(getenv("PARSER_PAGES_PER_QUERY", "5"))
    parser_daily_pages_per_query: int = int(getenv("PARSER_DAILY_PAGES_PER_QUERY", "10"))
    parser_search_period_days: int = int(getenv("PARSER_SEARCH_PERIOD_DAYS", "30"))
    parser_daily_search_period_days: int = int(getenv("PARSER_DAILY_SEARCH_PERIOD_DAYS", "3"))
    parser_delay_seconds: float = float(getenv("PARSER_DELAY_SECONDS", "0.35"))
    parser_max_vacancies: int = int(getenv("PARSER_MAX_VACANCIES", "0"))
    parser_queries_raw: str = getenv("PARSER_QUERIES", "")

    use_mock_llm: bool = getenv("USE_MOCK_LLM", "true").lower() == "true"
    use_mock_embeddings: bool = getenv("USE_MOCK_EMBEDDINGS", "true").lower() == "true"
    preload_models_on_startup: bool = getenv("PRELOAD_MODELS_ON_STARTUP", "true").lower() == "true"
    bot_backend_url: str = getenv("BOT_BACKEND_URL", "http://127.0.0.1:8000")
    bot_backend_timeout_seconds: float = float(getenv("BOT_BACKEND_TIMEOUT_SECONDS", "120"))


settings = Settings()
