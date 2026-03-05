# LLM Orchestration

A production-ready LLM orchestration service built with FastAPI + LangGraph + Langfuse. Features a multi-bot RAG system with isolated knowledge bases, long-term memory, voice evaluation, and comprehensive observability.

**Stack:** Python 3.13+, FastAPI, LangGraph, PostgreSQL + pgvector, OpenAI, Langfuse, mem0ai

## Features

- **Production-Ready Architecture**

  - FastAPI for high-performance async API endpoints
  - LangGraph integration for AI agent workflows with PostgreSQL state persistence
  - Langfuse for LLM observability and tracing (optional)
  - Structured logging with environment-specific formatting and request context (structlog)
  - Rate limiting with configurable rules per endpoint (slowapi)
  - PostgreSQL with pgvector for data persistence and vector storage
  - Docker and Docker Compose support
  - Prometheus metrics and Grafana dashboards for monitoring

- **AI & LLM Features**

  - Long-term memory with mem0ai and pgvector for semantic memory storage
  - LLM Service with automatic retry logic using tenacity (3 attempts, exponential backoff)
  - Multiple LLM model support with fallback chain: `gpt-5-mini → gpt-5 → gpt-4o → gpt-4o-mini`
  - Streaming responses for real-time chat interactions
  - Tool calling with DuckDuckGo search integration
  - Custom GPTs — user-created bots with custom system prompts and model selection

- **Multi-Bot RAG System**

  - Isolated knowledge bases per chatbot via `rag_key`
  - Document upload with automatic chunking (500 chars, 100 overlap) and embedding
  - Vector storage using pgvector (1536-dim OpenAI `text-embedding-3-small`)
  - Semantic similarity search with cosine distance
  - `user_isolated` and `chatbot_shared` RAG types
  - Batch embedding processing with rate limit protection

- **Voice Evaluation**

  - Azure Speech STT/TTS integration
  - Language proficiency evaluation via OpenAI Whisper
  - Audio processing and scoring pipeline

- **Security**

  - JWT-based authentication (10 min access token, 7 day refresh token)
  - API key management for service-to-service auth
  - Session management
  - Input sanitization
  - CORS configuration
  - Rate limiting protection

- **Developer Experience**

  - Environment-specific configuration with automatic `.env` file loading
  - Type hints throughout for better IDE support
  - Easy local development setup with Makefile commands
  - Model evaluation framework with Langfuse trace analysis

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL with pgvector extension ([see Database setup](#database-setup))
- Docker and Docker Compose (optional)

### Environment Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd orchestration
```

2. Install dependencies:

```bash
uv sync
```

3. Copy the example environment file:

```bash
cp .env.example .env.development
```

4. Update the `.env.development` file with your configuration.

### Database Setup

1. Create a PostgreSQL database with the pgvector extension enabled.
2. Update the database connection settings in your `.env` file:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mydb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SCHEMA=llmonl
```

Tables are auto-created by the SQLModel ORM at startup. If you encounter issues, run `schema.sql` manually.

### Running the Application

#### Local Development

**On Linux/macOS:**
```bash
make dev        # Development server with hot reload (port 8000)
make staging    # Staging server
make prod       # Production server
```

**On Windows (PowerShell):**
```powershell
# Development
$env:APP_ENV='development'; uv run uvicorn src.main:app --reload --port 8000

# Staging
$env:APP_ENV='staging'; uv run uvicorn src.main:app --reload --port 8000

# Production
$env:APP_ENV='production'; uv run uvicorn src.main:app --port 8000
```

Go to Swagger UI: `http://localhost:8000/docs`

#### Using Docker

**On Linux/macOS:**
```bash
# Build and start full stack (API, DB, Prometheus, Grafana, cAdvisor)
make docker-compose-up ENV=development

# Stop stack
make docker-compose-down ENV=development

# View logs
make docker-compose-logs ENV=development

# Build only
make docker-build-env ENV=development

# Run specific services (DB + API only)
make docker-run-env ENV=development
```

**On Windows (PowerShell):**
```powershell
# Run with Docker Compose
docker compose --env-file .env.development up -d
```

The Docker stack exposes:

| Service    | Port | Description              |
| ---------- | ---- | ------------------------ |
| API        | 8061 | FastAPI application      |
| PostgreSQL | 5432 | Database (configurable)  |
| Prometheus | 8063 | Metrics collection       |
| Grafana    | 8064 | Metrics visualization    |
| cAdvisor   | 8065 | Container resource usage |

Grafana default credentials: `admin` / `admin`

## Architecture

```
src/
├── main.py                         # FastAPI app entry point (middleware, lifespan, health)
├── common/                         # Shared infrastructure
│   ├── config.py                   # Environment config (auto-loads .env.{APP_ENV})
│   ├── logging.py                  # structlog setup with context binding
│   ├── metrics.py                  # Prometheus metrics
│   ├── middleware.py               # Logging, metrics middleware
│   ├── limiter.py                  # Rate limiting (slowapi)
│   ├── api/api.py                  # API router registration
│   ├── services/
│   │   ├── database.py             # SQLModel ORM + connection pooling
│   │   ├── llm.py                  # LLMRegistry + LLMService with retry/fallback
│   │   ├── graph.py                # Message processing (dump/prepare/process)
│   │   └── sanitization.py        # Input sanitization
│   ├── schemas/graph.py            # GraphState definition (LangGraph state type)
│   ├── prompts/                    # System prompt templates
│   └── langgraph/
│       ├── graph.py                # LangGraphAgent — main orchestration class
│       └── tools/                  # Tool registry (duckduckgo_search)
├── auth/                           # JWT auth + API key management
│   ├── api/auth_api.py
│   └── api/api_key_api.py
├── chatbot/                        # Chat endpoints, sessions, threads, custom GPTs
│   ├── api/chatbot_api.py
│   ├── api/session_api.py
│   └── api/custom_gpts.py
├── rag/                            # Multi-bot RAG system
│   └── api/rag_api.py
├── user/                           # User management
│   └── api/user_api.py
├── llm_resources/                  # Per-user LLM model configuration
│   └── api/llm_resource_api.py
└── voice_evaluation/               # Azure Speech STT/TTS + proficiency evaluation
    └── api/voice_evaluation_api.py
```

**Layer pattern per module:** `api/` (routers) → `services/` (business logic) → `models/` (SQLModel DB models) → `schemas/` (Pydantic)

**Adding an endpoint:** Create in `src/{module}/api/`, register in `src/common/api/api.py`.

## API Reference

Base URL: `http://localhost:8000/api/v1`

### Authentication

| Method | Endpoint               | Description                   |
| ------ | ---------------------- | ----------------------------- |
| POST   | `/auth/register`       | Register a new user           |
| POST   | `/auth/login`          | Authenticate, receive JWT     |
| POST   | `/auth/logout`         | Logout and invalidate session |
| POST   | `/auth/refresh`        | Refresh access token          |

### API Keys

| Method | Endpoint          | Description           |
| ------ | ----------------- | --------------------- |
| POST   | `/api-keys`       | Create API key        |
| GET    | `/api-keys`       | List API keys         |
| DELETE | `/api-keys/{id}`  | Revoke API key        |

### Users

| Method | Endpoint       | Description          |
| ------ | -------------- | -------------------- |
| GET    | `/users/me`    | Get current user     |
| PUT    | `/users/me`    | Update current user  |

### Chat

| Method | Endpoint                   | Description                    |
| ------ | -------------------------- | ------------------------------ |
| POST   | `/chatbot/chat`            | Send message, receive response |
| POST   | `/chatbot/chat/stream`     | Send message, streaming SSE    |
| GET    | `/chatbot/sessions`        | List chat sessions             |
| GET    | `/chatbot/sessions/{id}`   | Get session messages           |
| DELETE | `/chatbot/sessions/{id}`   | Delete session                 |

### Custom GPTs

| Method | Endpoint       | Description             |
| ------ | -------------- | ----------------------- |
| POST   | `/gpts`        | Create custom GPT       |
| GET    | `/gpts`        | List custom GPTs        |
| GET    | `/gpts/{id}`   | Get custom GPT details  |
| PUT    | `/gpts/{id}`   | Update custom GPT       |
| DELETE | `/gpts/{id}`   | Delete custom GPT       |
| POST   | `/gpts/{id}/chat`        | Chat with custom GPT    |
| POST   | `/gpts/{id}/chat/stream` | Stream chat with custom GPT |

### RAG

| Method | Endpoint                      | Description                    |
| ------ | ----------------------------- | ------------------------------ |
| POST   | `/rag/upload`                 | Upload document (file + rag_key) |
| GET    | `/rag/documents`              | List documents (filter by rag_key) |
| DELETE | `/rag/documents/{id}`         | Delete document                |
| POST   | `/rag/search`                 | Semantic similarity search     |

### Voice Evaluation

| Method | Endpoint                        | Description               |
| ------ | ------------------------------- | ------------------------- |
| POST   | `/voice-evaluation/evaluate`    | Evaluate voice recording  |
| POST   | `/voice-evaluation/tts`         | Text-to-speech synthesis  |

### LLM Resources

| Method | Endpoint            | Description                  |
| ------ | ------------------- | ---------------------------- |
| GET    | `/llm-resources`    | Get per-user LLM config      |
| PUT    | `/llm-resources`    | Update per-user LLM config   |

### Health & Monitoring

| Method | Endpoint    | Description                          |
| ------ | ----------- | ------------------------------------ |
| GET    | `/health`   | Health check with DB status          |
| GET    | `/metrics`  | Prometheus metrics endpoint          |

For full interactive API documentation: `/docs` (Swagger UI) or `/redoc` (ReDoc).

## Configuration

### Environment Files

Priority order (highest to lowest):
1. `.env.{APP_ENV}.local`
2. `.env.{APP_ENV}`
3. `.env.local`
4. `.env`

Valid environments: `development`, `staging`, `production`, `test`

### Key Environment Variables

```bash
# Application
APP_ENV=development
PROJECT_NAME="LLM Orchestration"
DEBUG=false

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mydb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SCHEMA=llmonl

# OpenAI
OPENAI_API_KEY=your_openai_api_key
DEFAULT_LLM_MODEL=gpt-5-mini
DEFAULT_LLM_TEMPERATURE=0.2
MAX_TOKENS=2000

# Long-Term Memory (mem0ai)
LONG_TERM_MEMORY_COLLECTION_NAME=longterm_memory
LONG_TERM_MEMORY_MODEL=gpt-4o-mini
LONG_TERM_MEMORY_EMBEDDER_MODEL=text-embedding-3-small

# Voice / Audio
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus
OPENAI_TTS_MODEL=tts-1
OPENAI_STT_MODEL=whisper-1

# Observability (optional)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Security
JWT_SECRET_KEY=your_secret_key_here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Rate Limiting
RATE_LIMIT_DEFAULT="200 per day,50 per hour"
```

## Key Components

### LangGraph Agent

Stateful two-node workflow: `_chat` → `_tool_call` (if tool calls detected) → back to `_chat` → `END`.

- State persisted as PostgreSQL checkpoints per `thread_id`
- Long-term memory injected into system prompt via mem0ai semantic search
- After each turn, conversation is summarized and stored back to mem0
- Entry points: `get_response()` (blocking) and `stream_response()` (SSE)

### LLM Service

`LLMRegistry` maintains instances of all models. `LLMService` wraps calls with:
- tenacity retry (3 attempts, exponential backoff: 1s → 2s → 4s)
- Circular fallback across the registry

**Supported models:**

| Model       | Use Case                | Reasoning Effort |
| ----------- | ----------------------- | ---------------- |
| gpt-5-mini  | Default (balanced)      | Low              |
| gpt-5       | Complex reasoning tasks | Medium           |
| gpt-5-nano  | Fast responses          | Minimal          |
| gpt-4o      | Production workloads    | N/A              |
| gpt-4o-mini | Cost-effective tasks    | N/A              |

**Fallback chain:** `gpt-5-mini → gpt-5 → gpt-4o → gpt-4o-mini`

### RAG System

Each chatbot has an isolated knowledge base identified by `rag_key`:

1. **Upload** — Document stored in DB, split into 500-char chunks (100-char overlap)
2. **Embed** — Each chunk embedded with `text-embedding-3-small` (1536-dim), stored in pgvector
3. **Search** — Cosine similarity search returns top-k chunks

RAG types:
- `user_isolated` — knowledge base scoped per user
- `chatbot_shared` — shared across all users of a chatbot

### Long-Term Memory

mem0ai with pgvector backend. User-scoped semantic memory stored in the configured collection. Multimodal content (images) is filtered before storing to ensure compatibility.

### Custom GPTs

Users can create custom bots with:
- Custom system instructions
- Model selection and temperature
- Assigned `rag_key` for knowledge base
- Independent session/message history (`gpt_session`, `gpt_chat_message` tables)

## Model Evaluation

The project includes an evaluation framework for measuring model performance using Langfuse traces.

**On Linux/macOS:**
```bash
make eval [ENV=development]          # Interactive mode
make eval-quick [ENV=development]    # Quick mode with defaults
make eval-no-report [ENV=development] # Without report generation
```

**On Windows (PowerShell):**
```powershell
$env:APP_ENV='development'; python -m evals.main --interactive
$env:APP_ENV='development'; python -m evals.main --quick
$env:APP_ENV='development'; python -m evals.main --no-report
```

Evaluation metrics are defined as markdown files in `evals/metrics/prompts/`:
- `conciseness.md`
- `hallucination.md`
- `helpfulness.md`
- `relevancy.md`
- `toxicity.md`

Reports are saved to `evals/reports/evaluation_report_YYYYMMDD_HHMMSS.json`.

## Logging

Uses structlog with automatic request context binding.

- **Development:** colored console output
- **Production:** JSON structured logs
- Always use kwargs, never f-strings in log calls:

```python
# Correct
logger.info("user_login", user_id=user.id, ip=request.client.host)

# Wrong
logger.info(f"User {user.id} logged in")
```

Every request automatically gets: `request_id`, `session_id`, `user_id`, `path`, `method`, `status`, `duration`.

## Project Structure

```
orchestration/
├── src/
│   ├── main.py                     # Application entry point
│   ├── common/                     # Shared infrastructure
│   ├── auth/                       # JWT auth + API key management
│   ├── chatbot/                    # Chat, sessions, custom GPTs
│   ├── rag/                        # Multi-bot RAG system
│   ├── user/                       # User management
│   ├── llm_resources/              # Per-user LLM configuration
│   └── voice_evaluation/           # Azure Speech STT/TTS + evaluation
├── evals/
│   ├── evaluator.py                # Evaluation logic
│   ├── main.py                     # Evaluation CLI
│   ├── metrics/prompts/            # Metric definitions (markdown)
│   └── reports/                    # Generated evaluation reports
├── grafana/                        # Grafana dashboard provisioning
├── prometheus/                     # Prometheus configuration
├── scripts/                        # Utility scripts
├── docker-compose.yml              # Full stack Docker Compose
├── Dockerfile                      # Application Docker image
├── Makefile                        # Development commands
├── pyproject.toml                  # Python dependencies (uv)
├── schema.sql                      # Database schema reference
├── SECURITY.md                     # Security policy
└── README.md                       # This file
```

## Security

For security concerns, please review our [Security Policy](SECURITY.md).

## Reference
https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template