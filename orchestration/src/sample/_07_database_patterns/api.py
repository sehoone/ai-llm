"""샘플 07 — 데이터베이스 패턴

Routes:
    GET  /api/v1/sample/db/health       — DB 연결 상태 + 커넥션 풀 정보
    GET  /api/v1/sample/db/users        — 사용자 목록 조회 (Depends 패턴)
    GET  /api/v1/sample/db/users/count  — 사용자 수 (managed_session 직접 사용)
    GET  /api/v1/sample/db/pool-stats   — 커넥션 풀 상태 상세

학습 포인트:
    1. get_db_session(): FastAPI Depends 주입 — 라우트에서의 표준 패턴
    2. managed_session: 서비스 레이어에서 직접 사용 — 자동 rollback + 에러 로깅
    3. get_session_maker(): 비-라우트 컨텍스트 (스케줄러, startup 이벤트)
    4. DatabaseService 믹스인: 단일 인스턴스로 모든 도메인 레포지토리 접근
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, func, select

from src.common.logging import logger
from src.common.services.database import database_service
from src.common.services.db_session import managed_session
from src.user.models.user_model import User

router = APIRouter()


# ── 스키마 ──────────────────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    id: int
    username: str
    email: str
    role: str
    status: str


# ── 패턴 1: FastAPI Depends 의존성 주입 ──────────────────────────────────────

def get_session():
    """FastAPI 라우트에 세션을 주입하는 의존성.

    database_service.get_db_session()은 managed_session 컨텍스트를 yield하여
    요청 종료 시 자동으로 세션을 닫고, SQLAlchemyError 발생 시 롤백한다.
    """
    yield from database_service.get_db_session()


@router.get(
    "/users",
    response_model=List[UserSummary],
    summary="사용자 목록 조회 (Depends 패턴)",
    description="""
FastAPI `Depends`로 DB 세션을 주입받는 표준 패턴.

**핵심 패턴:**
```python
def get_session():
    yield from database_service.get_db_session()

@router.get("/resource")
def get_resource(db: Session = Depends(get_session)):
    items = db.exec(select(Model)).all()
    return items
```

**동작 원리:**
1. 요청 도착 → FastAPI가 `get_session()` generator 실행 → 세션 생성
2. 라우트 함수에 세션 주입
3. 응답 완료 → generator 재개 → 세션 자동 반환 (commit/rollback/close)

`managed_session`이 `SQLAlchemyError` 발생 시 자동 롤백 + structlog 에러 기록.

**실제 구현 코드:** `src/auth/api/auth_api.py`
    """,
)
def get_users(db: Session = Depends(get_session)):
    users = db.exec(select(User).limit(20)).all()
    logger.info("users_listed", count=len(users))
    return [
        UserSummary(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            status=u.status,
        )
        for u in users
    ]


# ── 패턴 2: managed_session 직접 사용 (서비스 레이어) ───────────────────────

@router.get(
    "/users/count",
    summary="사용자 수 조회 (managed_session 패턴)",
    description="""
서비스 레이어에서 `managed_session`을 직접 사용하는 패턴.

**언제 사용하는가:**
- `Depends` 주입이 불가능한 서비스 함수 / 헬퍼
- 여러 작업을 하나의 트랜잭션으로 묶을 때

**핵심 패턴:**
```python
from src.common.services.db_session import managed_session

with managed_session(database_service.engine) as session:
    result = session.exec(select(Model)).all()
    # SQLAlchemyError 발생 시 자동 rollback + 로그
    # 블록 정상 종료 시 자동 commit + close
```

**실제 구현 코드:** `src/common/services/db_session.py`
    """,
)
def get_user_count():
    with managed_session(database_service.engine) as session:
        count = session.exec(select(func.count(User.id))).first()

    logger.info("user_count_queried", count=count)
    return {"total_users": count}


# ── 패턴 3: DatabaseService 믹스인 (서비스 메서드 직접 호출) ────────────────

@router.get(
    "/health",
    summary="DB 연결 상태",
    description="""
`DatabaseService.health_check()`로 DB 연결 상태를 확인합니다.

**DatabaseService 믹스인 패턴:**
```python
class DatabaseService(
    UserRepositoryMixin,     # get_user_by_id(), get_users(), ...
    SessionRepositoryMixin,  # get_session(), create_session(), ...
    GPTRepositoryMixin,      # get_chat_messages(), save_message(), ...
    LLMResourceRepositoryMixin,
    WorkflowRepositoryMixin,
):
    ...

# 단일 인스턴스로 모든 도메인 접근
database_service.get_user_by_id(user_id)
database_service.get_session(session_id)
database_service.get_llm_resources()
```

→ 도메인마다 별도 레포지토리 클래스를 DI 하는 대신, 믹스인 합성으로 단일 서비스 제공.

**실제 구현 코드:** `src/common/services/database.py`
    """,
)
async def db_health():
    is_healthy = await database_service.health_check()
    if not is_healthy:
        raise HTTPException(status_code=503, detail="DB 연결 실패")

    pool = database_service.engine.pool
    return {
        "status": "healthy",
        "pool_info": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        },
        "schema": "llmonl",
    }


# ── 패턴 4: 커넥션 풀 구성 정보 ─────────────────────────────────────────────

@router.get(
    "/pool-stats",
    summary="커넥션 풀 상태",
    description="""
`QueuePool` 커넥션 풀의 현재 상태와 설정값을 반환합니다.

**풀 설정 (src/common/config.py):**
```
pool_size=20        # 기본 연결 수
max_overflow=10     # 추가 허용 연결 수 (총 최대 30개)
pool_timeout=30     # 연결 대기 최대 시간(초)
pool_recycle=1800   # 연결 재사용 최대 시간(초) — NAT 타임아웃 방지
pool_pre_ping=True  # 사용 전 연결 유효성 검사
```

**비-라우트 컨텍스트에서의 세션 패턴:**
```python
# APScheduler 태스크, startup 이벤트 등
with database_service.get_session_maker() as session:
    # 여기서는 managed_session의 자동 롤백이 없으므로
    # try/except + rollback 직접 처리 필요
    try:
        session.add(record)
        session.commit()
    except Exception:
        session.rollback()
        raise
```

**실제 구현 코드:** `src/common/services/database.py`
    """,
)
def pool_stats():
    pool = database_service.engine.pool
    return {
        "pool_class": pool.__class__.__name__,
        "current": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_active": pool.checkedin() + pool.checkedout(),
        },
        "config": {
            "pool_size": 20,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle_seconds": 1800,
            "pool_pre_ping": True,
        },
    }
