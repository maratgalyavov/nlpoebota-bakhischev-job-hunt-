# HR Career Assistant (MVP)

Implementation based on [`design_doc.md`](design_doc.md).

## What is implemented

- Telegram bot commands: `/start`, `/a`, `/resume`, `/match`
- FastAPI backend: interview, generation, matching, parser, feedback, health, metrics
- SQLite persistence for users/sessions/answers/artifacts/feedback/vacancies
- FAISS matching with embeddings
- LLM generation with structured contracts and fallback behavior
- Monitoring with Prometheus + Grafana

## Quick start (Docker-first, recommended)

### 1) Prepare env

```bash
cp .env.example .env
```

Set required values in [`.env`](.env):

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
LLM_API_KEY=your_yandex_cloud_api_key
YANDEX_CLOUD_FOLDER_ID=your_folder_id
LLM_PROVIDER=yandex_cloud
LLM_MODEL=qwen2.5-7b-instruct
LLM_BASE_URL=https://llm.api.cloud.yandex.net/v1
EMBEDDING_PROVIDER=yandex_cloud
EMBEDDING_MODEL=text-search-doc
EMBEDDING_QUERY_MODEL=text-search-query
EMBEDDING_BASE_URL=https://llm.api.cloud.yandex.net/v1
PRELOAD_MODELS_ON_STARTUP=false
```

This Docker setup is now compatible with Yandex Cloud AI Studio, so the containers do not need to load
local Qwen or sentence-transformers weights at startup. That keeps memory much lower and is the safest
way to avoid Docker exits with code `137` on your Mac.

For open-source Qwen models in Yandex AI Studio, the app now uses Yandex's OpenAI-compatible endpoints
(`chat/completions` and `embeddings`) instead of the older specialized completion endpoint, because some
models are exposed only through the OpenAI-compatible API.

### 2) Run bot + backend

```bash
docker compose up --build bot backend
```

Services:
- Bot container command: [`python -m app.bot.telegram_app`](docker-compose.yml:11)
- Backend container command: [`python -m uvicorn app.main:app ...`](docker-compose.yml:29)
- Bot backend URL: `BOT_BACKEND_URL=http://backend:8000` inside Docker

### 3) Optional monitoring stack

```bash
docker compose up --build bot backend prometheus grafana
```

Endpoints:
- API: `http://127.0.0.1:8000`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000` (`admin/admin`)
- Metrics endpoint: [`/metrics`](app/observability/metrics.py:24)
- Dashboard file: [`monitoring/grafana/dashboards/hr-assistant-overview.json`](monitoring/grafana/dashboards/hr-assistant-overview.json)

### 4) Logs and control

```bash
docker compose logs -f bot
docker compose logs -f backend
docker compose down
```

## Python local run (secondary)

Use this if you explicitly need local non-Docker execution.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/build_index.py
python3 -m uvicorn app.main:app --reload
python3 -m app.bot.telegram_app
```

For local two-process runs on Apple Silicon, use:

```bash
BOT_BACKEND_URL=http://127.0.0.1:8000
LLM_PROVIDER=local_hf
LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LLM_DEVICE=mps
EMBEDDING_DEVICE=mps
LLM_MAX_NEW_TOKENS=512
LLM_TEMPERATURE=0.15
PRELOAD_MODELS_ON_STARTUP=false
```

## macOS Native Auto-Restart

If you want both services to run without Docker and restart automatically after crashes or login,
use the included `launchd` helpers:

```bash
cd /Users/maratgalavov/nlpoebota-bakhischev-job-hunt-
./scripts/local_services.sh install
./scripts/local_services.sh status
```

This renders and installs:
- [`launchd/com.hr.backend.plist.template`](launchd/com.hr.backend.plist.template)
- [`launchd/com.hr.bot.plist.template`](launchd/com.hr.bot.plist.template)

Useful commands:

```bash
./scripts/local_services.sh start
./scripts/local_services.sh stop
./scripts/local_services.sh restart
./scripts/local_services.sh status
./scripts/local_services.sh logs
```

Logs are written to `logs/backend.out.log`, `logs/backend.err.log`, `logs/bot.out.log`, and `logs/bot.err.log`.

## Model Tuning

For Docker with Yandex Cloud AI Studio, start with:

```bash
LLM_PROVIDER=yandex_cloud
LLM_MODEL=qwen2.5-7b-instruct
EMBEDDING_PROVIDER=yandex_cloud
EMBEDDING_MODEL=text-search-doc
EMBEDDING_QUERY_MODEL=text-search-query
PRELOAD_MODELS_ON_STARTUP=false
```

If you want a stronger text model, replace `LLM_MODEL` with a full URI or model ID from your Yandex AI
Studio catalog, for example:

```bash
LLM_MODEL=qwen2.5-32b-instruct
```

or

```bash
LLM_MODEL=gpt://<folder_id>/qwen2.5-72b-instruct
```

If you want native local inference instead of the API, the easiest step up from `Qwen/Qwen2.5-0.5B-Instruct` is:

```bash
LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LLM_PROVIDER=local_hf
LLM_DEVICE=mps
EMBEDDING_DEVICE=mps
LLM_MAX_NEW_TOKENS=512
LLM_TEMPERATURE=0.15
PRELOAD_MODELS_ON_STARTUP=false
```

If your Mac still feels comfortable on RAM, try:

```bash
LLM_MODEL=Qwen/Qwen2.5-3B-Instruct
LLM_MAX_NEW_TOKENS=512
LLM_TEMPERATURE=0.1
```

Why these recommendations:
- Yandex AI Studio exposes the Qwen family through model URIs like `gpt://<folder_id>/qwen2.5-7b-instruct`, `qwen2.5-32b-instruct`, and `qwen2.5-72b-instruct`.
- Yandex AI Studio also provides dedicated embedding models `emb://<folder_id>/text-search-doc/latest` and `emb://<folder_id>/text-search-query/latest`, which fit this project’s vacancy-index plus query-search flow better than a single generic embedding model.

## API examples

```bash
curl -X POST http://127.0.0.1:8000/v1/interview/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "telegram_username": "demo"}'
```

```bash
curl -X POST http://127.0.0.1:8000/v1/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "answer_text": "Мой ответ"}'
```

```bash
curl -X POST http://127.0.0.1:8000/v1/generate/resume \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1}'
```

```bash
curl -X POST http://127.0.0.1:8000/v1/match/vacancies \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "top_k": 5}'
```

Matching response includes explainability fields from [`/v1/match/vacancies`](app/api/routes_matching.py:45):
- `matched_skills`
- `reasons`
- `missing_skills_preview`
- `salary_from`
- `salary_to`
- `description_preview`

## HH parser integration

Components:
- Parser core: [`app/storage/hh_parser.py`](app/storage/hh_parser.py)
- Service: [`ParserService`](app/services/parser_service.py:20)
- Persistence: [`VacancyService.save_vacancies()`](app/services/vacancy_service.py:26)
- API routes:
  - [`POST /v1/parser/run`](app/api/routes_parser.py:11)
  - [`POST /v1/parser/daily-update`](app/api/routes_parser.py:16)

Run parser manually:

```bash
curl -X POST http://127.0.0.1:8000/v1/parser/run
curl -X POST http://127.0.0.1:8000/v1/parser/daily-update
```

Parser coverage is configurable via [`.env.example`](.env.example). The most important knobs are:
- `PARSER_PAGES_PER_QUERY`
- `PARSER_SEARCH_PERIOD_DAYS`
- `PARSER_DAILY_PAGES_PER_QUERY`
- `PARSER_DAILY_SEARCH_PERIOD_DAYS`
- `PARSER_QUERIES`

The default parser setup now:
- searches more role variants in both Russian and English
- loads up to 100 vacancies per search page
- scans multiple pages per query instead of only one
- refreshes existing vacancies on conflict instead of silently skipping updates

Then rebuild index:

```bash
python3 scripts/build_index.py
```

## Quality checks

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m mypy app
```

CI workflow: [`CI`](.github/workflows/ci.yml:1).

## Notes

- Runtime configuration lives in [`.env`](.env) and [`.env.example`](.env.example).
- App settings are read in [`Settings`](app/core/config.py:14).
- Dependency wiring and startup warmup are in [`build_container()`](app/api/deps.py:38).
