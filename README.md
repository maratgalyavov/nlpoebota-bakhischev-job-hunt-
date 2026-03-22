# HR Career Assistant (MVP)

Implementation based on [`design_doc.md`](design_doc.md) and backend-first plan in [`plans/mvp_implementation_plan.md`](plans/mvp_implementation_plan.md).

## What is implemented

- FastAPI backend with interview, generation, matching, feedback, and health routes
- SQLite persistence for users, sessions, interview answers, artifacts, and feedback
- Mock LLM generation service (resume / cover letter / skill gaps)
- Embedding service with deterministic mock mode and FAISS-based matching
- Mock vacancies dataset and index build script
- Telegram bot handlers for `/start`, `/a`, `/resume`, `/match`
- Unit + integration tests

## Quick start (local)

1. Create env file:

```bash
cp .env.example .env
```

2. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

3. Run tests:

```bash
python3 -m pytest -q
```

4. Build FAISS index from mock vacancies:

```bash
python3 scripts/build_index.py
```

5. Start API:

```bash
python3 -m uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

## API examples

Start interview:

```bash
curl -X POST http://127.0.0.1:8000/v1/interview/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "telegram_username": "demo"}'
```

Answer question:

```bash
curl -X POST http://127.0.0.1:8000/v1/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "answer_text": "Мой ответ"}'
```

Generate resume:

```bash
curl -X POST http://127.0.0.1:8000/v1/generate/resume \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1}'
```

Match vacancies:

```bash
curl -X POST http://127.0.0.1:8000/v1/match/vacancies \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "top_k": 5}'
```

Response now includes explainability per vacancy (`matched_skills`, `reasons`, `missing_skills_preview`) from [`/v1/match/vacancies`](app/api/routes_matching.py:45).

## Docker

```bash
cp .env.example .env
docker compose up --build
```

API: `http://127.0.0.1:8000`

Monitoring stack:
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000` (admin/admin)
- Dashboard file: [`monitoring/grafana/dashboards/hr-assistant-overview.json`](monitoring/grafana/dashboards/hr-assistant-overview.json)

## Notes

- Current environment uses Python 3.9; code and type hints were adapted for compatibility.
- For real production-like LLM and embeddings, disable mock flags in [`.env.example`](.env.example) and integrate actual providers in [`app/services/llm_service.py`](app/services/llm_service.py) and [`app/services/embedding_service.py`](app/services/embedding_service.py).

## Run a small local Qwen on Apple Silicon (MPS)

The app now supports a local HuggingFace backend in [`LLMService._local_hf_generate()`](app/services/llm_service.py:67).

Recommended models:
- For 16GB RAM device: `Qwen/Qwen2.5-0.5B-Instruct`
- For 48GB RAM device: `Qwen/Qwen2.5-1.5B-Instruct` (you can also try `Qwen/Qwen2.5-3B-Instruct`)

Set these values in [`.env`](.env):

```bash
USE_MOCK_LLM=false
LLM_PROVIDER=local_hf
LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LLM_DEVICE=auto
LLM_MAX_NEW_TOKENS=384
LLM_TEMPERATURE=0.2
```

Then run API normally:

```bash
python3 -m uvicorn app.main:app --reload
```

Behavior details:
- Device auto-detection is in [`LLMService._resolve_device()`](app/services/llm_service.py:30) and prefers MPS on macOS.
- If local model load/generation fails, app falls back to mock output in [`LLMService._generate()`](app/services/llm_service.py:196).

## LLM structured output contracts

LLM responses are validated against internal JSON contracts in [`LLMService._validate_contract()`](app/services/llm_service.py:129):
- [`ResumeContract`](app/services/llm_service.py:25)
- [`CoverLetterContract`](app/services/llm_service.py:34)
- [`SkillGapsContract`](app/services/llm_service.py:46)

This keeps generation deterministic and parse-safe even for local models.
