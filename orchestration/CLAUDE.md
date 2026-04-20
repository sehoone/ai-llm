# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM orchestration service built with FastAPI + LangGraph + Langfuse. Multi-bot RAG system with isolated knowledge bases, long-term memory (mem0ai), workflow engine, and comprehensive observability.

**Stack:** Python 3.13+, FastAPI, LangGraph, PostgreSQL + pgvector, OpenAI, Langfuse, APScheduler

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
make docker-compose-up ENV=development   # Start full stack (API:8000, DB, Prometheus:8063, Grafana:8064, cAdvisor:8065)
make docker-compose-down ENV=development # Stop stack
```

### Model Evaluation
```bash
make eval                 # Interactive evaluation mode
make eval-quick           # Quick evaluation with defaults
make eval-no-report       # Evaluation without report generation
```

## Architecture

```
src/
├── main.py                 # FastAPI app entry point (middleware, lifespan, health)
├── common/                 # Shared infrastructure
│   ├── config.py           # Environment config (auto-loads .env.{APP_ENV})
│   ├── logging.py          # structlog setup with context binding
│   ├── metrics.py          # Prometheus metrics
│   ├── middleware.py       # RequestID, Logging, Metrics, CORS middleware
│   ├── limiter.py          # slowapi rate limiter
│   ├── services/
│   │   ├── database.py     # SQLModel ORM + connection pooling
│   │   ├── llm.py          # LLMRegistry + LLMService with retry/fallback
│   │   ├── graph.py        # Message processing utilities (dump/prepare/process)
│   │   └── sanitization.py # Input sanitization
│   ├── schemas/graph.py    # GraphState definition (LangGraph state type)
│   ├── prompts/            # System prompt templates
│   └── langgraph/
│       ├── graph.py        # LangGraphAgent — main orchestration class
│       ├── _nodes.py       # Node implementations (_chat, _tool_call, _think, _verify)
│       ├── _memory.py      # Long-term memory mixin
│       └── tools/          # Tool registry (duckduckgo_search)
├── agent/                  # Configurable chatbot agents (model, RAG, tools per bot)
├── auth/                   # JWT auth + API key management
├── chatbot/                # Chat endpoints, sessions, threads, custom GPTs, attachments
├── llm_resources/          # Per-user LLM model config
├── rag/                    # Multi-bot RAG system (upload, chunking, embeddings, search)
├── user/                   # User management
├── voice_evaluation/       # Azure Speech STT/TTS + proficiency evaluation
└── workflow/               # Low-code DAG workflow engine (scheduling, webhooks, SSE)
```

**Layer pattern per module:** `api/` (routers) → `services/` (business logic) → `models/` (SQLModel DB models) → `schemas/` (Pydantic)

**Adding an endpoint:** Create in `src/{module}/api/`, register in `src/common/api/api.py`.

## Key Components

### LangGraph Agent (`src/common/langgraph/graph.py`, `_nodes.py`)

Graph nodes and flow:
```
START → [_think →] _chat → [_tool_call →] _chat → [_verify →] _chat → END
```

- `_chat` — main LLM node; routes to `_tool_call` (tool calls), `_verify` (deep thinking), or END
- `_think` — strategy planning node (deep thinking mode only, not user-facing)
- `_tool_call` — executes tools, returns to `_chat`
- `_verify` — quality evaluator; approves (→ END) or provides retry feedback (→ `_chat`, max 2 iterations)

State persisted as PostgreSQL checkpoints per `thread_id` via `AsyncPostgresSaver`. Fallback: production continues without checkpointer on DB failure; other envs raise.

Entry points: `get_response()` / `get_stream_response()`. Stream yields per-token output with section headers for think/verify nodes.

### LLM Service (`src/common/services/llm.py`)

`LLMRegistry` maintains instances of all models. `LLMService` wraps with tenacity retry (3 attempts, exponential backoff) and circular fallback.

- Default model: `gpt-5-mini` (reasoning=low)
- Fallback chain: `gpt-5-mini → gpt-5 → gpt-4o → gpt-4o-mini`
- `dump_messages()` — normalizes Message/BaseMessage/dict to OpenAI wire format, handles multimodal (images → base64 vision)
- `process_llm_response()` — strips reasoning/thinking blocks from GPT-5 structured content responses

### RAG System (`src/rag/`)

Each chatbot has an isolated knowledge base identified by `rag_key`. Upload → chunk (500 chars, 100 overlap) → embed (`text-embedding-3-small`, 1536-dim) → store in `rag_embedding` (pgvector cosine similarity).

- `rag_type`: `"user_isolated"` (per-user) or `"chatbot_shared"` (shared)
- `rag_group`: groups multiple `rag_key`s for batch retrieval across knowledge bases

### Agent System (`src/agent/`)

Configurable chatbots distinct from the default chatbot. Each agent stores: model selection, `rag_keys[]`, `rag_groups[]`, `tools_enabled[]`, system instructions, published state. Sessions tracked in `agent_session` table separately from `gpt_session`.

### Workflow Engine (`src/workflow/`)

Low-code DAG runner with:
- **Execution:** Topological sort + parallel node execution (`asyncio.gather`) with SSE streaming (NodeStart, NodeComplete, ExecutionComplete events)
- **Node types:** Code (Python), Condition (branching), HTTP, Chat (LangGraph integration) — extensible registry in `executor/registry.py`
- **Scheduling:** APScheduler with CronTrigger; loads all active schedules from DB at startup
- **Webhooks:** POST `/webhooks/{webhook_token}` → triggers execution with request body as input
- **Dynamic endpoints:** Workflows bind to custom paths via POST `/api/v1/run/{path}`

### Long-term Memory

mem0ai with pgvector backend. User-scoped semantic memory. Retrieved before graph invocation (`_get_relevant_memory()`), injected into system prompt, updated async after each turn (`_update_long_term_memory()`). Images filtered before storing.

### Observability

- **Logging:** structlog — JSON in production, colored console in development. Always use kwargs: `logger.info("event", key=value)` (no f-strings)
- **Metrics:** Prometheus on `:8063`, Grafana on `:8064`, cAdvisor on `:8065`
- **LLM Tracing:** Langfuse (optional, `LANGFUSE_ENABLED`), callbacks injected via `_get_langfuse_callbacks()`

## Environment Configuration

- `APP_ENV` controls which `.env.{environment}` file loads
- Priority: `.env.{env}.local` > `.env.{env}` > `.env.local` > `.env`
- Valid environments: `development`, `staging`, `production`, `test`
- Config accessed via `from src.common.config import settings`

Key settings groups: OpenAI (API key, models, TTS/STT), PostgreSQL (`POSTGRES_SCHEMA=llmonl`, pool 20/overflow 10), JWT (10 min access, 7 day refresh, HS256), rate limits, Langfuse, Azure Speech, mem0ai (model: gpt-4o-mini, embedder: text-embedding-3-small).

## Database

PostgreSQL with pgvector. `POSTGRES_SCHEMA=llmonl`. Tables auto-created by SQLModel ORM at startup. Manual reference: `schema.sql`.

Connection pool: `QueuePool`, `pool_pre_ping=True`, `pool_recycle=1800`.

Key tables: `users`, `session`, `agent`, `agent_session`, `gpt_session`, `gpt_chat_message`, `document`, `rag_embedding`, `rag_key_config`, `rag_group_config`, `workflow`, `workflow_execution`, `workflow_node_execution`, `workflow_schedule`, `workflow_endpoint`, `api_key`, `llm_resource`.

## Code Style

- Line length: 119
- Formatter: ruff (black-compatible)
- Docstrings: Google convention
- Logging: structlog kwargs only, no f-strings in log calls
