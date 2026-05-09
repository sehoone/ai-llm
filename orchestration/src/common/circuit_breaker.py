"""Shared circuit breaker for DB-driven resource selection."""

import random
import time
from dataclasses import dataclass
from enum import Enum
from itertools import groupby
from typing import List

from src.llm_resources.models.llm_resource_model import LLMResource


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    FAILURE_THRESHOLD: int = 3
    RECOVERY_TIMEOUT: float = 30.0

    def is_available(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN: allow one test request

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = CircuitState.OPEN


def select_by_weight(resources: List[LLMResource]) -> List[LLMResource]:
    """Order resources by priority DESC, weighted random within each priority tier."""
    sorted_resources = sorted(resources, key=lambda r: r.priority, reverse=True)
    result: List[LLMResource] = []
    for _, group_iter in groupby(sorted_resources, key=lambda r: r.priority):
        group = list(group_iter)
        remaining = group[:]
        while remaining:
            weights = [max(r.weight, 1) for r in remaining]
            chosen = random.choices(remaining, weights=weights, k=1)[0]
            result.append(chosen)
            remaining.remove(chosen)
    return result
