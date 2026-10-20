from fastapi import FastAPI

from src.core.config import settings
from src.domains.api_key.api import router as api_key_router
from src.domains.llm_resource.api import router as llm_resource_router
from src.domains.user.api import router as user_router

app = FastAPI(title="orchestration-v3 api", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


# ── 플랫폼 도메인 라우터 (V2 platform-server 포팅) ──
app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(api_key_router, prefix="/api/v1/api-keys", tags=["api-keys"])
app.include_router(llm_resource_router, prefix="/api/v1/llm-resources", tags=["llm-resources"])

# ── LLM 도메인 라우터는 이식 단계에서 등록 ──
# from src.domains.chat.api import router as chat_router
# app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
