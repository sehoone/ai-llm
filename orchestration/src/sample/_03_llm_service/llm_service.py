"""샘플 03: 멀티 프로바이더 LLM 서비스

실제 구현: src/common/services/llm.py (LLMService)

핵심 개념:
- Priority + Weighted Random 선택:
  1. DB에서 LLMResource 목록 조회 (60초 캐싱)
  2. priority DESC로 그룹화 (높은 우선순위 먼저)
  3. 같은 priority 내에서는 weight에 비례한 랜덤 선택
  4. Circuit Breaker가 OPEN인 리소스는 제외

- 다중 프로바이더 지원 (LiteLLM):
  OpenAI, Azure OpenAI, Anthropic, Google Gemini, Ollama

- Fallback 체인:
  DB 리소스 순서대로 시도 → 모두 실패 시 정적 LLMRegistry로 circular fallback

- Retry (tenacity):
  APITimeoutError, APIError → 지수 백오프(2~10초) 재시도 (최대 3회)
  RateLimitError → 즉시 다음 리소스로 이동 (retry 없음)
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from itertools import groupby
from typing import Dict, List, Optional

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from openai import APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .circuit_breaker import CircuitBreaker


# ── 리소스 모델 (실제: src/llm_resources/models/llm_resource_model.py) ──────────

@dataclass
class LLMResourceConfig:
    """LLM 리소스 설정 — DB의 llm_resource 테이블에 대응.

    여러 LLM 엔드포인트(Azure 리전, Anthropic, 자체 호스팅 Ollama 등)를
    DB에서 관리하면 코드 배포 없이 동적으로 추가/제거/우선순위 변경 가능.
    """

    id: int
    name: str
    provider: str           # "openai" | "azure" | "anthropic" | "google" | "ollama"
    model_name: str         # 논리적 모델명 (gpt-4o, claude-3-5-sonnet 등)
    api_key: str
    api_base: Optional[str] = None
    deployment_name: Optional[str] = None  # Azure에서 사용
    api_version: Optional[str] = None      # Azure에서 사용
    region: Optional[str] = None           # 로깅/추적용
    priority: int = 0       # 높을수록 먼저 시도 (기본 0)
    weight: int = 1         # 같은 priority 내에서 트래픽 비율


# ── 정적 폴백 레지스트리 ────────────────────────────────────────────────────────

class LLMRegistry:
    """하드코딩된 모델 목록 — DB 리소스가 모두 실패할 때의 최후 수단.

    실제 코드에서는 ChatOpenAI 인스턴스를 미리 생성해 재사용.
    """

    MODELS = [
        {"name": "gpt-4o-mini", "api_key": "your-key"},
        {"name": "gpt-4o", "api_key": "your-key"},
    ]

    @classmethod
    def get_llm(cls, index: int) -> ChatOpenAI:
        entry = cls.MODELS[index % len(cls.MODELS)]
        return ChatOpenAI(model=entry["name"], api_key=entry["api_key"])


# ── 핵심 서비스 ────────────────────────────────────────────────────────────────

class LLMService:
    """Priority + Circuit Breaker + Weighted Random으로 LLM을 선택하고 호출하는 서비스.

    클래스 레벨 캐시(_resources_cache)를 사용하는 이유:
    - 인스턴스마다 DB를 조회하면 낭비
    - 60초 TTL로 최신 설정을 반영하면서 DB 부하 최소화
    - 모든 인스턴스가 같은 Circuit Breaker 상태를 공유해야 일관된 failover
    """

    _resources_cache: List[LLMResourceConfig] = []
    _resources_cache_ts: float = 0.0
    _CACHE_TTL: float = 60.0
    _circuit_breakers: Dict[int, CircuitBreaker] = {}

    def _get_circuit_breaker(self, resource_id: int) -> CircuitBreaker:
        if resource_id not in self._circuit_breakers:
            self._circuit_breakers[resource_id] = CircuitBreaker()
        return self._circuit_breakers[resource_id]

    # ── 가중치 선택 알고리즘 ───────────────────────────────────────────────────

    def _weighted_order(self, resources: List[LLMResourceConfig]) -> List[LLMResourceConfig]:
        """Priority DESC로 정렬, 같은 priority 내에서 weight에 비례한 랜덤 순서 결정.

        예시:
            priority=10, weight=3: resource A
            priority=10, weight=1: resource B
            → A가 B보다 3배 더 자주 첫 번째로 선택됨

        동일 priority 내 weighted random의 목적:
        - 단순 round-robin: 한 서버가 느려져도 순서가 고정되어 항상 기다림
        - weighted random: 부하를 weight 비율로 분산하되 완전 무작위가 아님
        """
        sorted_by_priority = sorted(resources, key=lambda r: r.priority, reverse=True)

        result: List[LLMResourceConfig] = []
        for _, group_iter in groupby(sorted_by_priority, key=lambda r: r.priority):
            group = list(group_iter)
            remaining = group[:]
            while remaining:
                weights = [max(r.weight, 1) for r in remaining]
                chosen = random.choices(remaining, weights=weights, k=1)[0]
                result.append(chosen)
                remaining.remove(chosen)

        return result

    def _get_candidates(
        self,
        resources: List[LLMResourceConfig],
        model_name: Optional[str],
    ) -> List[LLMResourceConfig]:
        """model_name으로 필터링 + Circuit Breaker 제외 + 가중치 정렬."""
        if model_name:
            candidates = [r for r in resources if r.model_name == model_name]
            if not candidates:
                candidates = resources  # 매칭 없으면 전체 사용
        else:
            candidates = resources

        # OPEN 상태 Circuit Breaker 제외
        available = [r for r in candidates if self._get_circuit_breaker(r.id).is_available()]

        # 모두 OPEN이면 리셋 (전체 장애 상황 복구)
        if not available:
            for r in candidates:
                self._get_circuit_breaker(r.id).record_success()
            available = candidates

        return self._weighted_order(available)

    # ── LLM 팩토리 ────────────────────────────────────────────────────────────

    def _create_llm(self, resource: LLMResourceConfig) -> ChatLiteLLM:
        """DB 리소스 설정으로 LiteLLM 클라이언트 생성.

        LiteLLM model_id 형식:
          - Azure:     "azure/<deployment_name>"
          - Anthropic: "anthropic/<model_name>"
          - Google:    "gemini/<model_name>"
          - Ollama:    "ollama/<model_name>"
          - OpenAI:    "<model_name>" (그대로 사용)
        """
        provider = resource.provider

        if provider == "azure":
            model_id = f"azure/{resource.deployment_name}"
        elif provider == "anthropic":
            model_id = f"anthropic/{resource.model_name}"
        elif provider == "google":
            model_id = f"gemini/{resource.model_name}"
        elif provider == "ollama":
            model_id = f"ollama/{resource.model_name}"
        else:
            model_id = resource.model_name

        params = {
            "api_key": resource.api_key,
            "api_base": resource.api_base,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        if provider == "azure" and resource.api_version:
            params["api_version"] = resource.api_version

        return ChatLiteLLM(model=model_id, **params)

    # ── Retry 래퍼 ─────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APITimeoutError, APIError)),
        reraise=True,
    )
    async def _invoke_with_retry(
        self, llm: ChatLiteLLM, messages: List[BaseMessage]
    ) -> BaseMessage:
        """지수 백오프 재시도 포함 LLM 호출.

        retry 대상:
          - APITimeoutError: 네트워크 타임아웃 (일시적, 재시도 의미 있음)
          - APIError: 서버 오류 5xx (일시적, 재시도 의미 있음)

        retry 제외 (즉시 failover):
          - RateLimitError: 재시도해도 동일 서버에서 또 Rate Limit됨
            → 즉시 다음 리소스로 이동하는 것이 효율적
        """
        try:
            return await llm.ainvoke(messages)
        except RateLimitError:
            # Rate Limit은 재시도 없이 즉시 상위로 전달
            # caller가 다음 리소스로 failover
            raise
        except (APITimeoutError, APIError):
            # tenacity가 재시도
            raise

    # ── 공개 인터페이스 ────────────────────────────────────────────────────────

    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        db_resources: Optional[List[LLMResourceConfig]] = None,
    ) -> BaseMessage:
        """LLM을 선택하고 메시지를 전송한다.

        1. DB 리소스가 있으면 Priority+Weight 순서로 시도
        2. 모두 실패하면 정적 LLMRegistry circular fallback

        Args:
            messages: 전송할 메시지 목록
            model_name: 요청할 모델명 (없으면 우선순위 가장 높은 것 선택)
            db_resources: DB에서 가져온 LLMResource 목록 (테스트용 직접 주입 가능)
        """
        resources = db_resources or self._resources_cache
        active = [r for r in resources if True]  # 실제: is_active 필터

        if active:
            candidates = self._get_candidates(active, model_name)
            last_error = None

            for resource in candidates:
                cb = self._get_circuit_breaker(resource.id)
                try:
                    print(f"  시도: {resource.name} (priority={resource.priority}, weight={resource.weight})")
                    llm = self._create_llm(resource)
                    response = await self._invoke_with_retry(llm, messages)
                    cb.record_success()
                    return response
                except Exception as e:
                    cb.record_failure()
                    last_error = e
                    print(f"  실패: {resource.name} — {e}")

        # 정적 레지스트리 circular fallback
        print("  DB 리소스 전부 실패 → 정적 레지스트리 사용")
        for i in range(len(LLMRegistry.MODELS)):
            try:
                llm = LLMRegistry.get_llm(i)
                return await llm.ainvoke(messages)
            except Exception:
                continue

        raise RuntimeError("사용 가능한 LLM이 없습니다.")


# ── 동작 시연 ──────────────────────────────────────────────────────────────────

def demo_weighted_selection():
    """가중치 선택 알고리즘 시연 (LLM 호출 없음)."""
    service = LLMService()

    resources = [
        LLMResourceConfig(id=1, name="gpt4o-primary", provider="openai",
                         model_name="gpt-4o", api_key="key1", priority=10, weight=3),
        LLMResourceConfig(id=2, name="gpt4o-secondary", provider="openai",
                         model_name="gpt-4o", api_key="key2", priority=10, weight=1),
        LLMResourceConfig(id=3, name="gpt4o-mini-fallback", provider="openai",
                         model_name="gpt-4o-mini", api_key="key3", priority=5, weight=1),
    ]

    print("=== 가중치 선택 시연 (100회 시뮬레이션) ===")
    counts = {r.id: 0 for r in resources}

    for _ in range(100):
        ordered = service._get_candidates(resources, "gpt-4o")
        # 첫 번째 선택된 리소스 카운트 (priority=10이 항상 먼저)
        if ordered:
            counts[ordered[0].id] += 1

    print(f"primary (weight=3): {counts[1]}회 선택")
    print(f"secondary (weight=1): {counts[2]}회 선택")
    print(f"mini-fallback (priority=5): {counts[3]}회 선택")
    print("→ primary:secondary ≈ 3:1, mini-fallback은 0회 (낮은 priority)")

    print("\n=== Circuit Breaker 시연 ===")
    for _ in range(3):
        cb = service._get_circuit_breaker(1)
        cb.record_failure()

    print(f"3회 실패 후 primary is_available: {service._get_circuit_breaker(1).is_available()}")
    ordered = service._get_candidates(resources, "gpt-4o")
    print(f"primary 제외 후 첫 번째 후보: {ordered[0].name if ordered else '없음'}")


if __name__ == "__main__":
    demo_weighted_selection()
