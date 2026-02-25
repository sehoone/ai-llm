# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM orchestration service built with FastAPI + LangGraph + Langfuse. Multi-bot RAG system with isolated knowledge bases, long-term memory (mem0ai), and comprehensive observability.

**Stack:** Python 3.13+, FastAPI, LangGraph, PostgreSQL + pgvector, OpenAI, Langfuse

## Common Commands

### Development (Linux/macOS)
```bash
make install              # Install dependencies (uv sync)
make dev                  # Run dev server with reload (port 8000)
make lint                 # Run ruff linter
make format               # Run ruff formatter
```

### Development (Windows PowerShell)
```powershell
uv sync                                                          # Install dependencies
$env:APP_ENV='development'; uv run uvicorn src.main:app --reload --port 8000  # Run dev server
ruff check .                                                     # Lint
ruff format .                                                    # Format
```

### Testing
```bash
pytest                    # Run all tests
pytest -m "not slow"      # Skip slow tests
pytest -v path/to/test.py # Run specific test file
```

### Docker
```bash
make docker-compose-up ENV=development   # Start full stack (API:8061, DB, Prometheus:8063, Grafana:8064)
make docker-compose-down ENV=development # Stop stack
```

### Model Evaluation
```bash
make eval                 # Interactive evaluation mode
make eval-quick           # Quick evaluation with defaults
```

## Architecture

```
src/
├── main.py                 # FastAPI app entry point (middleware, lifespan, health)
├── common/                 # Shared infrastructure
│   ├── config.py           # Environment config (auto-loads .env.{APP_ENV})
│   ├── logging.py          # structlog setup with context binding
│   ├── metrics.py          # Prometheus metrics
│   ├── middleware.py       # Logging, metrics, CORS, rate-limit middleware
│   ├── services/
│   │   ├── database.py     # SQLModel ORM + connection pooling
│   │   ├── llm.py          # LLMRegistry + LLMService with retry/fallback
│   │   ├── graph.py        # Message processing utilities (dump/prepare/process)
│   │   └── sanitization.py # Input sanitization
│   ├── schemas/graph.py    # GraphState definition (LangGraph state type)
│   ├── prompts/            # System prompt templates
│   └── langgraph/
│       ├── graph.py        # LangGraphAgent — main orchestration class
│       └── tools/          # Tool registry (duckduckgo_search)
├── auth/                   # JWT auth + API key management
├── chatbot/                # Chat endpoints, sessions, threads, custom GPTs
├── rag/                    # Multi-bot RAG system (upload, chunking, embeddings, search)
├── user/                   # User management
├── llm_resources/          # Per-user LLM model config
└── voice_evaluation/       # Azure Speech STT/TTS + proficiency evaluation
```

**Layer pattern per module:** `api/` (routers) → `services/` (business logic) → `models/` (SQLModel DB models) → `schemas/` (Pydantic)

**Adding an endpoint:** Create in `src/{module}/api/`, register in `src/common/api/api.py`.

## Key Components

### LangGraph Agent (`src/common/langgraph/graph.py`)

Stateful two-node workflow: `_chat` → `_tool_call` (if tool calls detected) → back to `_chat` → `END`. State persisted as PostgreSQL checkpoints per `thread_id`.

- `get_response()` / `stream_response()` — main entry points
- Long-term memory injected into system prompt via mem0ai semantic search
- After each turn, conversation is summarized and stored back to mem0

### LLM Service (`src/common/services/llm.py`)

`LLMRegistry` maintains instances of all models. `LLMService` wraps calls with tenacity retry (3 attempts, exponential backoff) and circular fallback across the registry. Default model: `gpt-5-mini` (reasoning=low). Fallback chain: `gpt-5-mini → gpt-5 → gpt-4o → gpt-4o-mini`.

Message processing helpers in `src/common/services/graph.py`:
- `dump_messages()` — normalizes Message/BaseMessage/dict to OpenAI wire format, handles multimodal (images → base64 vision)
- `process_llm_response()` — strips reasoning/thinking blocks from GPT-5 structured content responses

### RAG System (`src/rag/`)

Each chatbot has an isolated knowledge base identified by `rag_key`. Documents are chunked (500 chars, 100 overlap) → OpenAI embeddings (`text-embedding-3-small`, 1536-dim) → stored in `rag_embedding` table (pgvector).

- `rag_type`: `"user_isolated"` (per-user) or `"chatbot_shared"` (shared across users)
- `rag_group`: groups multiple RAG keys for batch retrieval
- Search returns top-k similar chunks via pgvector cosine similarity

### Custom GPTs (`src/chatbot/`)

Users can create custom bots with their own system instructions, model selection, and `rag_key`. Separate session/message tables (`gpt_session`, `gpt_chat_message`) track custom GPT conversations independently.

### Long-term Memory

mem0ai with pgvector backend. User-scoped semantic memory stored in `LONG_TERM_MEMORY_COLLECTION_NAME` collection. Multimodal content (images) is filtered before storing to ensure compatibility.

### Observability

- **Logging:** structlog — JSON in production, colored console in development. Always use kwargs, not f-strings: `logger.info("event", key=value)`
- **Metrics:** Prometheus on `:8063`, Grafana on `:8064`, cAdvisor on `:8065`
- **LLM Tracing:** Langfuse (optional, controlled by `LANGFUSE_ENABLED`)

## Environment Configuration

- `APP_ENV` controls which `.env.{environment}` file loads
- Priority: `.env.{env}.local` > `.env.{env}` > `.env.local` > `.env`
- Valid environments: `development`, `staging`, `production`, `test`
- Config is accessed via `from src.common.config import settings`

Key settings groups: OpenAI (API key, models, TTS/STT), PostgreSQL (`POSTGRES_SCHEMA=llmonl`, pool size), JWT (10 min access, 7 day refresh), rate limits, Langfuse, Azure Speech.

## Database

PostgreSQL with pgvector extension. `POSTGRES_SCHEMA=llmonl`. Tables auto-created by SQLModel ORM at startup. Manual reference: `schema.sql`.

Connection pool: `QueuePool`, `pool_pre_ping=True`, `pool_recycle=1800`. Environment-specific pool sizes set in `apply_environment_settings()`.

## Code Style

- Line length: 119
- Formatter: ruff (black-compatible)
- Docstrings: Google convention
- Logging: structlog with context binding, pass variables as kwargs (no f-strings in log calls)
