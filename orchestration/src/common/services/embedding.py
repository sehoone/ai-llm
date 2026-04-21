"""Embedding service — DB-driven provider selection with priority, weighted random, and circuit breaker."""

import random
import time
from dataclasses import dataclass
from enum import Enum
from itertools import groupby
from typing import Any, Dict, List, Optional

import litellm
from src.common.config import settings
from src.common.logging import logger
from src.llm_resources.models.llm_resource_model import LLMResource


# ── Circuit Breaker ───────────────────────────────────────────────────────────

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


# ── EmbeddingService ──────────────────────────────────────────────────────────

class EmbeddingService:
    """Embedding service with Priority + Circuit Breaker + Weighted Random resource selection.

    Loads embedding resources from DB (resource_type="embedding"), selects by priority/weight,
    applies per-resource circuit breakers, and calls LiteLLM for provider-agnostic embedding.
    """

    _resources_cache: List[LLMResource] = []
    _resources_cache_ts: float = 0.0
    _RESOURCES_CACHE_TTL: float = 60.0

    _circuit_breakers: Dict[int, CircuitBreaker] = {}

    def _get_circuit_breaker(self, resource_id: int) -> CircuitBreaker:
        if resource_id not in EmbeddingService._circuit_breakers:
            EmbeddingService._circuit_breakers[resource_id] = CircuitBreaker()
        return EmbeddingService._circuit_breakers[resource_id]

    def _select_by_weight(self, resources: List[LLMResource]) -> List[LLMResource]:
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

    def _resolve_candidates(self, resources: List[LLMResource], model_name: Optional[str]) -> List[LLMResource]:
        if model_name:
            candidates = [r for r in resources if r.model_name == model_name]
            if not candidates:
                candidates = [r for r in resources if (r.deployment_name or r.name) == model_name]
            if not candidates:
                logger.warning("embedding_model_not_in_db", model_name=model_name)
                candidates = resources
        else:
            candidates = resources

        available = [r for r in candidates if self._get_circuit_breaker(r.id).is_available()]
        if not available:
            logger.warning("all_embedding_circuit_breakers_open_resetting", count=len(candidates))
            for r in candidates:
                self._get_circuit_breaker(r.id).record_success()
            available = candidates

        return self._select_by_weight(available)

    async def _get_cached_resources(self) -> List[LLMResource]:
        from src.common.services.database import database_service

        now = time.monotonic()
        if now - EmbeddingService._resources_cache_ts > EmbeddingService._RESOURCES_CACHE_TTL:
            try:
                resources = await database_service.get_embedding_resources()
                EmbeddingService._resources_cache = list(resources)
                EmbeddingService._resources_cache_ts = now
            except Exception as e:
                logger.error("failed_to_fetch_embedding_resources", error=str(e))
        return EmbeddingService._resources_cache

    def _build_litellm_params(self, resource: LLMResource) -> Dict[str, Any]:
        """Build LiteLLM call parameters from a DB resource."""
        provider = resource.provider

        if provider == "azure":
            model_id = f"azure/{resource.deployment_name}"
        else:
            model_id = resource.model_name or resource.deployment_name or resource.name

        params: Dict[str, Any] = {
            "model": model_id,
            "api_key": resource.api_key,
            "api_base": resource.api_base,
        }

        if provider == "azure" and resource.api_version:
            params["api_version"] = resource.api_version

        return params

    async def aembed_documents(self, texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
        """Embed a list of texts with failover across registered embedding resources.

        Args:
            texts: Texts to embed.
            model_name: Logical model name (matches llm_resource.model_name). Uses first active resource if None.

        Returns:
            List[List[float]]: Embedding vectors, one per input text.

        Raises:
            RuntimeError: If all resources fail.
        """
        resources = await self._get_cached_resources()
        if not resources:
            raise RuntimeError("no active embedding resources found in DB")

        ordered = self._resolve_candidates(resources, model_name)
        last_error: Optional[Exception] = None

        for resource in ordered:
            cb = self._get_circuit_breaker(resource.id)
            try:
                params = self._build_litellm_params(resource)
                logger.info(
                    "embedding_using_resource",
                    resource_name=resource.name,
                    model_name=resource.model_name,
                    provider=resource.provider,
                    region=resource.region,
                    priority=resource.priority,
                    circuit_state=cb.state.value,
                    text_count=len(texts),
                )
                response = await litellm.aembedding(input=texts, **params)
                cb.record_success()
                return [item["embedding"] for item in response.data]
            except Exception as e:
                cb.record_failure()
                last_error = e
                logger.warning(
                    "embedding_resource_failed",
                    resource=resource.name,
                    provider=resource.provider,
                    region=resource.region,
                    error=str(e),
                    circuit_state=cb.state.value,
                    failure_count=cb.failure_count,
                )

        raise RuntimeError(
            f"all embedding resources failed after trying {len(ordered)} resource(s). last error: {str(last_error)}"
        )

    async def aembed_query(self, text: str, model_name: Optional[str] = None) -> List[float]:
        """Embed a single query string.

        Args:
            text: Query text to embed.
            model_name: Logical model name.

        Returns:
            List[float]: Embedding vector.
        """
        vectors = await self.aembed_documents([text], model_name=model_name)
        return vectors[0]


embedding_service = EmbeddingService()
