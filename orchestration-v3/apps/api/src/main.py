from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from src.core.config import settings
from src.core.db import engine
from src.domains.api_key.api import router as api_key_router
from src.domains.auth.api import router as auth_router
from src.domains.auth.service import ensure_seed_admin
from src.domains.chat.api import router as chat_router
from src.domains.llm_resource.api import router as llm_resource_router
from src.domains.user.api import router as user_router
from src.engine.observability import shutdown as observability_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 기동 시 seed 관리자 보장 (최초 로그인용 — SEED_ADMIN_PASSWORD 설정 시).
    with Session(engine) as session:
        ensure_seed_admin(session)
    yield
    # 종료 시 버퍼된 Langfuse 트레이스 flush (ADR-0007). 비활성이면 no-op.
    observability_shutdown()


app = FastAPI(title="orchestration-v3 api", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


# ── 인증 (ID/PW 로그인 → HS256 JWT 발급) ──
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

# ── 플랫폼 도메인 라우터 (V2 platform-server 포팅) ──
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(api_key_router, prefix="/api/v1/api-keys", tags=["api-keys"])
app.include_router(llm_resource_router, prefix="/api/v1/llm-resources", tags=["llm-resources"])

# ── LLM 도메인 라우터 ──
# chat: 메시지 전송·승인(HITL) — SSE (ADR-0008)
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
