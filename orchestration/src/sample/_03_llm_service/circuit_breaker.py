"""샘플 03: Circuit Breaker 패턴

실제 구현: src/common/services/llm.py (CircuitBreaker, CircuitState)

핵심 개념:
- Circuit Breaker: 반복 실패하는 외부 서비스를 잠시 차단해 전체 장애 확산 방지
사용 이유:
- LLM API는 일시적 장애(502, 503), Rate Limit이 빈번함
- 장애 서버에 계속 요청하면 타임아웃이 쌓여 전체 응답 속도 저하
- Circuit Breaker가 장애 서버를 잠시 제외하고 다른 서버로 즉시 failover
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"      # 정상 동작 — 모든 요청 통과
    OPEN = "open"          # 차단 중 — 모든 요청 즉시 거부
    HALF_OPEN = "half_open"  # 복구 테스트 중 — 요청 1개만 통과


@dataclass
class CircuitBreaker:
    """단일 외부 리소스(LLM 엔드포인트)의 가용성을 추적하는 회로 차단기.

    Attributes:
        state: 현재 회로 상태
        failure_count: 연속 실패 횟수
        last_failure_time: 마지막 실패 시각 (monotonic time)
        FAILURE_THRESHOLD: OPEN 전환 기준 연속 실패 횟수
        RECOVERY_TIMEOUT: OPEN → HALF_OPEN 전환까지 대기 시간(초)
    """

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    FAILURE_THRESHOLD: int = 3
    RECOVERY_TIMEOUT: float = 30.0

    def is_available(self) -> bool:
        """이 리소스에 요청을 보낼 수 있는지 반환."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.RECOVERY_TIMEOUT:
                # 복구 시간이 지났으면 테스트 요청 1개 허용
                self.state = CircuitState.HALF_OPEN
                return True
            return False

        # HALF_OPEN: 테스트 요청 1개 허용
        return True

    def record_success(self) -> None:
        """성공 — 회로를 닫고 실패 카운터 리셋."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self) -> None:
        """실패 — 카운터 증가, 임계값 초과 시 회로 열기."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = CircuitState.OPEN


# ── 사용 예시 ──────────────────────────────────────────────────────────────────

def demo_circuit_breaker():
    """Circuit Breaker 동작 시연."""
    cb = CircuitBreaker(FAILURE_THRESHOLD=3, RECOVERY_TIMEOUT=5.0)

    print("=== Circuit Breaker 동작 시연 ===\n")

    # 정상 상태에서 실패 누적
    for i in range(1, 4):
        print(f"실패 {i}: is_available={cb.is_available()}, state={cb.state.value}")
        cb.record_failure()

    print(f"\n임계값 도달 후: state={cb.state.value}")
    print(f"is_available={cb.is_available()} (요청 차단됨)")

    print(f"\n{cb.RECOVERY_TIMEOUT}초 대기 후...")
    # 실제로 기다리지 않고 last_failure_time을 조작하여 시뮬레이션
    cb.last_failure_time -= cb.RECOVERY_TIMEOUT + 1

    print(f"is_available={cb.is_available()} (HALF_OPEN으로 전환, 테스트 요청 허용)")
    print(f"state={cb.state.value}")

    # 테스트 성공
    cb.record_success()
    print(f"\n테스트 성공 후: state={cb.state.value} (정상 복구)")


if __name__ == "__main__":
    demo_circuit_breaker()
