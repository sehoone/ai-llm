"""[sample 도메인] MCP 도구 — LLM 경계 (apps/api의 api 계층에 대응).

얇게 유지: 입력을 받아 SampleService 를 호출하고 결과를 직렬화할 뿐.
도메인 로직·외부 호출은 service / client / repository 에 위임한다.

app.py 등록:
    from src.domains.sample import tools as sample_tools  # noqa: F401
"""
from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ToolError

from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.domains.sample.service import SampleService

logger = get_logger("domains.sample")


def _service(ctx: Context) -> SampleService:
    lc = ctx.lifespan_context
    return SampleService(lc["http_client"], lc["db_session"])


@mcp.tool()
@tool_logger(logger, param_keys=["item_id"])
async def get_sample_item(item_id: str, ctx: Context) -> dict[str, Any]:
    """외부 REST 시스템에서 단일 아이템을 조회한다.

    Args:
        item_id: 외부 시스템의 아이템 식별자
    """
    item = await _service(ctx).get_item(item_id)
    return item.model_dump()


@mcp.tool()
@tool_logger(logger, param_keys=["limit"])
async def list_sample_records(ctx: Context, limit: int = 20) -> dict[str, Any]:
    """로컬 DB에서 레코드 목록을 조회한다.

    Args:
        limit: 반환할 최대 레코드 수 (1 ~ db_max_page_size)
    """
    records = await _service(ctx).list_records(limit)
    return {"total": len(records), "records": [r.model_dump() for r in records]}


@mcp.tool()
@tool_logger(logger, param_keys=["item_id"])
async def get_sample_overview(item_id: str, ctx: Context) -> dict[str, Any]:
    """외부 아이템 + 로컬 레코드 수를 조합한 도메인 뷰 (REST + DB 동시 사용).

    Args:
        item_id: 외부 시스템의 아이템 식별자
    """
    overview = await _service(ctx).get_overview(item_id)
    return overview.model_dump()
