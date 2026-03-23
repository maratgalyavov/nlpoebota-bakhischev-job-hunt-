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
USE_MOCK_LLM=false
LLM_PROVIDER=local_hf
LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LLM_DEVICE=auto
USE_MOCK_EMBEDDINGS=false
EMBEDDING_DEVICE=auto
PRELOAD_MODELS_ON_STARTUP=true
```

`PRELOAD_MODELS_ON_STARTUP=true` pre-downloads/loads models on process startup so first bot/API calls are fast.

### 2) Run bot + backend

```bash
docker compose up --build bot backend
```

Services:
- Bot container command: [`python -m app.bot.telegram_app`](docker-compose.yml:11)
- Backend container command: [`python -m uvicorn app.main:app ...`](docker-compose.yml:23)

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
python3 -m pip install -r requirements.txt
python3 scripts/build_index.py
python3 -m uvicorn app.main:app --reload
python3 -m app.bot.telegram_app
```

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
