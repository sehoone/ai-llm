from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from src.core.config import settings
from src.core.db import engine
from src.domains.ai_overview.api import router as ai_overview_router
from src.domains.api_key.api import router as api_key_router
from src.domains.artifact.api import public_router as artifact_public_router
from src.domains.artifact.api import router as artifact_router
from src.domains.auth.api import router as auth_router
from src.domains.auth.service import ensure_seed_admin
from src.domains.chat.api import router as chat_router
from src.domains.llm_resource.api import router as llm_resource_router
from src.domains.meeting.api import router as meeting_router
from src.domains.meeting.service import fail_stuck_meetings
from src.domains.rag.api import router as rag_router
from src.domains.user.api import router as user_router
from src.engine.observability import shutdown as observability_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 기동 시 seed 관리자 보장 (최초 로그인용 — SEED_ADMIN_PASSWORD 설정 시).
    with Session(engine) as session:
        ensure_seed_admin(session)
    # 인프로세스 BackgroundTask로 처리되는 회의는 재시작 시 고아가 된다 → 비종료 상태를 FAILED로 정리.
    fail_stuck_meetings()
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

# rag: 지식베이스 그룹·키·문서 + 검색 (ADR-0012)
app.include_router(rag_router, prefix="/api/v1/rag", tags=["rag"])

# artifact: 스트리밍 산출물 + 버전관리 + 공개 링크 (ADR-0013)
app.include_router(artifact_router, prefix="/api/v1/artifacts", tags=["artifacts"])
app.include_router(artifact_public_router, prefix="/api/v1/public/artifacts", tags=["artifacts-public"])

# ai_overview: 사내 문서 + LLM 키워드/동의어 + 하이브리드(trgm+pgvector) 검색 (V2 포팅)
app.include_router(ai_overview_router, prefix="/api/v1/ai-overview", tags=["ai-overview"])

# meeting: 음성 회의록 — 업로드·전사(STT)·요약·화자매핑·발행 (V2 포팅)
app.include_router(meeting_router, prefix="/api/v1/meetings", tags=["meetings"])
