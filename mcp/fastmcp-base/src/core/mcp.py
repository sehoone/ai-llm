from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.config import get_settings
from src.core.db import create_async_engine_from_settings, create_session_factory
from src.core.http import create_http_client

# 라이프스팬 동안 채워지는 공유 컨텍스트 — custom_route에서 ctx 없이 접근 시 사용
_lifespan_context: dict = {}


def get_lifespan_context() -> dict:
    """custom_route 등 Context를 받을 수 없는 곳에서 lifespan 컨텍스트에 접근하는 공개 접근자."""
    return _lifespan_context

#   서버가 뜰 때 한 번만 초기화하고, 모든 도구가 공유하게 하는 진입점
#   FastMCP는 lifespan= 파라미터로 이 함수를 받아 서버 시작/종료 시점에 호출
#
#   yield 한 dict 가 각 도구의 ctx.lifespan_context 로 자동 주입된다.
#   도구 코드에서 ctx.lifespan_context["db_session"] / ["http_client"] 로 꺼내 쓴다.
#
# @asynccontextmanager
#   yield 앞 = 서버 startup (초기화), yield 뒤 finally = 서버 shutdown (자원 해제).
#   try/finally 로 감싸야 Ctrl+C나 예외 발생 시에도 DB 커넥션·소켓이 반드시 닫힌다.
@asynccontextmanager
async def lifespan(mcp: FastMCP):
    settings = get_settings()

    #   PostgreSQL 과의 커넥션 풀 관리 객체
    #   서버 전체에서 engine 하나를 공유하면 풀 크기(pool_size=20)가 일정하게 유지된다.
    #
    #   engine 을 직접 노출하지 않고 session_factory(async_sessionmaker) 로 감싸서 전달한다.
    #   도구에서는 ctx.lifespan_context["db_session"] 으로 팩토리를 꺼낸 뒤
    #   async with session_factory() as db:  # 팩토리 호출 → 풀에서 연결 하나를 빌림
    #          result = await db.execute(...)   # 쿼리 실행
    engine = create_async_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    #   ctx.lifespan_context["http_client"] 로 꺼내 쓴다.
    #   client: httpx.AsyncClient = ctx.lifespan_context["http_client"]
    #      response = await client.get(url)           # 이미 열린 연결 재사용
    http_client = create_http_client(settings)

    # _lifespan_context 에 저장해두면 ctx를 받을 수 없는 custom_route(/health 등)에서도
    # get_lifespan_context() 를 통해 동일 객체에 접근할 수 있다.
    _lifespan_context.update({"db_session": session_factory, "http_client": http_client})
    try:
        # yield 이후가 서버 실행 구간 — FastMCP가 이 컨텍스트를 각 도구의 ctx.lifespan_context 로 주입한다.
        yield _lifespan_context
    finally:
        # 서버 종료 시 반드시 자원 해제:
        # 1. _lifespan_context 비워 이후 접근이 빈 dict를 보도록 한다.
        # 2. 커넥션 풀의 모든 연결을 닫는다 (진행 중인 트랜잭션은 강제 롤백).
        # 3. httpx 세션을 닫아 열린 소켓을 반환한다.
        _lifespan_context.clear()
        await engine.dispose()
        await http_client.aclose()


mcp = FastMCP("FastMCP Base", lifespan=lifespan)
