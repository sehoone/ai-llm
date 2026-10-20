"""sample 도메인 단위 테스트 — 데모 모드라 외부 의존 없음.

FastMCP Client 로 in-memory 전체 스택(등록·검증·실행)을 테스트한다. HTTP 미들웨어를
거치지 않으므로 OIDC 설정도 불필요. pyproject의 asyncio_mode="auto"로 마커 생략 가능.
DB가 필요한 도구(list_sample_records·get_sample_overview)는 등록만 확인하고,
실제 조회는 PostgreSQL + scripts/schema.sql 적용이 필요하므로 통합 테스트로 분리한다.
"""
from fastmcp import Client

from src.app import mcp


async def test_get_sample_item_demo_mode():
    async with Client(mcp) as client:
        result = await client.call_tool("get_sample_item", {"item_id": "abc"})
    assert result.data["id"] == "abc"
    assert result.data["is_demo"] is True


async def test_get_sample_item_rejects_blank():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_sample_item", {"item_id": "   "}, raise_on_error=False
        )
    assert result.is_error


async def test_domain_tools_registered():
    async with Client(mcp) as client:
        names = {t.name for t in await client.list_tools()}
    assert {"get_sample_item", "list_sample_records", "get_sample_overview"} <= names
