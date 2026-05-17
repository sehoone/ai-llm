"""
[케이스 03 - database] SQLAlchemy async DB CRUD 패턴

다루는 패턴:
  1. ctx: Context — lifespan_context 에서 db_session 꺼내기
  2. async with session_factory() as db — 세션 생성·해제
  3. select / where / offset / limit — SQLAlchemy 2.x 스타일
  4. db.flush() → db.refresh() → db.commit() 순서
  5. SQLAlchemyError → ToolError 변환
  6. @protected 인증 데코레이터 조합

사전 조건:
  - scripts/schema.sql 에 products 테이블 추가 (orm.py 주석 참고)
  - APP_ENV=local uv run python main.py server 로 서버 기동

app.py 등록:
    from src.sample.database import tools as db_sample_tools  # noqa: F401
"""
from typing import Any, Optional

from fastmcp import Context
from fastmcp.exceptions import ToolError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from src.core.auth import protected
from src.core.config import get_settings
from src.core.logging import get_logger, tool_logger
from src.core.mcp import mcp
from src.sample.database.models import ProductListResponse, ProductResponse
from src.sample.database.orm import Product

logger = get_logger("sample.database")


def _to_response(p: Product) -> ProductResponse:
    return ProductResponse(
        id=p.id,
        name=p.name,
        price=float(p.price),
        stock=p.stock,
        category=p.category,
        is_active=p.is_active,
        created_at=p.created_at.isoformat(),
    )


# ── Tool 1: 상품 생성 ─────────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["name", "category"])
@protected  # 인증 필요 — @protected 는 tool_logger 안쪽에 위치
async def db_create_product(
    name: str,
    price: float,
    ctx: Context,           # 포인트 ①: ctx 로 DB 세션 접근
    stock: int = 0,
    category: str = "기타",
) -> dict[str, Any]:
    """새 상품을 등록합니다.

    Args:
        name: 상품명 (1~200자)
        price: 가격 (0 이상)
        stock: 재고 수량 (기본값 0)
        category: 카테고리 (기본값: 기타)
        ctx: MCP 컨텍스트 (자동 주입 — 클라이언트가 직접 전달하지 않음)
    """
    if not (1 <= len(name) <= 200):
        raise ToolError("상품명은 1~200자 사이여야 합니다.")
    if price < 0:
        raise ToolError("가격은 0 이상이어야 합니다.")
    if stock < 0:
        raise ToolError("재고는 0 이상이어야 합니다.")

    # 포인트 ②: lifespan_context 에서 session_factory 꺼내기
    session_factory = ctx.lifespan_context["db_session"]

    try:
        # 포인트 ③: async with 로 세션 자동 관리 (commit/rollback)
        async with session_factory() as db:
            product = Product(name=name, price=price, stock=stock, category=category)
            db.add(product)

            # 포인트 ④: flush → DB에 INSERT 실행 (id 할당) / refresh → 최신 상태 반영
            await db.flush()
            await db.refresh(product)
            await db.commit()

            return {"success": True, "product": _to_response(product).model_dump()}

    # 포인트 ⑤: SQLAlchemyError → ToolError 변환
    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── Tool 2: 상품 목록 조회 (페이지네이션) ─────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["limit", "offset", "category"])
@protected
async def db_list_products(
    ctx: Context,
    limit: int = 10,
    offset: int = 0,
    category: Optional[str] = None,
    active_only: bool = True,
) -> dict[str, Any]:
    """상품 목록을 조회합니다.

    Args:
        limit: 페이지 크기 (최대 100)
        offset: 건너뛸 행 수
        category: 카테고리 필터 (생략 시 전체)
        active_only: 활성 상품만 조회 여부
        ctx: MCP 컨텍스트 (자동 주입)
    """
    settings = get_settings()
    limit = min(max(1, limit), settings.db_max_page_size)

    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            # 포인트 ⑥: SQLAlchemy 2.x select() 스타일
            q = select(Product)
            if active_only:
                q = q.where(Product.is_active.is_(True))
            if category:
                q = q.where(Product.category == category)

            # 전체 수 조회
            count_q = select(func.count()).select_from(q.subquery())
            total = (await db.execute(count_q)).scalar_one()

            # 페이지 데이터 조회
            result = await db.execute(q.offset(offset).limit(limit))
            products = result.scalars().all()

            return ProductListResponse(
                products=[_to_response(p) for p in products],
                total_count=total,
                limit=limit,
                offset=offset,
            ).model_dump()

    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── Tool 3: 단건 조회 ─────────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["product_id"])
@protected
async def db_get_product(product_id: int, ctx: Context) -> dict[str, Any]:
    """ID로 상품을 조회합니다."""
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if product is None:
                raise ToolError(f"상품 ID {product_id}를 찾을 수 없습니다.")
            return _to_response(product).model_dump()

    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── Tool 4: 수정 ──────────────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["product_id"])
@protected
async def db_update_product(
    product_id: int,
    ctx: Context,
    name: Optional[str] = None,
    price: Optional[float] = None,
    stock: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> dict[str, Any]:
    """상품 정보를 수정합니다. 전달한 필드만 변경됩니다."""
    if name is not None and not (1 <= len(name) <= 200):
        raise ToolError("상품명은 1~200자 사이여야 합니다.")
    if price is not None and price < 0:
        raise ToolError("가격은 0 이상이어야 합니다.")

    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if product is None:
                raise ToolError(f"상품 ID {product_id}를 찾을 수 없습니다.")

            # 포인트 ⑦: None 체크 후 필드별 부분 업데이트
            if name is not None:
                product.name = name
            if price is not None:
                product.price = price
            if stock is not None:
                product.stock = stock
            if is_active is not None:
                product.is_active = is_active

            await db.flush()
            await db.refresh(product)
            await db.commit()
            return {"success": True, "product": _to_response(product).model_dump()}

    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")


# ── Tool 5: 삭제 ──────────────────────────────────────────────────────────────
@mcp.tool()
@tool_logger(logger, param_keys=["product_id"])
@protected
async def db_delete_product(product_id: int, ctx: Context) -> dict[str, Any]:
    """상품을 삭제합니다 (하드 삭제)."""
    session_factory = ctx.lifespan_context["db_session"]
    try:
        async with session_factory() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if product is None:
                raise ToolError(f"상품 ID {product_id}를 찾을 수 없습니다.")

            await db.delete(product)
            await db.commit()
            return {"success": True, "deleted_id": product_id, "name": product.name}

    except ToolError:
        raise
    except SQLAlchemyError as e:
        raise ToolError(f"데이터베이스 오류: {e}")
