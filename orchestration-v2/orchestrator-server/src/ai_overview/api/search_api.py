"""AI Overview search API — SSE streaming search."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.ai_overview.services.search_service import ai_overview_search_service
from src.auth.api.auth_api import get_current_user
from src.common.logging import logger
from src.user.models.user_model import User

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    model: str = "gpt-4o-mini"
    system_prompt: str = ""


@router.post("/search")
async def ai_overview_search(
    request: Request,
    body: SearchRequest,
    _user: User = Depends(get_current_user),
):
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info("ai_overview_search_started", query=query, model=body.model, has_custom_prompt=bool(body.system_prompt))

    async def generate():
        async for line in ai_overview_search_service.stream_search(
            query=query,
            model=body.model,
            system_prompt=body.system_prompt.strip() or None,
        ):
            yield f"{line}\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
