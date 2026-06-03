"""샘플 03 — LLM 서비스 API

Routes:
    GET  /api/v1/sample/llm/info              — LLM 서비스 현황 (레지스트리, 리소스)
    POST /api/v1/sample/llm/call              — LLM 직접 호출
    GET  /api/v1/sample/llm/circuit-breakers  — Circuit Breaker 상태 조회

학습 포인트:
    1. LLMService는 DB의 llm_resource 테이블에서 60초 캐시로 설정을 동적 로드
    2. Priority DESC + Weighted Random으로 요청 분산
    3. Circuit Breaker: 연속 3회 실패 시 해당 리소스 30초 차단
    4. DB 리소스 모두 실패 시 LLMRegistry(정적 목록) circular fallback
"""

import time
from typing import Optional

from fastapi import APIRouter
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from src.common.services.llm import LLMRegistry, LLMService, llm_service

router = APIRouter()


class LLMCallRequest(BaseModel):
    message: str
    model_name: Optional[str] = None


class LLMCallResponse(BaseModel):
    response: str
    model_used: Optional[str] = None


@router.get(
    "/info",
    summary="LLM 서비스 현황",
    description="""
LLMRegistry(정적 모델 목록)와 캐시된 DB 리소스 현황을 반환합니다.

**정보 구성:**
- `registry_models`: 코드에 하드코딩된 폴백용 모델 목록
- `db_resources_count`: DB에서 로드된 활성 LLMResource 수
- `cache_age_seconds`: 마지막 DB 조회 후 경과 시간 (TTL=60초)

**실제 구현 코드:** `src/common/services/llm.py` `LLMService`
    """,
)
async def llm_info():
    registry_models = LLMRegistry.get_all_names()

    # 캐시된 DB 리소스 조회 (실제 DB 조회 없이 캐시만 확인)
    cache_age = time.monotonic() - LLMService._resources_cache_ts
    cached_resources = LLMService._resources_cache

    return {
        "registry_models": registry_models,
        "default_model": registry_models[0] if registry_models else None,
        "db_resources_count": len(cached_resources),
        "cache_age_seconds": round(cache_age, 1),
        "cache_ttl_seconds": LLMService._RESOURCES_CACHE_TTL,
        "circuit_breakers_active": len(LLMService._circuit_breakers),
    }


@router.post(
    "/call",
    response_model=LLMCallResponse,
    summary="LLM 직접 호출",
    description="""
LLMService.call()을 직접 호출하는 예시.

**선택 과정:**
1. DB에서 활성 LLMResource 조회 (60초 캐시)
2. `model_name` 으로 필터링
3. Circuit Breaker OPEN 리소스 제외
4. Priority DESC + Weight 비례 랜덤 순서 결정
5. 순서대로 시도 → 성공 시 즉시 반환
6. 모두 실패 시 LLMRegistry circular fallback

**실제 구현 코드:** `src/common/services/llm.py` `LLMService.call()`
    """,
)
async def llm_call(body: LLMCallRequest):
    messages = [HumanMessage(content=body.message)]
    response = await llm_service.call(messages, model_name=body.model_name)

    return LLMCallResponse(
        response=str(response.content),
        model_used=body.model_name,
    )


@router.get(
    "/circuit-breakers",
    summary="Circuit Breaker 상태",
    description="""
각 DB LLM 리소스의 Circuit Breaker 상태를 반환합니다.

**상태 종류:**
- `closed`: 정상 — 모든 요청 통과
- `open`: 차단 중 — 연속 3회 실패 후 30초간 요청 거부
- `half_open`: 복구 테스트 중 — 30초 후 테스트 요청 1개 허용

**실제 구현 코드:** `src/common/services/llm.py` `CircuitBreaker`
    """,
)
async def circuit_breaker_status():
    breakers = []
    for resource_id, cb in LLMService._circuit_breakers.items():
        elapsed = time.monotonic() - cb.last_failure_time if cb.last_failure_time > 0 else None
        breakers.append({
            "resource_id": resource_id,
            "state": cb.state.value,
            "failure_count": cb.failure_count,
            "seconds_since_last_failure": round(elapsed, 1) if elapsed else None,
            "is_available": cb.is_available(),
        })

    return {
        "circuit_breakers": breakers,
        "total": len(breakers),
        "open_count": sum(1 for b in breakers if b["state"] == "open"),
    }
